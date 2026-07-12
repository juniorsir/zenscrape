import asyncio
import random
import time
from typing import List, Optional

from curl_cffi.requests import AsyncSession
from loguru import logger
from .setup_env import ensure_tor_env
from .models import ZenRequest, ZenResponse
from .config import ZenEngineConfig
from .storage import ZenDatabase  # Assuming you have the DB class

class BasePlugin:
    """
    Base class for ZenScrape plugins. 
    Inherit from this to intercept requests and responses.
    """
    async def on_request(self, request: ZenRequest) -> ZenRequest:
        return request

    async def on_response(self, response: ZenResponse) -> ZenResponse:
        return response

class ZenCrawler:
    def __init__(
        self,
        concurrency: int = 5,
        max_depth: int = 5,
        max_requests: int = 0,
        auto_tor: bool = True,
        stop_on_error: bool = False
    ):
        self.config = ZenEngineConfig.get()
        if self.config.use_tor and auto_tor:
            ensure_tor_env()

        self.concurrency = concurrency
        self.max_depth = max_depth
        self.max_requests = max_requests
        self.stop_on_error = stop_on_error

        # State Management
        self.queue = asyncio.PriorityQueue()
        self.seen_urls = set()
        self.stats = {"success": 0, "failed": 0}
        self.is_running = True
        self.plugins = []
        
        # Initialize Database if caching is enabled
        self.db = ZenDatabase(self.config.db_path) if self.config.cache_requests else None

        # Network Setup
        if self.config.use_tor:
            # Tor default SOCKS5 proxy
            if "socks5h://127.0.0.1:9050" not in self.config.proxy_list:
                self.config.proxy_list.append("socks5h://127.0.0.1:9050")
            logger.info("🛡️ Tor Tunneling Enabled")

        self.session = AsyncSession(
            impersonate=self.config.impersonate,
            verify=self.config.verify_ssl
        )

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    async def rotate_ip(self):
        """Sends a signal to Tor to get a new IP address"""
        import socket
        try:
            # Use a short timeout so the script doesn't hang
            with socket.create_connection(("127.0.0.1", 9051), timeout=2) as s:
                s.send(b'AUTHENTICATE ""\r\n')
                s.send(b'SIGNAL NEWNYM\r\n')
                response = s.recv(1024)
                if b"250 OK" in response:
                    logger.info("🔄 Tor Identity Rotated!")
                    await asyncio.sleep(3) # Wait for Tor to build the new path
                else:
                    logger.warning(f"⚠️ Tor Auth Failed: {response}")
        except Exception as e:
            logger.error(f"❌ Tor Control Port Error: {e}. (Did you start Tor with --ControlPort 9051?)")

    async def add_request(self, request: ZenRequest):
        """Standard method to add requests with depth validation"""
        if self.max_depth and request.depth > self.max_depth:
            return
        
        # We use a lock or simply check URL before putting into queue
        if request.url not in self.seen_urls:
            self.seen_urls.add(request.url)
            # Priority is negative because PriorityQueue returns the SMALLEST number first
            # We want higher priority numbers to come out first
            await self.queue.put((-request.priority, request))

    async def _worker(self):
        while self.is_running:
            if self.max_requests and self.stats["success"] >= self.max_requests:
                self.is_running = False
                break

            try:
                # Use wait_for to allow the worker to exit if the queue stays empty
                priority, request = await self.queue.get()
            except Exception:
                break

            try:
                # 1. CACHE CHECK
                if self.config.cache_requests and self.db and self.db.is_cached(request.url):
                    logger.debug(f"⏩ Skipping cached: {request.url}")
                    self.queue.task_done()
                    continue

                # 2. PLUGINS: Pre-Request
                for plugin in self.plugins:
                    request = await plugin.on_request(request)

                # 3. PREPARE NETWORK ARGS
                proxy_str = random.choice(self.config.proxy_list) if self.config.proxy_list else None
                
                req_kwargs = {
                    "method": request.method,
                    "url": request.url,
                    "timeout": request.timeout,
                    "allow_redirects": request.allow_redirects,
                    "proxy": proxy_str,
                }
                
                if request.headers: req_kwargs["headers"] = request.headers
                if request.cookies: req_kwargs["cookies"] = request.cookies
                if request.params:  req_kwargs["params"] = request.params
                if request.json_data: req_kwargs["json"] = request.json_data
                elif request.data: req_kwargs["data"] = request.data

                # 4. EXECUTE REQUEST
                response = await self.session.request(**req_kwargs)

                # 5. HANDLE RATE LIMITS
                if response.status_code == 429:
                    logger.warning(f"Rate limited (429): {request.url}. Retrying...")
                    await asyncio.sleep(random.uniform(5, 10))
                    await self.queue.put((priority, request))
                    continue

                # 6. WRAP RESPONSE
                zen_res = ZenResponse(
                    status_code=response.status_code,
                    content=response.content,
                    url=str(response.url),
                    headers=dict(response.headers)
                )
                zen_res.meta = request.meta

                # 7. PLUGINS: Post-Response
                for plugin in self.plugins:
                    zen_res = await plugin.on_response(zen_res)

                # 8. VALIDATE & CALLBACK
                if 200 <= response.status_code < 400:
                    self.stats["success"] += 1
                    if request.callback:
                        if asyncio.iscoroutinefunction(request.callback):
                            await request.callback(zen_res)
                        else:
                            request.callback(zen_res)
                    
                    # Update cache on success
                    if self.config.cache_requests and self.db:
                        self.db.mark_as_cached(request.url)
                else:
                    raise Exception(f"HTTP Error {response.status_code}")

            except Exception as e:
                self.stats["failed"] += 1
                logger.error(f"Request failed: {request.url} | Error: {e}")

                if request.retries > 0:
                    request.retries -= 1
                    await self.queue.put((priority, request))
                elif request.errback:
                    if asyncio.iscoroutinefunction(request.errback):
                        await request.errback(e, request)
                    else:
                        request.errback(e, request)

                if self.stop_on_error:
                    self.is_running = False

            finally:
                self.queue.task_done()
                # Respectful delay between requests
                await asyncio.sleep(random.uniform(0.2, 0.8))

    async def run(self):
        start_time = time.time()
        logger.info(f"ZenScrape Started. Concurrency: {self.concurrency}")

        # Start workers
        workers = [asyncio.create_task(self._worker()) for _ in range(self.concurrency)]

        # Wait for the queue to be fully processed
        await self.queue.join()
        
        # Shutdown
        self.is_running = False
        for w in workers:
            w.cancel()
            
        try:
            if hasattr(self, 'session'):
                await self.session.close()
        except Exception:
            # Ignore the 'void *' / NoneType error on cleanup
            pass

        duration = time.time() - start_time
        logger.info(f"Crawl Finished. Success: {self.stats['success']} | Failed: {self.stats['failed']} | Duration: {duration:.2f}s")
