from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import time

class moscow_time_applet(BaseApplet):
    TTL = const(120)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('moscow_time_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
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
        # Register with default TTL from BaseApplet if not specified otherwise
        self.data_manager.register_endpoint(self.api_url, self.TTL)

    async def update(self):
        # Fetch data in update
        self.current_data = self.data_manager.get_cached_data(self.api_url)
        # No need to call super().update()

    async def draw(self):
        # Draw uses data fetched by update()
        self.screen_manager.clear()
        self.screen_manager.draw_header("Moscow Time")

        if self.current_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            # No footer if no data
            return

        # Draw timestamp from local RTC (NTP-synced)
        try:
            timestamp = int(time.time())
        except Exception as e:
            timestamp = None
            print(f"[moscow_time_applet] Failed to get local time: {e}")
        self.screen_manager.draw_footer(timestamp)

        # Access the nested 'data' dictionary which holds the actual API response
        bitcoin_data = self.current_data.get('data', {})
        if not isinstance(bitcoin_data, dict):
            print(f"[moscow_time_applet] Unexpected data format: {bitcoin_data}")
            self.screen_manager.draw_centered_text("Data Error")
            return

        price = bitcoin_data.get('lastPrice')

        if price is not None:
            try:
                btc_price = float(price)
                if btc_price > 0:  # Check price is positive
                    # Calculate Moscow Time (sats per dollar)
                    moscow_time = int(100_000_000 / btc_price)

                    # Format as clock display (e.g., 15:32)
                    # Ensure it handles cases like 100 sats -> 01:00
                    display_time = f"{moscow_time//100:02d}:{moscow_time%100:02d}"

                    self.screen_manager.draw_centered_text(display_time, scale=12)
                else:
                    print("[moscow_time_applet] BTC price is zero or negative, cannot calculate Moscow Time.")
                    self.screen_manager.draw_centered_text("N/A")
            except (ValueError, TypeError) as e:
                print(f"[moscow_time_applet] Error converting values: {e}")
                self.screen_manager.draw_centered_text("Data Error")
        else:
            # Handle missing price data
            self.screen_manager.draw_centered_text("N/A")

        # screen_manager.update() is called by AppletManager or transition
        # self.drawn flag removed
