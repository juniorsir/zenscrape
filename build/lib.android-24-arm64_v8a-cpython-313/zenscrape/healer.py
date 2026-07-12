import re
from typing import Optional, List
from selectolax.lexbor import LexborHTMLParser, LexborNode

class SelfHealingEngine:
    @staticmethod
    def find_fallback(parser: LexborHTMLParser, target_tag: str, fallback_hints: List[str]) -> Optional[LexborNode]:
        """
        Attempts to locate elements by scanning structural clues, 
        text patterns, or alternative attributes when primary CSS classes break.
        """
        # 1. Strategy A: Check common semantic data-attributes
        for hint in fallback_hints:
            selector = f"{target_tag}[itemprop*='{hint}'], {target_tag}[aria-label*='{hint}'], {target_tag}[name*='{hint}']"
            node = parser.css_first(selector)
            if node:
                return node

        # 2. Strategy B: Heuristic text content search (e.g., finding buttons containing "Submit")
        for node in parser.css(target_tag):
            text_content = node.text(strip=True).lower()
            for hint in fallback_hints:
                if hint.lower() in text_content:
                    return node

        # 3. Strategy C: Structural containment search (parents or containers)
        for hint in fallback_hints:
            container = parser.css_first(f"[class*='{hint}'], [id*='{hint}']")
            if container:
                # Find the nearest child matching the requested tag
                child = container.css_first(target_tag)
                if child:
                    return child

        return None
