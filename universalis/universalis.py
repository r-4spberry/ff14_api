from collections import deque
import json
import time
import aiohttp
import asyncio
from pathlib import Path
import warnings


class RateLimiter:
    def __init__(self, rate_limit, time_window):
        self.rate_limit = rate_limit  # Maximum number of requests
        self.time_window = time_window  # Time window in seconds
        self.tokens = deque()  # Stores timestamps of recent requests

    async def wait_for_token(self):
        while True:
            now = time.time()
            # Remove tokens older than the time window
            while self.tokens and self.tokens[0] <= now - self.time_window:
                self.tokens.popleft()
            # If we have space for a new token, add it and proceed
            if len(self.tokens) < self.rate_limit:
                self.tokens.append(now)
                return
            # Otherwise, wait until the oldest token is freed
            await asyncio.sleep(self.tokens[0] + self.time_window - now)


items_file = "items.json"
CONNECTIONS = 8


class Universalis:
    def __init__(self, lang="en"):
        script_dir = Path(__file__).parent
        self.rate_limiter = RateLimiter(rate_limit=25, time_window=1)
        self.items_file = script_dir / "items.json"
        self.session = None
        self.request_queue = asyncio.Queue()
        self._worker_task = None
        self.connection_semaphore = asyncio.Semaphore(CONNECTIONS)
        self.lang = lang

    async def _get_items(self):
        items = self.load_items()
        marketable = await self.marketable_items()  # Await marketable items
        marketable_set = set(marketable)
        # Filter the items based on the marketable IDs
        filtered_items = {
            id: names for id, names in items.items() if int(id) in marketable_set
        }
        print(3)
        return filtered_items

    def load_items(self):
        with open(self.items_file, encoding="utf-8") as f:
            return json.load(f)

    def item_from_id(self, item_id):
        return self.items[str(item_id)][self.lang]

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self._worker_task = asyncio.create_task(self._process_requests())
        # Now that the session is available, load items
        self.items = await self._get_items()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        await self.session.close()

    async def _process_requests(self):
        while True:
            request = await self.request_queue.get()
            try:
                await self.rate_limiter.wait_for_token()
                async with self.session.get(
                    request["url"], params=request.get("params")
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if request["callback"]:
                        request["callback"](data)
            except Exception as e:
                print(f"Request failed: {e}")
            finally:
                self.request_queue.task_done()

    async def _make_request(self, url, params=None):
        await self.rate_limiter.wait_for_token()
        async with self.connection_semaphore:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def data_centers(self):
        url = "https://universalis.app/api/v2/data-centers"
        return await self._make_request(url)

    async def marketable_items(self):
        url = "https://universalis.app/api/v2/marketable"
        return await self._make_request(url)

    async def worlds(self):
        url = "https://universalis.app/api/v2/worlds"
        return await self._make_request(url)

    async def current_data(self, worldDcRegion, itemIds):
        itemIds = ",".join(map(str, itemIds))
        url = f"https://universalis.app/api/v2/{worldDcRegion}/{itemIds}"
        return await self._make_request(url)

    async def most_recently_updated(self, world_id, data_center=None, entries=None):
        if entries is None:
            entries = 50
        elif entries > 200:
            warnings.warn(f"Entries must be less than 200, defaulting to 200")
            entries = 200

        params = {"world": world_id, "entries": entries}
        if data_center:
            params["dataCenter"] = data_center
        url = "https://universalis.app/api/v2/extra/stats/most-recently-updated"
        return await self._make_request(url, params)

    def add_request_to_queue(self, url, callback=None, params=None):
        self.request_queue.put_nowait(
            {"url": url, "callback": callback, "params": params}
        )
