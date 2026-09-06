from screen_manager import ScreenManager
from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const

class bitcoin_eur_applet(BaseApplet):
    TTL = const(61)

    def __init__(self, screen_manager: ScreenManager, data_manager: DataManager):
        super().__init__('bitcoin_eur_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR"
        self.current_price_data = None # Store data fetched in update()
        self.register()

    def start(self):
        # Reset data when applet starts
        self.current_price_data = None
        super().start()

    def stop(self):
        # No need for drawn flag handling
        super().stop()

    def register(self):
        # Register with default TTL from BaseApplet if not specified otherwise
        self.data_manager.register_endpoint(self.api_url, self.TTL)

    async def update(self):
        # Fetch data in update
        self.current_price_data = self.data_manager.get_cached_data(self.api_url)
        # print(f"[bitcoin_eur_applet] Updated data: {self.current_data}") # Optional debug
        # No need to call super().update()

    async def draw(self):
        # Draw uses data fetched by update()
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Euro Price")

        if self.current_price_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            # No footer if no data
        elif isinstance(self.current_price_data, dict):
            # Draw timestamp from the outer cache dictionary
            self.screen_manager.draw_footer(self.current_price_data.get('timestamp', None))

            # Access the nested 'data' dictionary which holds the actual API response
            bitcoin_data = self.current_price_data.get('data', {})
            if not isinstance(bitcoin_data, dict):
                 print(f"[bitcoin_eur_applet] Unexpected data format: {bitcoin_data}")
                 self.screen_manager.draw_centered_text("Data Error")
                 return

            price = bitcoin_data.get('lastPrice')
            change_percent = bitcoin_data.get('priceChangePercent')

            if price is not None and change_percent is not None:
                try:
                    eur_price = float(price)
                    change = float(change_percent)

                    # Draw the label, price and change
                    self.screen_manager.draw_centered_text("BTC/EUR", scale=3, y_offset=-60)
                    # Use "E" without space for bitmap font compatibility
                    self.screen_manager.draw_centered_text(f"E{int(eur_price):,}")

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
                    print(f"[bitcoin_eur_applet] Error converting values: {e}")
                    self.screen_manager.draw_centered_text("Data Error")
            else:
                self.screen_manager.draw_centered_text("N/A") # Handle missing data
        else:
            self.screen_manager.draw_centered_text("Error") # Handle unexpected data type
            print(f"[bitcoin_eur_applet] Unexpected data type: {type(self.current_price_data)}")

        # screen_manager.update() is called by AppletManager or transition
