from screen_manager import ScreenManager
from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc

class dominance_applet(BaseApplet):
    """
    Displays the Bitcoin Dominance percentage (BTC.D).
    Data from: https://api.coingecko.com/api/v3/global
    """
    TTL = const(600)  # 10 minutes
    API_URL = "https://api.coingecko.com/api/v3/global"

    def __init__(self, screen_manager: ScreenManager, data_manager: DataManager):
        super().__init__('dominance_applet', screen_manager)
        self.data_manager = data_manager
        self.current_data = None
        self.register()

    def register(self):
        self.data_manager.register_endpoint(self.API_URL, self.TTL)

    def start(self):
        self.current_data = None
        super().start()

    def stop(self):
        super().stop()

    async def update(self):
        self.current_data = self.data_manager.get_cached_data(self.API_URL)
        gc.collect()

    async def draw(self):
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Dominance")

        timestamp = None
        if isinstance(self.current_data, dict):
            # api_response_data is the actual content from CoinGecko
            api_response_data = self.current_data.get('data', {}) 
            if isinstance(api_response_data, dict):
                # The actual data from CoinGecko is nested under another 'data' key
                coingecko_internal_data = api_response_data.get('data', {})
                if isinstance(coingecko_internal_data, dict):
                    timestamp = coingecko_internal_data.get("updated_at")
        self.screen_manager.draw_footer(timestamp)

        if self.current_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            gc.collect()
            return

        api_response_data = self.current_data.get('data', {})
        if not isinstance(api_response_data, dict):
            print(f"[dominance_applet] API Error or unexpected data format: {api_response_data}")
            self.screen_manager.draw_centered_text("API Error")
            gc.collect()
            return

        # Extract dominance data
        # api_response_data is the direct JSON response from CoinGecko.
        # The actual values are nested under a 'data' key within this response.
        coingecko_internal_data = api_response_data.get('data', {})
        if not isinstance(coingecko_internal_data, dict):
            self.screen_manager.draw_centered_text("Data Error")
            print(f"[dominance_applet] CoinGecko internal 'data' object not found or not a dict.")
            gc.collect()
            return

        market_cap_percentage_data = coingecko_internal_data.get('market_cap_percentage', {})
        if not isinstance(market_cap_percentage_data, dict):
            self.screen_manager.draw_centered_text("Data Error")
            print(f"[dominance_applet] market_cap_percentage not found or not a dict in CoinGecko data.")
            gc.collect()
            return
            
        btc_dominance = market_cap_percentage_data.get('btc')

        if btc_dominance is None:
            self.screen_manager.draw_centered_text("No Data")
            print(f"[dominance_applet] btc_dominance value not found.")
            gc.collect()
            return

        try:
            dominance_value = float(btc_dominance)
            
            # Display Title "BTC.D"
            self.screen_manager.draw_centered_text("BTC.D", scale=3, y_offset=-60)
            
            # Display Dominance Percentage
            # Using y_offset=-10 to match ATH applet's main value position
            self.screen_manager.draw_centered_text(f"{dominance_value:.2f}%", y_offset=-10)

            # --- Draw Dominance Bar ---
            bar_margin_x = 30
            bar_height = 20
            # Position bar below the dominance percentage text
            # Dominance text (scale 8) is y_offset=-10. Approx bottom: screen_height/2 - 10 + (8*8/2) = screen_height/2 + 22
            bar_top_abs_y = self.screen_manager.height // 2 + 35 
            
            bar_outline_color_rgb = self.screen_manager.theme['ACCENT_COLOR'] # Use ACCENT_COLOR for header/orange
            bar_pen = self.screen_manager.get_pen(bar_outline_color_rgb)
            self.screen_manager.display.set_pen(bar_pen)

            bar_x = bar_margin_x
            bar_width = self.screen_manager.width - 2 * bar_margin_x

            # Draw outline (4 lines)
            # Top line
            self.screen_manager.display.line(bar_x, bar_top_abs_y, bar_x + bar_width - 1, bar_top_abs_y)
            # Bottom line
            self.screen_manager.display.line(bar_x, bar_top_abs_y + bar_height - 1, bar_x + bar_width - 1, bar_top_abs_y + bar_height - 1)
            # Left line
            self.screen_manager.display.line(bar_x, bar_top_abs_y, bar_x, bar_top_abs_y + bar_height - 1)
            # Right line
            self.screen_manager.display.line(bar_x + bar_width - 1, bar_top_abs_y, bar_x + bar_width - 1, bar_top_abs_y + bar_height - 1)

            # Draw fill (inside the outline)
            fill_x = bar_x + 1
            fill_y = bar_top_abs_y + 1
            fill_max_width = bar_width - 2
            fill_height = bar_height - 2

            # Clamp dominance_value between 0 and 100 for fill calculation
            clamped_dominance = max(0.0, min(100.0, dominance_value))
            actual_fill_width = int((clamped_dominance / 100.0) * fill_max_width)

            if actual_fill_width > 0: # Only draw fill if it has width
                self.screen_manager.display.rectangle(fill_x, fill_y, actual_fill_width, fill_height)

        except (ValueError, TypeError) as e:
            print(f"[dominance_applet] Error converting dominance value or drawing bar: {e}")
            self.screen_manager.draw_centered_text("Data Error")

        gc.collect()
