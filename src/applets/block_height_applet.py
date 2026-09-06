from system_applets.base_applet import DataApplet
from micropython import const


class block_height_applet(DataApplet):
    TTL = const(120)
    API_URL = "https://mempool.space/api/v1/blocks/tip/height"
    HEADER = "Bitcoin Block Height"
    DICT_PAYLOAD = False  # The endpoint returns a bare integer

    def payload(self):
        # A bare integer, so there is no empty dict to fall back on.
        return self.current_data.get('data') if isinstance(self.current_data, dict) else None

    def render(self, height):
        if height is None:
            self.screen_manager.draw_centered_text("N/A")
            return
        try:
            # Format with commas
            self.screen_manager.draw_centered_text(f"{int(height):,}")
        except (ValueError, TypeError):
            self.screen_manager.draw_centered_text("Error")
