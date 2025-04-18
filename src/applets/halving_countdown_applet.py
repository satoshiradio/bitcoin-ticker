from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc

class halving_countdown_applet(BaseApplet):
    TTL = const(120)
    BLOCKS_PER_HALVING = const(210_000)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('halving_countdown_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://mempool.space/api/blocks/tip/height"
        self.drawn = False
        self.register()

    def start(self):
        super().start()

    def stop(self):
        super().stop()
        self.drawn = False

    def register(self):
        self.data_manager.register_endpoint(self.api_url, self.TTL)

    def calculate_next_halving(self, current_height):
        # Calculate how many halvings have occurred
        halvings_occurred = current_height // self.BLOCKS_PER_HALVING
        # Calculate next halving block height
        next_halving_height = (halvings_occurred + 1) * self.BLOCKS_PER_HALVING
        # Calculate blocks remaining
        blocks_remaining = next_halving_height - current_height
        return blocks_remaining

    async def update(self):
        gc.collect()
        return await super().update()

    async def draw(self):
        if self.drawn:
            return

        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Halving Countdown")
        self.data = self.data_manager.get_cached_data(self.api_url)

        if self.data is None:
            gc.collect()
            await self.data_manager._update_cache(self.api_url)
            self.data = self.data_manager.get_cached_data(self.api_url)
            if self.data is None:
                return

        try:
            current_height = int(self.data.get('data', 0))
            blocks_remaining = self.calculate_next_halving(current_height)
            self.screen_manager.draw_centered_text(f"{blocks_remaining:,}")
        except (ValueError, TypeError) as e:
            print("Error processing block height:", e)

        self.screen_manager.draw_footer(self.data.get('timestamp', None))
        self.data = None
        self.screen_manager.update()
        self.drawn = True
        gc.collect()
