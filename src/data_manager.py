import uasyncio as asyncio
import urequests
import time
import json
import os
import uhashlib
import ubinascii
from pimoroni import RGBLED
from utils import atomic_write


class DataManager:
    """
    Manages periodic fetching and caching of data from registered endpoints.
    Caches data to the local filesystem and handles optional LED indications.
    """

    def __init__(
        self,
        ttl_default: int = 60,
        cache_dir: str = "cache",
        led=RGBLED(6, 7, 8)
    ) -> None:
        """
        :param ttl_default: Default time-to-live (seconds) for all endpoints unless overridden.
        :param cache_dir:   Directory where fetched data is cached.
        :param led:         An optional RGBLED object to signal fetch states.
        """
        self.ttl_default = ttl_default
        self.cache_dir = cache_dir
        self.led = led

        self.endpoint_registry = {}
        self.retry_count = 3
        self.timeout = 10  # seconds
        # Bumped on every successful cache update so consumers (e.g. the applet
        # render loop) can tell whether anything actually changed.
        self.revision = 0

        # Create the cache directory if it doesn't exist
        if not self._exists(self.cache_dir):
            self._mkdir(self.cache_dir)

    def _exists(self, path: str) -> bool:
        """
        Check if a path (file or directory) exists.
        :param path: Filesystem path to check.
        :return: True if exists, else False.
        """
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def _mkdir(self, path: str) -> None:
        """
        Create a directory.
        :param path: Directory path to create.
        """
        os.mkdir(path)

    def _set_led(self, state: str) -> None:
        """
        Set LED state for debugging or status indication.
        :param state: A string describing current operation.
        """
        if self.led is None:
            return

        # You can customize these colors based on your preference
        if state == "getting_data":
            self.led.set_rgb(255, 128, 0)     # Orange
        elif state == "error":
            self.led.set_rgb(255, 0, 0)       # Red
        elif state == "success":
            self.led.set_rgb(0, 255, 0)       # Green
        elif state == "off":
            self.led.set_rgb(0, 0, 0)
        else:
            self.led.set_rgb(0, 0, 0)

    def _get_hash(self, url: str) -> str:
        """
        Generate a hash for the URL using SHA256 (first 8 hex chars).
        Uses uhashlib which is built into MicroPython on RP2040.
        :param url: The URL to hash.
        :return: A hash string (8 hex characters, ~4 billion unique values).
        """
        url_bytes = url.encode('utf-8')
        h = uhashlib.sha256(url_bytes)
        return ubinascii.hexlify(h.digest()).decode('ascii')[:8]

    def _get_cache_file_path(self, url: str) -> str:
        """
        Generate the file path for the cached data, based on the URL hash.
        :param url: The endpoint URL.
        :return: The absolute filesystem path for the cache file.
        """
        file_name = f"{self._get_hash(url)}.json"
        return f"{self.cache_dir}/{file_name}"

    def register_endpoint(self, url, ttl=None):
        """
        Register an endpoint to be polled with a specific TTL.
        If the same endpoint is registered multiple times, the smallest TTL is used.
        :param url: The endpoint URL to fetch from.
        :param ttl: Time-to-live in seconds before a new fetch is forced.
        """
        if ttl is None:
            ttl = self.ttl_default

        if url not in self.endpoint_registry:
            self.endpoint_registry[url] = {
                'ttl': ttl,
                'last_update': 0,  # Initialize last_update to 0 to force initial fetch
                # Parsed cache entry, kept in RAM so applets never re-read the file
                'data': self._read_cache_file(url)
            }
        else:
            # Use the minimum TTL if multiple registrations occur
            if ttl < self.endpoint_registry[url]['ttl']:
                self.endpoint_registry[url]['ttl'] = ttl
            # Do not reset last_update if already registered, to respect existing cache state
            # unless we specifically want to force re-fetch on re-registration logic.
            # For now, assume existing last_update is fine.

    def _read_cache_file(self, url):
        """
        Read the on-disk cache entry for a URL once, at registration time.
        A missing or truncated file is treated as "no cache", never as an error.
        :param url: The endpoint URL whose cache file should be read.
        :return: Parsed cache entry if readable, otherwise None.
        """
        try:
            with open(self._get_cache_file_path(url), 'r') as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            print(f"[DataManager] No usable cache file for {url}: {e}")
            return None

    def get_cached_data(self, url):
        """
        Retrieve the in-memory cache entry for a specific URL.
        :param url: The URL whose cached data should be retrieved.
        :return: Parsed JSON data if available, otherwise None.
        """
        entry = self.endpoint_registry.get(url)
        if entry is None:
            return None
        return entry['data']

    async def _fetch_data(self, url: str):
        """
        Fetch data from an API endpoint with a retry mechanism and exponential backoff.
        :param url: The endpoint URL to fetch.
        :return: The parsed JSON data if successful, otherwise None.
        """
        print(f"[DataManager] Fetching data from {url}")
        response = None
        for attempt in range(self.retry_count):
            try:
                self._set_led("getting_data")
                response = urequests.get(url, timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0 (Linux; ARM) MicroPython/1.0"})
                if response.status_code == 200:
                    data = response.json()
                    self._set_led("success")
                    print(f"[DataManager] Successfully fetched data from: {url}") # Less verbose log
                    return data
                else:
                    print(f"[DataManager] HTTP Error: {response.status_code}")
                    self._set_led("error")
            except OSError as e:
                print(f"[DataManager] Network error (attempt {attempt + 1}/{self.retry_count}): {e}")
                self._set_led("error")
                # Exponential backoff before the next attempt
                await asyncio.sleep(2 ** attempt)
            except ValueError as e:
                print(f"[DataManager] JSON parsing error: {e}")
                self._set_led("error")
                return None
            except Exception as e:
                print(f"[DataManager] Unexpected error: {e}")
                self._set_led("error")
                return None
            finally:
                # Ensure response is closed to free resources
                if response is not None:
                    response.close()
                self._set_led("off")

        print(f"[DataManager] Failed to fetch data from {url} after {self.retry_count} attempts.")
        return None

    async def _update_cache(self, url: str) -> None:
        """
        Periodically update the cache for a specific endpoint.
        :param url: The endpoint URL to keep updated.
        """
        while True:
            ttl = self.endpoint_registry[url]['ttl']
            try:
                current_time = time.time()
                last_update = self.endpoint_registry[url]['last_update']
                data = None

                # Check if the TTL has expired OR if it's the very first run (last_update == 0)
                if last_update == 0 or (current_time - last_update > ttl):
                    data = await self._fetch_data(url)
                    if data is not None:
                        # Update last_update only after a successful fetch and write
                        new_timestamp = time.time() # Use fresh timestamp for successful update
                        self.endpoint_registry[url]['last_update'] = new_timestamp
                        metadata = {
                            'data': data,
                            'timestamp': current_time
                        }
                        # Keep the parsed entry in RAM and mirror it to flash
                        self.endpoint_registry[url]['data'] = metadata
                        self.revision += 1
                        atomic_write(self._get_cache_file_path(url), metadata)

                # Sleep for half the TTL to allow for more frequent checks
                # while still respecting the TTL for fresh data
                # For initial fetch (last_update was 0), a shorter sleep might be better if fetch failed.
                # However, _fetch_data has retries. If it returns None, it means all retries failed.
                sleep_duration = ttl // 2
                if last_update == 0 and data is None: # If initial fetch for this URL failed in this cycle
                    sleep_duration = min(60, ttl // 2 if ttl // 2 > 0 else 60) # Retry sooner, ensure positive sleep
            except Exception as e:
                # One misbehaving endpoint must never take down the other pollers
                print(f"[DataManager] Update task error for {url}: {e}")
                sleep_duration = ttl or 30

            await asyncio.sleep(sleep_duration)

    async def run(self) -> None:
        """
        Start polling all registered endpoints concurrently.
        This method should be scheduled as a background task, e.g.:
            asyncio.create_task(data_manager.run())
        """
        print("[DataManager] Starting data manager")
        tasks = [
            asyncio.create_task(self._update_cache(url))
            for url in self.endpoint_registry
        ]
        if not tasks:
            print("[DataManager] No endpoints registered. DataManager run loop will be idle.")
        else:
            print(f"[DataManager] Starting _update_cache tasks for URLs: {list(self.endpoint_registry.keys())}")
        await asyncio.gather(*tasks)
