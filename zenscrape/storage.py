import sqlite3
import json
from loguru import logger

class ZenDatabase:
    def __init__(self, db_name="zenscrape_data.db"):
        self.db_name = db_name
        # check_same_thread=False is important for high-concurrency async
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._setup()

    def _setup(self):
        """Creates the necessary tables if they don't exist"""
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS results 
                             (id INTEGER PRIMARY KEY, url TEXT, data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY)''')
        self.conn.commit()

    def is_cached(self, url: str) -> bool:
        """Checks if URL is in the cache table"""
        self.cursor.execute("SELECT 1 FROM cache WHERE url=?", (url,))
        return self.cursor.fetchone() is not None

    def mark_as_cached(self, url: str):
        """The Engine calls this after a successful request"""
        try:
            self.cursor.execute("INSERT OR IGNORE INTO cache (url) VALUES (?)", (url,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to update cache: {e}")

    def save_result(self, url: str, data_dict: dict):
        """Your callback calls this to save data"""
        try:
            self.cursor.execute("INSERT INTO results (url, data) VALUES (?, ?)", 
                                (url, json.dumps(data_dict)))
            # We also add it to cache here to be safe
            self.cursor.execute("INSERT OR IGNORE INTO cache (url) VALUES (?)", (url,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to save result: {e}")

    def close(self):
        self.conn.close()
