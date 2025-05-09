from screen_manager import ScreenManager
from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc

class bitcoin_applet(BaseApplet):
    TTL = const(120)

    def __init__(self, screen_manager: ScreenManager, data_manager: DataManager):
        super().__init__('bitcoin_applet', screen_manager)
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
        # print(f"[bitcoin_applet] Updated data: {self.current_data}") # Optional debug
        gc.collect()
        # No need to call super().update()

    async def draw(self):
        # Draw uses data fetched by update()
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin US Dollar Price")

        if self.current_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            # No footer if no data
        elif isinstance(self.current_data, dict):
            # Draw timestamp from the outer cache dictionary
            self.screen_manager.draw_footer(self.current_data.get('timestamp', None))

            # Access the nested 'data' dictionary which holds the actual API response
            bitcoin_data = self.current_data.get('data', {})
            if not isinstance(bitcoin_data, dict):
                 # Handle cases where 'data' might not be a dict (e.g., error response)
                 print(f"[bitcoin_applet] Unexpected data format: {bitcoin_data}")
                 self.screen_manager.draw_centered_text("Data Error")
                 gc.collect()
                 return # Stop drawing if data format is wrong

            price = bitcoin_data.get('lastPrice')
            change_percent = bitcoin_data.get('priceChangePercent')

            if price is not None and change_percent is not None:
                try:
                    usd_price = float(price)
                    change = float(change_percent)

                    # Draw the label, price and change
                    self.screen_manager.draw_centered_text("BTC/USD", scale=3, y_offset=-60)
                    self.screen_manager.draw_centered_text(f"${int(usd_price):,}")

                    # Draw the change percentage with indicator triangle
                    change_text = f"24h change: {change:+.2f}%"
                    text_width = self.screen_manager.display.measure_text(change_text, scale=2)
                    x = (self.screen_manager.width - text_width) // 2
                    y = (self.screen_manager.height - 16) // 2 + 60 # 16 = text height scale 2

                    triangle_size = 10
                    triangle_x = x - triangle_size - 5
                    triangle_y = y + 8 # Approx vertical center

                    triangle_color_name = "POSITIVE_COLOR" if change >= 0 else "NEGATIVE_COLOR"
                    triangle_color = self.screen_manager.theme[triangle_color_name]
                    self.screen_manager.display.set_pen(self.screen_manager.get_pen(triangle_color))

                    if change >= 0: # Upward triangle
                        self.screen_manager.display.triangle(
                            triangle_x, triangle_y,
                            triangle_x + triangle_size, triangle_y,
                            triangle_x + (triangle_size // 2), triangle_y - triangle_size
                        )
                    else: # Downward triangle
                        self.screen_manager.display.triangle(
                            triangle_x, triangle_y - triangle_size,
                            triangle_x + triangle_size, triangle_y - triangle_size,
                            triangle_x + (triangle_size // 2), triangle_y
                        )

                    # Draw the text (use default color)
                    self.screen_manager.draw_text(change_text, x, y, scale=2)

                except (ValueError, TypeError) as e:
                    print(f"[bitcoin_applet] Error converting values: {e}")
                    self.screen_manager.draw_centered_text("Data Error")
            else:
                # Handle missing price or change data
                self.screen_manager.draw_centered_text("N/A")
        else:
            # Handle case where self.current_data is not a dict (unexpected)
            self.screen_manager.draw_centered_text("Error")
            print(f"[bitcoin_applet] Unexpected data type: {type(self.current_data)}")

        # screen_manager.update() is called by AppletManager or transition
        # self.drawn flag removed
        gc.collect()
