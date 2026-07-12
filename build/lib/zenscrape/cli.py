import argparse
import asyncio
import csv
import sqlite3
import json
import sys
from .engine import ZenCrawler
from .models import ZenRequest
from .config import ZenEngineConfig, ZenSecurityConfig
from .storage import ZenDatabase

def export_db_to_csv(db_path, csv_path):
    """Converts the SQLite results table to a clean CSV file"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url, data, timestamp FROM results")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"❌ No data found in {db_path} to export.")
            return

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Data', 'Timestamp']) # Headers
            writer.writerow(['---', '---', '---'])
            for row in rows:
                writer.writerow(row)
        print(f"📊 Successfully exported {len(rows)} items to {csv_path}")
    except Exception as e:
        print(f"❌ Export failed: {e}")
    finally:
        conn.close()

async def quick_scrape(url, concurrency, tor, output):
    config = ZenSecurityConfig(use_tor=tor)
    ZenEngineConfig.setup(config)
    
    db = ZenDatabase(output)
    crawler = ZenCrawler(concurrency=concurrency)

    async def default_callback(response):
        title = response.css_first("title").text() if response.css_first("title") else "No Title"
        print(f"✅ Scraped: {response.url}")
        db.save_result(response.url, {"title": title.strip()})

    await crawler.add_request(ZenRequest(url=url, callback=default_callback))
    await crawler.run()

def main():
    parser = argparse.ArgumentParser(description="ZenScrape CLI Tool")
    
    # Notice: required=True is REMOVED from --url
    parser.add_argument("--url", help="URL to scrape")
    parser.add_argument("--concurrency", type=int, default=1, help="Parallel workers")
    parser.add_argument("--tor", action="store_true", help="Enable Tor")
    parser.add_argument("--output", default="zenscrape_results.db", help="SQLite output file")
    parser.add_argument("--csv", help="Path to export database to CSV (e.g. report.csv)")
    
    args = parser.parse_args()

    # LOGIC CHECK:
    # 1. User wants to export CSV
    if args.csv:
        export_db_to_csv(args.output, args.csv)
        # If they didn't provide a URL, we stop here.
        if not args.url:
            return

    # 2. User wants to scrape
    if args.url:
        asyncio.run(quick_scrape(args.url, args.concurrency, args.tor, args.output))
    
    # 3. User provided nothing
    if not args.url and not args.csv:
        parser.print_help()

if __name__ == "__main__":
    main()
