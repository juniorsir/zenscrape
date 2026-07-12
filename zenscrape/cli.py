import argparse
import asyncio
import csv
import sqlite3
import json
import sys
import os
from loguru import logger
from urllib.parse import urljoin

from .engine import ZenCrawler
from .models import ZenRequest
from .config import ZenEngineConfig, ZenSecurityConfig
from .storage import ZenDatabase
from .inspector import ZenInspector

# --- EXPORT UTILITIES ---
def export_data(db_path, format="json"):
    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT url, data, timestamp FROM results")
        rows = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to read database: {e}")
        return
    finally:
        conn.close()

    if not rows:
        logger.warning("No data found to export.")
        return

    filename = f"export_{format}.{format}"
    if format == "json":
        data = [{"url": r[0], "data": json.loads(r[1]), "time": r[2]} for r in rows]
        with open(filename, "w") as f: 
            json.dump(data, f, indent=4)
    else:
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "DATA", "TIMESTAMP"])
            writer.writerows(rows)
    logger.success(f"💾 Exported {len(rows)} items to {filename}")

# --- CORE SCRAPER EXECUTION ---
async def start_scrape(args):
    config = ZenSecurityConfig(
        use_tor=args.tor, 
        impersonate=args.profile, 
        cache_requests=not args.no_cache
    )
    ZenEngineConfig.setup(config)
    
    from .cli import calculate_optimal_concurrency
    final_concurrency = calculate_optimal_concurrency(args.concurrency)
    
    db = ZenDatabase(args.output)
    crawler = ZenCrawler(
        concurrency=final_concurrency, 
        max_depth=args.depth, 
        delay=args.delay
    )

    async def callback(response):
        data = {}
        if args.css:
            elems = response.css(args.css)
            data["extracted"] = [e.text(strip=True) for e in elems if e.text(strip=True)] if elems else ["Not Found"]
        else:
            title = response.css_first("title").text() if response.css_first("title") else "N/A"
            data["extracted"] = [title.strip()]

        db.save_result(response.url, data)

        print("\n" + "═"*50)
        print(f"📥 SCRAPED RESULTS FROM SUBMISSION:")
        print("═"*50)
        for val in data.get("extracted", ["No Data"]):
            print(f"👉 {val[:100]}")
        print("═"*50 + "\n")

        if args.depth > 0 and response.meta.get("depth", 0) < args.depth:
            for link in response.css("article.product_pod h3 a, a"):
                href = link.attributes.get("href")
                if href and not href.startswith("#"):
                    full_url = urljoin(response.url, href)
                    new_depth = response.meta.get("depth", 0) + 1
                    
                    await crawler.add_request(ZenRequest(
                        url=full_url,
                        callback=callback,
                        meta={"depth": new_depth}
                    ))

    headers = json.loads(args.headers) if args.headers else {}
    cookies = json.loads(args.cookies) if args.cookies else {}
    post_data = json.loads(args.data) if args.data else {}
    params = json.loads(args.params) if args.params else {}

    req = ZenRequest(
        url=args.url,
        method=args.method,
        headers=headers,
        cookies=cookies,
        data=post_data,
        params=params,
        callback=callback
    )

    await crawler.add_request(req)
    await crawler.run()

    if args.json: export_data(args.output, "json")
    if args.csv: export_data(args.output, "csv")

# --- CONCURRENCY MANAGER ---
def calculate_optimal_concurrency(user_concurrency: int) -> int:
    cpu_cores = os.cpu_count() or 2
    is_android = os.path.exists("/data/data/com.termux")
    if user_concurrency == 0:
        if is_android:
            optimal = min(max(int(cpu_cores * 1.5), 2), 6)
            logger.info(f"📱 Mobile detected. Auto-optimizing workers to: {optimal} (Cores: {cpu_cores})")
            return optimal
        else:
            optimal = min(cpu_cores * 2, 16)
            logger.info(f"💻 Desktop detected. Auto-optimizing workers to: {optimal} (Cores: {cpu_cores})")
            return optimal
    if is_android and user_concurrency > 10:
        logger.warning(f"⚠️ Warning: High concurrency ({user_concurrency}) on mobile may cause crashes or heavy battery drain.")
    return user_concurrency

