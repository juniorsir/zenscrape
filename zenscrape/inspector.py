import json
from urllib.parse import urljoin, urlparse
from selectolax.lexbor import LexborHTMLParser

class ZenInspector:
    def __init__(self, html: str, url: str):
        self.parser = LexborHTMLParser(html)
        self.url = url
        self.domain = urlparse(url).netloc
        
        # Strip script and style tags to sanitize DOM
        for tag in self.parser.css("script, style"):
            tag.decompose()

    def get_summary(self):
        return {
            "title": self.parser.css_first('title').text(strip=True) if self.parser.css_first('title') else "No Title",
            "metadata": self._get_meta(),
            "forms": self._get_forms(),
            "links": self._get_links(),
            "media": {
                "images": [img.attributes.get("src") for img in self.parser.css("img") if img.attributes.get("src")],
                "count": len(self.parser.css("img"))
            },
            "structure": {
                "tables": len(self.parser.css("table")),
                "json_ld": len(self.parser.css('script[type="application/ld+json"]')),
                "lists": len(self.parser.css("ul, ol")),
                "headings": self._get_heading_hierarchy(),
                "detailed_tables": self._get_tables_detailed()
            }
        }

    def _get_meta(self):
        meta = {}
        for tag in self.parser.css("meta"):
            name = tag.attributes.get("name") or tag.attributes.get("property")
            content = tag.attributes.get("content")
            if name and content:
                meta[name] = content
        return meta

    def _get_forms(self):
        """Parses standard forms, with fallback heuristics for modern JS SPAs like YouTube"""
        forms = []
        
        # 1. Standard HTML Form Parsing
        for form in self.parser.css("form"):
            f_data = {
                "action": urljoin(self.url, form.attributes.get("action", "")),
                "method": form.attributes.get("method", "GET").upper(),
                "inputs": [],
                "virtual": False
            }
            for inp in form.css("input, select, textarea"):
                name = inp.attributes.get("name")
                if name:
                    f_data["inputs"].append({
                        "name": name,
                        "type": inp.attributes.get("type", "text"),
                        "placeholder": inp.attributes.get("placeholder", ""),
                        "required": "required" in inp.attributes
                    })
            if f_data["inputs"]:
                forms.append(f_data)

        # 2. HEURISTIC FALLBACK: If 0 standard forms are found (SPA Site Mode)
        if not forms:
            # Scan for loose input fields that resemble search elements
            for inp in self.parser.css("input"):
                name_attr = inp.attributes.get("name") or inp.attributes.get("id") or inp.attributes.get("class") or ""
                name_lower = name_attr.lower()
                
                # Check if it looks like an active search field
                if any(keyword in name_lower for keyword in ["search", "query", "find", "q"]):
                    # Build a platform-specific Virtual Form
                    action_url = self.url
                    field_name = name_attr if name_attr else "q"
                    
                    if "youtube.com" in self.url:
                        action_url = "https://www.youtube.com/results"
                        field_name = "search_query" # YouTube's native query parameter
                    elif "wikipedia.org" in self.url:
                        action_url = "https://en.wikipedia.org/w/index.php"
                        field_name = "search"
                    else:
                        # Generic Fallback: target root domain /search
                        parsed = urlparse(self.url)
                        action_url = f"{parsed.scheme}://{parsed.netloc}/search"
                    
                    forms.append({
                        "action": action_url,
                        "method": "GET",
                        "inputs": [{
                            "name": field_name,
                            "type": "text",
                            "placeholder": inp.attributes.get("placeholder", "Search..."),
                            "required": False
                        }],
                        "virtual": True # Flagged as a Virtual fallback
                    })
                    break # Build only one optimized virtual form

        return forms

    def _get_links(self):
        internal, external = set(), set()
        for a in self.parser.css("a"):
            href = a.attributes.get("href")
            if not href or href.startswith(("#", "javascript:", "mailto:")): continue
            
            full_url = urljoin(self.url, href)
            if self.domain in urlparse(full_url).netloc:
                internal.add(full_url)
            else:
                external.add(full_url)
        return {"internal": list(internal), "external": list(external)}

    def _get_heading_hierarchy(self):
        headings = []
        for h in self.parser.css("h1, h2, h3"):
            headings.append({
                "tag": h.tag.upper(),
                "text": h.text(strip=True)
            })
        return headings[:15]

    def _get_tables_detailed(self):
        tables = []
        for i, table in enumerate(self.parser.css("table")):
            headers = [th.text(strip=True) for th in table.css("th") if th.text(strip=True)]
            tables.append({
                "id": i + 1,
                "columns": headers if headers else ["Generic/No Headers"]
            })
        return tables
