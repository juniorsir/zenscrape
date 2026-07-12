import json
from .models import ZenRequest

class ZenAutomator:
    @staticmethod
    def google_search(query: str):
        """Builds a Google search request"""
        return ZenRequest(
            url="https://www.google.com/search",
            method="GET",
            params={"q": query, "num": 100}
        )

    @staticmethod
    def instagram_login(username, password):
        """Builds the payload for Instagram Login"""
        # Note: IG requires specific headers and CSRF tokens
        return ZenRequest(
            url="https://www.instagram.com/accounts/login/ajax/",
            method="POST",
            data={
                "username": username,
                "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}",
                "queryParams": {},
                "optIntoOneTap": "false"
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/"
            }
        )
