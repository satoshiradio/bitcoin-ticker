from system_applets.base_applet import DataApplet
from micropython import const


class halving_countdown_applet(DataApplet):
    TTL = const(120)
    BLOCKS_PER_HALVING = const(210_000)
    # Share the same endpoint as block_height_applet to avoid duplicate fetches
    API_URL = "https://mempool.space/api/v1/blocks/tip/height"
    HEADER = "Bitcoin Halving Countdown"
    DICT_PAYLOAD = False  # The endpoint returns a bare integer

    def payload(self):
        # A bare integer, so there is no empty dict to fall back on.
        return self.current_data.get('data', 0) if isinstance(self.current_data, dict) else 0

    def render(self, height):
        try:
            current_height = int(height)
        except (ValueError, TypeError) as e:
            print("Error processing block height:", e)
            self.screen_manager.draw_centered_text("Error")
            return

        if current_height <= 0:
            self.screen_manager.draw_centered_text("N/A")
            return

        # Blocks left until the next multiple of BLOCKS_PER_HALVING
        blocks_remaining = self.BLOCKS_PER_HALVING - (current_height % self.BLOCKS_PER_HALVING)
        self.screen_manager.draw_centered_text(f"{blocks_remaining:,}")
