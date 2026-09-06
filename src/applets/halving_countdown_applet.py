from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const

class halving_countdown_applet(BaseApplet):
    TTL = const(120)
    BLOCKS_PER_HALVING = const(210_000)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('halving_countdown_applet', screen_manager)
        self.data_manager = data_manager
        # Share the same endpoint as block_height_applet to avoid duplicate fetches
        self.api_url = "https://mempool.space/api/v1/blocks/tip/height"
        self.current_data = None # Store data fetched in update()
        self.register()

    def start(self):
        self.current_data = None
        super().start()

    def stop(self):
        super().stop()

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
        self.current_data = self.data_manager.get_cached_data(self.api_url)

    async def draw(self):
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Halving Countdown")

        if self.current_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            # No footer if no data
        else:
            self.screen_manager.draw_footer(self.current_data.get('timestamp', None))
            try:
                current_height = int(self.current_data.get('data', 0))
                if current_height > 0:
                    blocks_remaining = self.calculate_next_halving(current_height)
                    self.screen_manager.draw_centered_text(f"{blocks_remaining:,}")
                else:
                    self.screen_manager.draw_centered_text("N/A") # Handle case where height is 0 or missing
            except (ValueError, TypeError) as e:
                print("Error processing block height:", e)
                self.screen_manager.draw_centered_text("Error") # Display error on screen
