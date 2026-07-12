import random
from fake_useragent import UserAgent
from loguru import logger

class MiddlewareManager:
    def __init__(self, config):
        self.config = config
        try:
            self.ua = UserAgent()
        except Exception:
            self.ua = None
            
        # Fallback list if UserAgent() fails or for offline use
        self.fallbacks = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

    async def process_request(self, request):
        """Pre-processing before the request hits the network"""
        
        # 1. User-Agent Rotation
        if "User-Agent" not in request.headers:
            try:
                request.headers["User-Agent"] = self.ua.random if self.ua else random.choice(self.fallbacks)
            except:
                request.headers["User-Agent"] = random.choice(self.fallbacks)

        # 2. Proxy Handling (Convert List/Tor to single string for curl_cffi)
        proxy_url = None
        if self.config.use_tor:
            proxy_url = "socks5h://127.0.0.1:9050"
        elif self.config.proxy_list:
            proxy_url = random.choice(self.config.proxy_list)
        
        return proxy_url
