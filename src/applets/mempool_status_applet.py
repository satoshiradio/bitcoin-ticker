from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const

class mempool_status_applet(BaseApplet):
    TTL = const(60)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('mempool_status_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://mempool.space/api/mempool"
        self.current_data = None # Store data fetched in update()
        self.register()

    def start(self):
        # Reset data when applet starts
        self.current_data = None
        super().start()

    def stop(self):
        # No need for drawn flag handling
        super().stop()

    def register(self):
        self.data_manager.register_endpoint(self.api_url, self.TTL)

    async def update(self):
        # Fetch new data
        self.current_data = self.data_manager.get_cached_data(self.api_url)
        # No need to call super().update()

    async def draw(self):
        # Draw uses data fetched by update()
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Mempool Size")

        if self.current_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            # No footer if no data
            return

        # Draw timestamp from the outer cache dictionary
        self.screen_manager.draw_footer(self.current_data.get('timestamp', None))

        # Access the nested 'data' dictionary which holds the actual API response
        mempool_data = self.current_data.get('data', {})
        if not isinstance(mempool_data, dict):
            print(f"[mempool_status_applet] Unexpected data format: {mempool_data}")
            self.screen_manager.draw_centered_text("Data Error")
            return

        try:
            count = int(mempool_data.get("count", 0))
            vsize = int(mempool_data.get("vsize", 0))  # in vbytes

            size_mb = vsize / 1_000_000.0 # Calculate MB
            size_str = f"{size_mb:.2f} MB"
            tx_count_str = f"{count:,} TXs"

            # --- Restore Traffic Light ---
            if size_mb < 2.0:
                congestion_level = "low"
            elif size_mb < 10.0:
                congestion_level = "medium"
            else:
                congestion_level = "high"
            self.screen_manager.draw_traffic_light(congestion_level)

            # --- Draw Main Size ---
            # Restore small header text
            self.screen_manager.draw_horizontal_centered_text("Mempool Size (MB)", y=60, scale=2)
            # Restore original position
            self.screen_manager.draw_centered_text(size_str, scale=6, y_offset=0)


            # --- Draw Transaction Count ---
            # Restore original position
            self.screen_manager.draw_horizontal_centered_text(tx_count_str, y=self.screen_manager.height - 60, scale=2)

        except (ValueError, TypeError, KeyError) as e:
            print(f"[mempool_status_applet] Error parsing data: {e}")
            self.screen_manager.draw_centered_text("Data Error")

        # screen_manager.update() is called by AppletManager or transition
