from typing import Dict, Any, Optional, Callable, Union
from pydantic import BaseModel
from selectolax.lexbor import LexborHTMLParser

class ZenRequest(BaseModel):
    url: str
    method: str = "GET"
    # Networking & Auth
    headers: Optional[Dict[str, str]] = {}
    cookies: Optional[Dict[str, str]] = {}
    params: Optional[Dict[str, Any]] = {}
    data: Optional[Union[str, Dict, bytes]] = None
    json_data: Optional[Dict] = None
    # Behavior Controls
    priority: int = 0
    retries: int = 3
    timeout: int = 30
    allow_redirects: bool = True
    max_redirects: int = 5

    # Crawler Logic
    callback: Optional[Callable] = None
    errback: Optional[Callable] = None
    meta: Dict[str, Any] = {}          
    depth: int = 0

    def __lt__(self, other):
        """Allows the PriorityQueue to sort requests by URL if priorities are equal"""
        return self.url < other.url

class ZenResponse:
    def __init__(self, status_code: int, content: bytes, url: str, headers: Dict):
        self.status_code = status_code
        self.content = content
        self.url = url
        self.headers = headers
        self.meta: Dict[str, Any] = {}  # Set by engine
        self._selector = None

    @property
    def text(self) -> str:
        """Returns the response body as a string."""
        return self.content.decode("utf-8", errors="ignore")

    @property
    def selector(self):
        """Internal parser engine."""
        if not self._selector:
            self._selector = LexborHTMLParser(self.text)
        return self._selector

    def css(self, query: str):
        """Apply a CSS selector to the response."""
        return self.selector.css(query)

    def css_first(self, query: str, default=None):
        """Apply a CSS selector and return the first match."""
        return self.selector.css_first(query, default=default)

    def json(self) -> Dict:
        """Parse response as JSON."""
        import json
        return json.loads(self.text)
