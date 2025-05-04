from screen_manager import ScreenManager
from system_applets.base_applet import BaseApplet
import ujson as json
import os
from data_manager import DataManager
from micropython import const
import gc
import uerrno

class ath_applet(BaseApplet):
    """
    Displays Bitcoin All-Time High (ATH) information:
    - ATH Price (USD)
    - ATH Date
    - Percentage difference from current price to ATH
    """
    TTL = const(120) # Same TTL as bitcoin_applet for current price

    def __init__(self, screen_manager: ScreenManager, data_manager: DataManager):
        super().__init__('ath_applet', screen_manager)
        self.data_manager = data_manager
        # Need current price data, use the same endpoint as bitcoin_applet
        self.api_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        self.current_price_data = None # Store current price data fetched in update()
        self.ath_data = None # Store ATH data loaded in start()
        self.register()

    def _load_ath_data(self):
        """Load ATH data from the JSON file created by the initializer."""
        try:
            with open("bitcoin_ath.json", "r") as f:
                self.ath_data = json.load(f)
                print(f"[ath_applet] Loaded ATH data: {self.ath_data}")
        except OSError as e:
            if e.args[0] == uerrno.ENOENT:
                print("[ath_applet] bitcoin_ath.json not found.")
            else:
                print(f"[ath_applet] Error loading bitcoin_ath.json: {e}")
            self.ath_data = None # Ensure it's None on error
        except ValueError:
            print("[ath_applet] Error parsing bitcoin_ath.json.")
            self.ath_data = None
        except Exception as e:
            print(f"[ath_applet] Unexpected error loading ATH data: {e}")
            self.ath_data = None

    def start(self):
        # Reset data when applet starts
        self.current_price_data = None
        self._load_ath_data() # Load ATH data when applet starts
        super().start()

    def stop(self):
        super().stop()

    def register(self):
        # Register endpoint for current price data
        self.data_manager.register_endpoint(self.api_url, self.TTL)

    async def update(self):
        # Fetch current price data
        self.current_price_data = self.data_manager.get_cached_data(self.api_url)
        gc.collect()

    async def draw(self):
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin ATH Info")

        # Draw footer with timestamp from current price data cache
        timestamp = None
        if isinstance(self.current_price_data, dict):
            timestamp = self.current_price_data.get('timestamp', None)
        self.screen_manager.draw_footer(timestamp)

        # Check if ATH data is loaded
        if not self.ath_data or self.ath_data.get("ath_usd") is None:
            self.screen_manager.draw_centered_text("ATH Data N/A", y_offset=90)
            gc.collect()
            return

        ath_price = self.ath_data["ath_usd"]
        ath_date_str = self.ath_data.get("ath_date_usd", "Unknown date")
        ath_date_formatted = ath_date_str.split("T")[0] if isinstance(ath_date_str, str) else "Unknown date"

        # Draw ATH Price and Date - centered on screen
        # Looking at bitcoin_applet.py, we see they're using absolute positions
        # and the draw_centered_text has a different parameter style
        
        # Title centered at the top portion
        self.screen_manager.draw_centered_text("BTC ATH", scale=3, y_offset=-60)
        
        # ATH Price - large and prominent in the center, matching bitcoin_applet's size
        # In the bitcoin example, they don't specify scale for the price, meaning it uses default (likely 4)
        self.screen_manager.draw_centered_text(f"${int(ath_price):,}")
        
        # Date below the price - moved down more to avoid overlap
        self.screen_manager.draw_centered_text(f"Date: {ath_date_formatted}", scale=2, y_offset=40)
        
        # Check if current price data is available
        current_price = None
        if isinstance(self.current_price_data, dict):
            price_data = self.current_price_data.get('data', {})
            if isinstance(price_data, dict):
                price_str = price_data.get('lastPrice')
                if price_str is not None:
                    try:
                        current_price = float(price_str)
                    except (ValueError, TypeError):
                        print(f"[ath_applet] Error converting current price: {price_str}")

        # Calculate and draw percentage difference if current price is available
        # Position this at the bottom portion but above the footer - moved down more
        if current_price is not None:
            try:
                percentage_diff = ((current_price - ath_price) / ath_price) * 100
                diff_text = f"Current: {percentage_diff:.2f}% vs ATH"
                text_color = self.screen_manager.theme['NEGATIVE_COLOR'] if percentage_diff < 0 else self.screen_manager.theme['MAIN_FONT_COLOR']
                
                # Drawing at y_offset=70 (70 pixels below center) - adjusted from 80 to avoid footer
                self.screen_manager.draw_centered_text(diff_text, scale=2, y_offset=70, color=text_color)
            except ZeroDivisionError:
                self.screen_manager.draw_centered_text("Cannot calc % diff (ATH=0?)", scale=2, y_offset=70, 
                                                      color=self.screen_manager.theme['NEGATIVE_COLOR'])
            except Exception as e:
                print(f"[ath_applet] Error calculating percentage diff: {e}")
                self.screen_manager.draw_centered_text("% Diff Error", scale=2, y_offset=70,
                                                     color=self.screen_manager.theme['NEGATIVE_COLOR'])
        else:
            # Current price not available
            self.screen_manager.draw_centered_text("Current Price: Loading...", scale=2, y_offset=70)

        gc.collect()
