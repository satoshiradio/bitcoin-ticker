from screen_manager import ScreenManager
from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import ujson as json
import os
import uerrno

class bitcoin_gold_ratio_applet(BaseApplet):
    """
    Displays Bitcoin to Gold price ratio:
    - Current BTC price in USD
    - Current Gold price per oz in USD
    - The ratio between them (BTC/Gold)
    """
    TTL = const(300)  # 5 minutes, gold price updates less frequently

    def __init__(self, screen_manager: ScreenManager, data_manager: DataManager, config_manager=None):
        super().__init__('bitcoin_gold_ratio_applet', screen_manager, config_manager)
        self.data_manager = data_manager
        self.btc_api_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        self.gold_api_url = "https://api.gold-api.com/price/XAU"
        self.current_price_data = None
        self.gold_price_data = None
        self.register()

    def start(self):
        self.current_price_data = None
        self.gold_price_data = None
        super().start()

    def stop(self):
        super().stop()

    def register(self):
        self.data_manager.register_endpoint(self.btc_api_url, self.TTL)
        self.data_manager.register_endpoint(self.gold_api_url, self.TTL)

    async def update(self):
        self.current_price_data = self.data_manager.get_cached_data(self.btc_api_url)
        new_gold_data = self.data_manager.get_cached_data(self.gold_api_url)
        if new_gold_data:
            self.gold_price_data = new_gold_data

    async def draw(self):
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin/Gold Ratio")

        if self.current_price_data is None:
            self.screen_manager.draw_centered_text("Loading BTC Price...")
            return

        if self.gold_price_data is None:
            self.screen_manager.draw_centered_text("Loading Gold Price...")
            return

        self.screen_manager.draw_footer(self.current_price_data.get('timestamp', None))

        bitcoin_data = self.current_price_data.get('data', {})
        if not isinstance(bitcoin_data, dict):
            # Handle cases where 'data' might not be a dict (e.g., error response)
            print(f"[bitcoin_gold_ratio_applet] Unexpected BTC data format: {bitcoin_data}")
            self.screen_manager.draw_centered_text("BTC Data Error")
            return

        # Access gold data (could be from file or API cache)
        if isinstance(self.gold_price_data, dict) and 'data' in self.gold_price_data:
            # If gold data came from API cache, it has nested structure
            gold_data = self.gold_price_data.get('data', {})
        else:
            # If gold data came from config or direct API, it's direct
            gold_data = self.gold_price_data or {}

        try:
            # Get BTC price from nested data structure
            btc_price = float(bitcoin_data.get('lastPrice', 0))

            gold_price = float(gold_data.get('price', 0))

            if btc_price > 0 and gold_price > 0:
                ounces = btc_price / gold_price
                ratio = ounces
                
                self.screen_manager.draw_centered_text("BTC/Gold (oz)", scale=3, y_offset=-60)
                self.screen_manager.draw_centered_text(f"{ratio:.2f}", scale=8, y_offset=0)
                
                prev_price = float(bitcoin_data.get('prevClosePrice', btc_price))
                prev_ratio = prev_price / gold_price
                change_percent = ((ratio - prev_ratio) / prev_ratio) * 100

                # Draw the change percentage with indicator triangle
                change_text = f"24h change: {change_percent:+.2f}%"
                text_width = self.screen_manager.display.measure_text(change_text, scale=2)
                x = (self.screen_manager.width - text_width) // 2
                y = (self.screen_manager.height - 16) // 2 + 60

                triangle_size = 10
                triangle_x = x - triangle_size - 5
                triangle_y = y + 8

                triangle_color_name = "POSITIVE_COLOR" if change_percent >= 0 else "NEGATIVE_COLOR"
                triangle_color = self.screen_manager.theme[triangle_color_name]
                self.screen_manager.display.set_pen(self.screen_manager.get_pen(triangle_color))

                if change_percent >= 0:  # Upward triangle
                    self.screen_manager.display.triangle(
                        triangle_x, triangle_y,
                        triangle_x + triangle_size, triangle_y,
                        triangle_x + (triangle_size // 2), triangle_y - triangle_size
                    )
                else:  # Downward triangle
                    self.screen_manager.display.triangle(
                        triangle_x, triangle_y - triangle_size,
                        triangle_x + triangle_size, triangle_y - triangle_size,
                        triangle_x + (triangle_size // 2), triangle_y
                    )

                self.screen_manager.draw_text(change_text, x, y, scale=2)

            else:
                self.screen_manager.draw_centered_text("Invalid Price Data")

        except (ValueError, TypeError, KeyError) as e:
            print(f"[bitcoin_gold_ratio_applet] Error: {e}")
            self.screen_manager.draw_centered_text("Data Error")
