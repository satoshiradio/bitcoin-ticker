from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc

class fee_applet(BaseApplet):
    TTL = const(120)
    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('fee_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://mempool.space/api/v1/fees/recommended"
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
        return await super().update()

    async def draw(self):
        if self.drawn:
            return
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Mempool Fees")

        self.data = self.data_manager.get_cached_data(self.api_url)
        if self.data is None:
            print("No data")
            gc.collect()
            await self.data_manager._update_cache(self.api_url)
            self.data = self.data_manager.get_cached_data(self.api_url)
            if self.data is None:
                return

        self.screen_manager.draw_footer(self.data.get('timestamp',None))
        self.data = self.data.get('data')
        y = 60
        for fee_type, fee_key in [
            ("Fast", 'fastestFee'),
            ("Medium", 'halfHourFee'),
            ("Slow", 'hourFee')
        ]:
            fee = self.data.get(fee_key, 'N/A')
            self.screen_manager.draw_text(f"{fee_type}:", 10, y, scale=2)
            fee_text = f"{fee} sat/vB" if isinstance(fee, (int, float)) else str(fee)
            self.screen_manager.draw_text(fee_text, self.screen_manager.width - 10 - self.screen_manager.display.measure_text(fee_text, 2), y, scale=2)
            y += 40
        self.screen_manager.update()
        self.drawn = True
