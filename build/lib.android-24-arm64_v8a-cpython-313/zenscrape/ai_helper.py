import asyncio
from selectolax.lexbor import LexborHTMLParser
from urllib.parse import urljoin
from .engine import ZenCrawler
from .models import ZenRequest
from .config import ZenEngineConfig, ZenSecurityConfig

class ZenAIHelper:
    @staticmethod
    def clean_html_for_llm(html: str, url: str) -> str:
        """Strips structural junk and extracts clean text + absolute image links"""
        parser = LexborHTMLParser(html)
        
        # 1. Decompose non-readable structural tags
        junk_tags = ["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript", "svg", "form"]
        for tag in parser.css(", ".join(junk_tags)):
            tag.decompose()

        # 2. Extract content and format images/tables/headings as Markdown
        content_blocks = []
        for el in parser.css("h1, h2, h3, p, li, table, img"): # Added 'img'
            
            # --- IMAGE EXTRACTION ---
            if el.tag == "img":
                src = el.attributes.get("src")
                alt = el.attributes.get("alt", "Image")
                if src:
                    # Automatically resolve relative links to full URL
                    abs_src = urljoin(url, src)
                    # Don't add track/pixel/icon images (usually less than 30px)
                    width = el.attributes.get("width", "100")
                    if "pixel" not in src and width.isdigit() and int(width) > 30:
                        content_blocks.append(f"\n![{alt}]({abs_src})\n")
                continue

            # --- TEXT EXTRACTION ---
            text = el.text(strip=True)
            if not text: continue
            
            if el.tag == "h1":
                content_blocks.append(f"\n# {text}\n")
            elif el.tag == "h2":
                content_blocks.append(f"\n## {text}\n")
            elif el.tag == "h3":
                content_blocks.append(f"\n### {text}\n")
            elif el.tag == "li":
                content_blocks.append(f"* {text}")
            else:
                content_blocks.append(text)

        return "\n".join(content_blocks).strip()

    @classmethod
    async def browse(cls, url: str, use_tor: bool = False) -> dict:
        ZenEngineConfig.setup(ZenSecurityConfig(use_tor=use_tor, impersonate="chrome110"))
        
        result = {"url": url, "title": "", "text": "", "error": None}
        crawler = ZenCrawler(concurrency=1)

        async def callback(response):
            result["title"] = response.css_first("title").text(strip=True) if response.css_first("title") else "N/A"
            # Pass response.url to resolve image links correctly
            result["text"] = cls.clean_html_for_llm(response.text, response.url)

        await crawler.add_request(ZenRequest(url=url, callback=callback))
        await crawler.run()
        return result
