from screen_manager import ScreenManager
from system_applets.base_applet import BaseApplet
import ujson as json
import os
from data_manager import DataManager
from micropython import const
import gc
import uerrno
import time

class ath_eur_applet(BaseApplet):
    """
    Displays Bitcoin All-Time High (ATH) information in EUR:
    - ATH Price (EUR) from ath.json
    - ATH Date from ath.json
    - Current Price (EUR) from Binance
    - Percentage difference from current price to ATH
    """
    TTL = const(120) # For current price from Binance

    def __init__(self, screen_manager: ScreenManager, data_manager: DataManager):
        super().__init__('ath_eur_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR" # For current price
        self.current_price_data = None # Store current price data fetched in update()
        self.ath_data = None # Store ATH data loaded in start() from ath.json
        self.register()

    def _load_ath_data(self):
        """Load ATH data from the common ath.json file."""
        try:
            with open("ath.json", "r") as f:
                self.ath_data = json.load(f)
                print(f"[ath_eur_applet] Loaded ATH data from ath.json: {self.ath_data}")
        except OSError as e:
            if e.args[0] == uerrno.ENOENT:
                print("[ath_eur_applet] ath.json not found.")
            else:
                print(f"[ath_eur_applet] Error loading ath.json: {e}")
            self.ath_data = None
        except ValueError:
            print("[ath_eur_applet] Error parsing ath.json.")
            self.ath_data = None
        except Exception as e:
            print(f"[ath_eur_applet] Unexpected error loading ATH data: {e}")
            self.ath_data = None

    def start(self):
        self.current_price_data = None
        self._load_ath_data() # Load ATH data from file
        super().start()

    def stop(self):
        super().stop()

    def register(self):
        # Register endpoint for current price data from Binance
        self.data_manager.register_endpoint(self.api_url, self.TTL)

    async def update(self):
        # Fetch current price data from Binance
        self.current_price_data = self.data_manager.get_cached_data(self.api_url)
        gc.collect()

    async def draw(self):
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin EUR ATH")

        timestamp = None
        if isinstance(self.current_price_data, dict): # Timestamp from current price fetch
            timestamp = self.current_price_data.get('timestamp', None)
        self.screen_manager.draw_footer(timestamp)

        # Check if ATH data is loaded from ath.json
        if not self.ath_data or self.ath_data.get("ath_eur") is None:
            self.screen_manager.draw_centered_text("ATH EUR Data N/A", scale=3, y_offset=0)
            gc.collect()
            return

        ath_price_eur = self.ath_data["ath_eur"]
        ath_date_str_eur = self.ath_data.get("ath_date_eur", "Unknown date")
        ath_date_formatted = ath_date_str_eur.split("T")[0] if isinstance(ath_date_str_eur, str) else "Unknown date"

        # Title "BTC EUR ATH"
        self.screen_manager.draw_centered_text("BTC EUR ATH", scale=3, y_offset=-60)
        
        # ATH Price - large and prominent
        self.screen_manager.draw_centered_text(f"E{int(ath_price_eur):,}", y_offset=-10) # Euro symbol replaced with E, space removed
        
        # ATH Date (scale 2, below ATH price)
        self.screen_manager.draw_centered_text(f"{ath_date_formatted}", scale=2, y_offset=25)
        
        # Check if current price data is available (from Binance)
        current_price_eur = None
        if isinstance(self.current_price_data, dict):
            price_data = self.current_price_data.get('data', {}) # Binance data structure
            if isinstance(price_data, dict):
                price_str = price_data.get('lastPrice')
                if price_str is not None:
                    try:
                        current_price_eur = float(price_str)
                    except (ValueError, TypeError):
                        print(f"[ath_eur_applet] Error converting current EUR price: {price_str}")
        
        # Display Combined Current Price and Percentage Difference (scale 2)
        if current_price_eur is not None:
            # Check for new ATH before calculating percentage
            if self.ath_data and current_price_eur > self.ath_data.get("ath_eur", 0):
                fetch_timestamp = self.current_price_data.get('timestamp')
                if fetch_timestamp:
                    t = time.gmtime(fetch_timestamp) # Use gmtime for UTC
                    new_ath_date_str = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(t[0], t[1], t[2], t[3], t[4], t[5])
                else: # Fallback
                    t = time.gmtime(time.time())
                    new_ath_date_str = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(t[0], t[1], t[2], t[3], t[4], t[5])

                print(f"[ath_eur_applet] New ATH EUR detected: {current_price_eur} (was {self.ath_data.get('ath_eur')}) on {new_ath_date_str}")
                self.ath_data["ath_eur"] = current_price_eur
                self.ath_data["ath_date_eur"] = new_ath_date_str

                # Update local variables for the current draw cycle
                ath_price_eur = current_price_eur # This was the variable name used below
                ath_date_formatted = new_ath_date_str.split("T")[0]

                try:
                    with open("ath.json", "w") as f:
                        json.dump(self.ath_data, f)
                    print("[ath_eur_applet] Updated ath.json with new EUR ATH.")
                except Exception as e:
                    print(f"[ath_eur_applet] Error writing updated ath.json: {e}")

            try:
                percentage_diff = ((current_price_eur - ath_price_eur) / ath_price_eur) * 100
                combined_text = f"Now: E{int(current_price_eur):,} ({percentage_diff:+.2f}% vs ATH)" # Euro symbol replaced with E, space removed
                text_color = self.screen_manager.theme['NEGATIVE_COLOR'] if percentage_diff < 0 else self.screen_manager.theme['MAIN_FONT_COLOR']
                self.screen_manager.draw_centered_text(combined_text, scale=2, y_offset=60, color=text_color)
            except ZeroDivisionError:
                self.screen_manager.draw_centered_text(f"Now: E{int(current_price_eur):,} (ATH Zero)", scale=2, y_offset=60, # Euro symbol replaced with E, space removed
                                                      color=self.screen_manager.theme['NEGATIVE_COLOR'])
            except Exception as e:
                print(f"[ath_eur_applet] Error calculating/displaying combined price/percentage: {e}")
                self.screen_manager.draw_centered_text(f"Now: E{int(current_price_eur):,} (Error %)", scale=2, y_offset=60, # Euro symbol replaced with E, space removed
                                                     color=self.screen_manager.theme['NEGATIVE_COLOR'])
        else:
            self.screen_manager.draw_centered_text("Current Price: Loading...", scale=2, y_offset=60)

        gc.collect()
