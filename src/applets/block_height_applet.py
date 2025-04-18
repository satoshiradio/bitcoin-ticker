from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc

class block_height_applet(BaseApplet):
    TTL = const(120)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('block_height_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://mempool.space/api/v1/blocks/tip/height"
        self.cached_data = None
        self.drawn = False
        self.register()

    def start(self):
        super().start()

    def stop(self):
        self.cached_data = None
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
        self.screen_manager.draw_header("Bitcoin Block Height")
        self.data = self.data_manager.get_cached_data(self.api_url)
        if self.data is None:
            print("No data available, attempting to update cache.")
            gc.collect()
            await self.data_manager._update_cache(self.api_url)
            self.data = self.data_manager.get_cached_data(self.api_url)
            if self.data is None:
                return
        self.screen_manager.draw_footer(self.data.get('timestamp', None))
        height = self.data.get('data')
        if height is not None:
            self.screen_manager.draw_centered_text(f"{int(height):,}")  # Let it use default scale=8
        height = None
        self.data = None
        self.screen_manager.update()
        self.drawn = True

        gc.collect()
