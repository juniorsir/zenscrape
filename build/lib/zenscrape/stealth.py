import random

class StealthMiddleware:
    @staticmethod
    def get_stealth_headers(url: str):
        """Generates modern browser headers (Sec-Fetch, etc.)"""
        domain = url.split("//")[-1].split("/")[0]
        return {
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": f"https://www.google.com/search?q={domain}",
            "Accept-Language": "en-US,en;q=0.9",
        }