async def run_inspector(args):
    logger.info(f"🔍 Scouting {args.url}...")
    from curl_cffi.requests import AsyncSession
    proxy = "socks5h://127.0.0.1:9050" if args.tor else None
    
    async with AsyncSession(impersonate=args.profile, proxies={"http": proxy, "https": proxy} if proxy else None) as s:
        try:
            res = await s.get(args.url, timeout=20)
            insp = ZenInspector(res.text, args.url)
            summary = insp.get_summary()
        except Exception as e:
            logger.error(f"Failed to inspect site: {e}")
            return

    print("\n" + "═"*60)
    print(f"📡 SITE INTELLIGENCE: {summary['title'][:50]}")
    print("═"*60)
    print(f"🔗 Links:  {len(summary['links']['internal'])} Internal | {len(summary['links']['external'])} External")
    print(f"🏗️  Forms:  {len(summary['forms'])} detected")
    print(f"🖼️  Media:  {summary['media']['count']} Images")
    
    if summary['forms']:
        print("\n📝 INPUTS DETECTED:")
        for i, f in enumerate(summary['forms']):
            fields = [f"{inp['name']} ({inp['type']})" for inp in f['inputs']]
            print(f"  [Form {i+1}] {f['method']} -> {f['action']}")
            print(f"    Fields: {', '.join(fields)}")

    print("\n" + "═"*60)
    print("CHOICES:")
    print("1. [TITLES]   Extract Page Titles")
    print("2. [MAP]      Extract all Internal Links")
    print("3. [FORMS]    Extract Form Actions")
    print("4. [IMAGES]   Extract all Image URLs")
    print("5. [DEEP]     Start Recursive Crawl (Depth 1)")
    print("6. [SUBMIT]   Fill and Submit Detected Form")
    print("7. [AUDIT]    Deep Structural Audit")
    print("q. [EXIT]")
    
    choice = input("\nAction (1-7): ").lower()
    
    if choice == '1': args.css = "title"
    elif choice == '2': args.css = "a"
    elif choice == '3': args.css = "form"
    elif choice == '4': args.css = "img"
    elif choice == '5': args.depth = 1
    elif choice == '6':
        if not summary['forms']:
            logger.error("No forms detected to submit!")
            return
        selected_form = summary['forms'][0]
        payload = {}
        fillable_types = ["text", "search", "password", "email", "tel", "url"]
        for field in selected_form['inputs']:
            if field['type'] in fillable_types:
                val = input(f"   Value for '{field['name']}' ({field['type']}): ")
                if val: payload[field['name']] = val
            elif field['type'] == "submit":
                payload[field['name']] = field['placeholder'] or "submit"

        args.url = selected_form['action']
        args.method = selected_form['method']
        if selected_form['method'] == "POST":
            args.data = json.dumps(payload)
            args.params = "{}"
        else:
            args.params = json.dumps(payload)
            args.data = "{}"
        if not args.css: args.css = "h2, h3, title"
        
    elif choice == '7':
        print("\n" + "═"*60)
        print("🔍 DEEP STRUCTURAL AUDIT")
        print("═"*60)
        print("\n🔑 SEO & OPEN GRAPH METADATA:")
        important_meta = ["description", "og:title", "og:description", "og:image", "keywords"]
        for key in important_meta:
            if key in summary["metadata"]:
                print(f"  • {key}: {summary['metadata'][key][:80]}...")
        if summary["structure"]["headings"]:
            print("\n🌲 HEADING HIERARCHY TREE:")
            for h in summary["structure"]["headings"]:
                indent = "  " if h["tag"] == "H2" else "    " if h["tag"] == "H3" else ""
                print(f"{indent}• [{h['tag']}] {h['text']}")
        if summary["structure"]["detailed_tables"]:
            print("\n📊 TABLE SCHEMAS DETECTED:")
            for t in summary["structure"]["detailed_tables"]:
                print(f"  • Table #{t['id']} Columns: {', '.join(t['columns'][:5])}")
        print("\n" + "═"*60)
        input("\nPress Enter to Exit Audit...")
        sys.exit()
    elif choice == 'q': sys.exit()

    await start_scrape(args)

def main():
    parser = argparse.ArgumentParser(description="ZenScrape Elite - Professional Web Intelligence")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument("--inspect", action="store_true", help="Interactive Mode")
    parser.add_argument("--tor", action="store_true", help="Route through Tor")
    parser.add_argument("--profile", default="chrome110")
    parser.add_argument("--concurrency", type=int, default=0)
    parser.add_argument("--depth", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--method", default="GET", choices=["GET", "POST", "PUT"])
    parser.add_argument("--data", default="{}")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--headers", default="{}")
    parser.add_argument("--cookies", default="{}")
    parser.add_argument("--css")
    parser.add_argument("--output", default="zenscrape_results.db")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--csv", action="store_true")

    args = parser.parse_args()
    
    action_performed = False

    if args.url:
        action_performed = True
        if args.inspect: asyncio.run(run_inspector(args))
        else: asyncio.run(start_scrape(args))

    if args.json:
        export_data(args.output, "json")
        action_performed = True
        
    if args.csv:
        export_data(args.output, "csv")
        action_performed = True

    if not action_performed:
        parser.print_help()

if __name__ == "__main__":
    main()
