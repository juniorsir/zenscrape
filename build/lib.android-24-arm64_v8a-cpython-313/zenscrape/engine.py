import asyncio
import random
import time
import json
import os
from typing import List, Optional
from curl_cffi.requests import AsyncSession
from loguru import logger
from .models import ZenRequest, ZenResponse
from .config import ZenEngineConfig
from .setup_env import ensure_tor_env # Restore Import

class BasePlugin:
    async def on_request(self, request: ZenRequest) -> ZenRequest: return request
    async def on_response(self, response: ZenResponse) -> ZenResponse: return response

class AdaptivePolitenessController:
    def __init__(self, initial_delay: float = 1.0, min_delay: float = 0.1, max_delay: float = 10.0):
        self.delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.consecutive_successes = 0

    def adjust_speed(self, status_code: int, latency_ms: float):
        if status_code in [429, 503, 403]:
            self.delay = min(self.delay * 2.0, self.max_delay)
            self.consecutive_successes = 0
            logger.warning(f"⏳ Congestion detected (HTTP {status_code}). Backing off. Delay: {self.delay:.2f}s")
        elif latency_ms > 2000:
            self.delay = min(self.delay + 0.5, self.max_delay)
            self.consecutive_successes = 0
        else:
            self.consecutive_successes += 1
            if self.consecutive_successes >= 5:
                self.delay = max(self.delay - 0.1, self.min_delay)
                self.consecutive_successes = 0

class SessionRotator:
    def __init__(self, sessions_directory: str = "sessions"):
        self.sessions_dir = sessions_directory
        self.active_sessions = {}
        self._load_sessions()

    def _load_sessions(self):
        if not os.path.exists(self.sessions_dir):
            try: os.makedirs(self.sessions_dir)
            except: pass
            return

        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.sessions_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        self.active_sessions[filename] = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading session file {filename}: {e}")
        
        if self.active_sessions:
            logger.info(f"👥 Loaded {len(self.active_sessions)} identity cookies from '{self.sessions_dir}'")

    def get_session_by_index(self, index: int) -> Optional[dict]:
        if not self.active_sessions:
            return None
        keys = list(self.active_sessions.keys())
        selected_key = keys[index % len(keys)]
        logger.info(f"Worker {index} bound to identity: {selected_key}")
        return self.active_sessions[selected_key]


class ZenCrawler:
    # Set auto_tor: bool = True
    def __init__(self, concurrency: int = 5, max_depth: int = 5, delay: float = 0, auto_tor: bool = True):
        self.config = ZenEngineConfig.get()
        self.concurrency = concurrency
        self.max_depth = max_depth
        self.delay = delay
        self.queue = asyncio.PriorityQueue()
        self.seen_urls = set()
        self.is_running = True
        self.stats = {"success": 0, "failed": 0}
        self.plugins = []
        
        # RESTORE: Tor Background Auto-Starter
        if self.config.use_tor and auto_tor:
            ensure_tor_env()

        self.politeness = AdaptivePolitenessController(initial_delay=max(delay, 0.5))
        self.session_rotator = SessionRotator("instagram_sessions")

    def add_plugin(self, plugin: BasePlugin):
        self.plugins.append(plugin)

    async def add_request(self, request: ZenRequest):
        if self.max_depth and request.depth > self.max_depth: return
        if request.url not in self.seen_urls:
            self.seen_urls.add(request.url)
            await self.queue.put((-request.priority, request))

    async def _worker(self, worker_id: int):
        proxy_str = "socks5h://127.0.0.1:9050" if self.config.use_tor else None
        worker_session = AsyncSession(
            impersonate=self.config.impersonate,
            proxies={"http": proxy_str, "https": proxy_str} if proxy_str else None
        )

        worker_cookies = self.session_rotator.get_session_by_index(worker_id)
        if worker_cookies:
            worker_session.cookies.update(worker_cookies)

        while self.is_running:
            try:
                try:
                    priority, request = await self.queue.get()
                except asyncio.CancelledError:
                    break

                try:
                    current_delay = self.politeness.delay * random.uniform(0.8, 1.2)
                    await asyncio.sleep(current_delay)

                    for plugin in self.plugins:
                        request = await plugin.on_request(request)

                    req_kwargs = {
                        "method": request.method,
                        "url": request.url,
                        "timeout": 30
                    }

                    if request.headers: req_kwargs["headers"] = request.headers
                    if request.cookies: req_kwargs["cookies"] = request.cookies
                    if request.params:  req_kwargs["params"] = request.params

                    if request.json_data:
                        req_kwargs["json"] = request.json_data
                    elif request.data:
                        if isinstance(request.data, str):
                            try: req_kwargs["data"] = json.loads(request.data)
                            except: req_kwargs["data"] = request.data
                        else:
                            req_kwargs["data"] = request.data

                    start_ts = time.time()
                    response = await worker_session.request(**req_kwargs)
                    latency = (time.time() - start_ts) * 1000

                    self.politeness.adjust_speed(response.status_code, latency)

                    zen_res = ZenResponse(
                        status_code=response.status_code,
                        content=response.content,
                        url=str(response.url),
                        headers=dict(response.headers)
                    )
                    zen_res.meta = request.meta

                    for plugin in self.plugins:
                        zen_res = await plugin.on_response(zen_res)

                    if request.callback:
                        if asyncio.iscoroutinefunction(request.callback):
                            await request.callback(zen_res)
                        else:
                            request.callback(zen_res)

                    logger.success(f"👷 Worker {worker_id} | HTTP {response.status_code} | {latency:4.0f}ms | {request.url}")
                    self.stats["success"] += 1

                except Exception as e:
                    logger.error(f"👷 Worker {worker_id} FAILED | {request.url} | {str(e)[:50]}")
                    self.stats["failed"] += 1
                finally:
                    self.queue.task_done()

            except Exception:
                pass

        try: await worker_session.close()
        except: pass

    async def run(self):
        start_time = time.time()
        mode = "TOR 🛡️" if self.config.use_tor else "DIRECT 🌐"
        logger.info(f"🚀 ZenScrape Starting | Mode: {mode} | Workers: {self.concurrency}")

        workers = [asyncio.create_task(self._worker(i)) for i in range(self.concurrency)]
        await self.queue.join()

        self.is_running = False
        for w in workers:
            w.cancel()

        await asyncio.gather(*workers, return_exceptions=True)

        duration = time.time() - start_time
        print("\n" + "="*50)
        print(f"📊 ZEN SCRAPE COMPLETE")
        print("="*50)
        print(f"✅ Success:   {self.stats['success']}")
        print(f"❌ Failed:    {self.stats['failed']}")
        print(f"⏱️  Duration:  {duration:.2f}s")
        print(f"🚀 Speed:     {self.stats['success']/max(duration,1):.2f} req/s")
        print("="*50 + "\n")
