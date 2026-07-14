
---

# 🛡️ ZenScrape Elite

`ZenScrape` is a high-performance, asynchronous, and fully anonymized web scraping framework and command-line intelligence tool. Designed to operate seamlessly on resource-constrained environments like high-performance **production servers (WSL/Linux/macOS)**, ZenScrape focuses on stealth, data integrity, and automated discovery.

---

## 🧭 Core Architectural Advancements

| Feature | Engineering Implementation | Benefit |
| :--- | :--- | :--- |
| **WAF Bypass** | `curl_cffi` C-level TLS Impersonation | Mimics Chrome and Safari JA3 fingerprints to pass Cloudflare/Akamai. |
| **Absolute Anonymity** | Integrated SOCKS5h Tor Routing | Automatically boots and monitors local Tor processes, forcing remote DNS resolution. |
| **Zero Cookie Leaks** | Worker-Bound Private Sessions | Each concurrency thread holds its own isolated `AsyncSession` to prevent identity overlap. |
| **Congestion Control** | AIMD Adaptive Politeness Controller | Dynamically speeds up or backs off crawling based on server response latency/status codes. |
| **Self-Healing Selectors** | Heuristic Semantic Parsing | Fallback routines that locate HTML elements by structural similarity when classes change. |
| **Resumable Crawls** | SQLite Persistent Caching | Remembers completed tasks to prevent redundant downloads on restart. |
| **LLM Token-Savings** | Structural Markdown Sanitizer | Strips layout bloat (header/footer/CSS/JS) to deliver optimized context to AI models. |

---

## 📦 Installation & Setup

### 1. Simple Installation (From PyPI)
```bash
pip install zenscrape
```

### 2. From Source (Local Development / Compilation)
For maximum speed and IP protection, you can compile the Python source code directly into **native C-binaries** on your machine:
```bash
git clone https://github.com/juniorsir/zenscrape.git
cd zenscrape
pip install cython setuptools wheel
python setup.py build_ext --inplace
pip install -e .
```

---

## 💻 Command Line Interface (CLI) Reference

ZenScrape features an interactive terminal client. 

```bash
zenscrape --url [URL] [OPTIONS]
```

### Global Options

*   `--url [URL]`: The target website address.
*   `--concurrency [N]`: Number of parallel workers. (Set to `0` for **Smart Auto-Calculated Concurrency** tailored to your hardware).
*   `--inspect`: Starts the interactive **Site Discovery & Form-Filler Mode**.
*   `--tor`: Activates automatic background Tor SOCKS5h routing.
*   `--profile [NAME]`: Browser signature profile to emulate (`chrome110`, `safari15_5`, `firefox107`).
*   `--css [SELECTOR]`: Target CSS selector to extract.
*   `--depth [N]`: Crawl depth (e.g., `1` to follow all links on the target page).
*   `--delay [N]`: Artificial sleep delay between requests (with automatic random jitter).
*   `--output [FILE]`: Target SQLite database path (Defaults to `zenscrape_results.db`).
*   `--no-cache`: Force download of cached pages.
*   `--csv`: Standalone command to convert SQLite database to an Excel-friendly CSV.
*   `--json`: Standalone command to convert SQLite database to a clean, nested JSON.

---

## 🛠️ CLI Usage Examples

### A. Automatic Depth-Crawling with Performance Guards
Crawl a website up to 1 level deep using an optimized worker count calculated automatically for your phone/CPU:
```bash
zenscrape --url https://books.toscrape.com --depth 1
```

### B. Anonymous CSS Data Extraction
Extract book prices anonymously over the Tor network:
```bash
zenscrape --url https://books.toscrape.com --css ".price_color" --tor
```

### C. Standard Form-Based POST/GET Submissions
Log in to an endpoint or submit query parameters securely:
```bash
zenscrape --url https://example.com/login --method POST --data '{"user":"admin","pass":"secret"}' --tor
```

### D. Exporting Collected Data
Convert your scraped database into ready-to-use CSV or JSON formats:
```bash
# Export to CSV
zenscrape --output zenscrape_results.db --csv

# Export to JSON
zenscrape --output zenscrape_results.db --json
```

---

## 🔍 Interactive "Discovery Mode" (Scouting)

If you run ZenScrape with the `--inspect` flag, it acts like a security scanner. It maps out the page’s links, media elements, forms, and input fields (including field types like `password`, `text`, or `email`) and presents an interactive action menu:

```bash
zenscrape --url https://google.com --inspect --tor
```

### The Interactive Menu:
```text
════════════════════════════════════════════════════════════
📡 SITE INTELLIGENCE: Google
════════════════════════════════════════════════════════════
🔗 Links:  21 Internal | 4 External
🏗️  Forms:  1 detected
🖼️  Media:  13 Images

📝 INPUTS DETECTED:
  [Form 1] GET -> https://google.com/search
    Fields: q (text), btnK (submit)

════════════════════════════════════════════════════════════
CHOICES:
1. [TITLES]   Extract Page Titles
2. [MAP]      Extract all Internal Links
3. [FORMS]    Extract Form Actions
4. [IMAGES]   Extract all Image URLs
5. [DEEP]     Start Recursive Crawl (Depth 1)
6. [SUBMIT]   Fill and Submit Detected Form
7. [AUDIT]    Deep Structural Audit
q. [EXIT]

Action (1-7): 
```

*   **Option 6 (Form-Filler)**: ZenScrape will prompt you to enter values for all detected non-hidden form fields, assemble the payload, and submit it anonymously.
*   **Option 7 (Structural Audit)**: Maps out the heading hierarchy (`H1 -> H2 -> H3`), SEO/OG metadata, and parses detected `<table>` columns.

---

## 🤖 Developer API (Using inside Python)

You can import `zenscrape` directly into your Python scripts or AI Assistant agents.

### 1. Standard Crawl
```python
import asyncio
from zenscrape import ZenCrawler, ZenRequest

async def parse_quote(response):
    for quote in response.css(".quote"):
        print(quote.css_first(".text").text())

async def main():
    crawler = ZenCrawler(concurrency=2)
    await crawler.add_request(ZenRequest(
        url="https://quotes.toscrape.com", 
        callback=parse_quote
    ))
    await crawler.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Autonomous AI Assistant Research Helper (`ZenAIHelper`)
Provides token-optimized Markdown summaries and extracted image links directly to multi-modal Large Language Models (LLMs):

```python
import asyncio
from zenscrape import ZenAIHelper

async def ai_agent_task():
    # Browse anonymously, sanitize HTML, extract clean Markdown + Images
    scraped_context = await ZenAIHelper.browse("https://en.wikipedia.org/wiki/Termux", use_tor=True)
    
    # Deliver structured context directly to OpenAI/Claude context windows
    print(f"Source Title: {scraped_context['title']}")
    print(f"Markdown Content:\n{scraped_context['text'][:1000]}")

asyncio.run(ai_agent_task())
```

---

## 🔌 Writing Plugins
Extend the framework's capability by intercepting request and response cycles.

```python
# plugins/anti_block.py
import asyncio
from zenscrape import BasePlugin

class AntiBlockPlugin(BasePlugin):
    async def on_response(self, response):
        if response.status_code == 429:
            print("🚫 Rate limit hit. Cooling down...")
            await asyncio.sleep(10)
        return response

# Register the plugin:
# crawler = ZenCrawler()
# crawler.add_plugin(AntiBlockPlugin())
```

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.
