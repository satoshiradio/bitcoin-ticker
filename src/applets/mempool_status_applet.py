from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc

class mempool_status_applet(BaseApplet):
    TTL = const(60)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('mempool_status_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://mempool.space/api/mempool"
        self.drawn = False
        self.register()

    def start(self):
        super().start()

    def stop(self):
        super().stop()
        self.drawn = False

    def register(self):
        self.data_manager.register_endpoint(self.api_url, self.TTL)

    async def update(self):
        gc.collect()
        return await super().update()

    async def draw(self):
        if self.drawn:
            return

        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Mempool Size")

        self.data = self.data_manager.get_cached_data(self.api_url)
        if self.data is None:
            gc.collect()
            await self.data_manager._update_cache(self.api_url)
            self.data = self.data_manager.get_cached_data(self.api_url)
            if self.data is None:
                return

        try:
            raw = self.data.get("data", {})
            count = int(raw.get("count", 0))
            vsize = int(raw.get("vsize", 0))  # in vbytes

            size_mb = vsize / 1_000_000.0
            size_str = f"{size_mb:.2f} MB"
            tx_count_str = f"{count:,} TXs"

            # Congestion traffic light
            if size_mb < 2.0:
                congestion_level = "low"
            elif size_mb < 10.0:
                congestion_level = "medium"
            else:
                congestion_level = "high"

            self.screen_manager.draw_traffic_light(congestion_level)

            # Draw small header
            self.screen_manager.draw_horizontal_centered_text("Mempool Size (MB)", y=60, scale=2)

            # Draw large MB size
            self.screen_manager.draw_centered_text(size_str, scale=6, y_offset=0)

            # Draw transaction count underneath
            self.screen_manager.draw_horizontal_centered_text(tx_count_str, y=self.screen_manager.height - 60, scale=2)


        except Exception as e:
            print("[mempool applet] Error parsing data:", e)

        self.screen_manager.draw_footer(self.data.get('timestamp', None))
        self.screen_manager.update()
        self.drawn = True
        gc.collect()
