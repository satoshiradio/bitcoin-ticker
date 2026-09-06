from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const

class fee_applet(BaseApplet):
    TTL = const(120)
    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('fee_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://mempool.space/api/v1/fees/recommended"
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
        # Fetch data in update
        self.current_data = self.data_manager.get_cached_data(self.api_url)
        # No need to call super().update()

    async def draw(self):
        # Draw uses data fetched by update()
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Mempool Fees")

        if self.current_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            # No footer if no data
            return

        # Draw timestamp from the outer cache dictionary
        self.screen_manager.draw_footer(self.current_data.get('timestamp', None))

        # Access the nested 'data' dictionary which holds the actual API response
        fee_data = self.current_data.get('data', {})
        if not isinstance(fee_data, dict):
            print(f"[fee_applet] Unexpected data format: {fee_data}")
            self.screen_manager.draw_centered_text("Data Error")
            return

        y = 60 # Starting Y position for fee lines
        for fee_type, fee_key in [
            ("Fast:", 'fastestFee'), # Added colon for consistency
            ("Medium:", 'halfHourFee'),
            ("Slow:", 'hourFee')
        ]:
            fee = fee_data.get(fee_key) # Get fee from nested data
            fee_text = f"{fee} sat/vB" if isinstance(fee, (int, float)) else "N/A"

            # Draw label left-aligned
            self.screen_manager.draw_text(fee_type, 10, y, scale=2)
            # Draw value right-aligned
            value_width = self.screen_manager.display.measure_text(fee_text, scale=2)
            self.screen_manager.draw_text(fee_text, self.screen_manager.width - 10 - value_width, y, scale=2)
            y += 40 # Move to next line

        # screen_manager.update() is called by AppletManager or transition
