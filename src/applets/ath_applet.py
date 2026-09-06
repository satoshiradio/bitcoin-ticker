from system_applets.base_applet import DataApplet
from micropython import const
from utils import atomic_write
import ujson as json
import time


class ath_applet(DataApplet):
    """
    Displays Bitcoin All-Time High (ATH) information:
    - ATH Price
    - ATH Date
    - Percentage difference from the current price to the ATH
    """
    TTL = const(120)  # Same TTL as bitcoin_applet for current price
    # Needs the current price, so it uses the same endpoint as bitcoin_applet
    API_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    HEADER = "BITCOIN vs US DOLLAR ATH"
    LABEL = "BTC/USD ATH"
    SYMBOL = "$"
    ATH_KEY = "ath_usd"
    ATH_DATE_KEY = "ath_date_usd"
    NO_DATA_TEXT = "ATH Data N/A"
    ATH_FILE = "ath.json"
    FOOTER_ALWAYS = True
    DICT_PAYLOAD = False  # A missing price only degrades part of the screen

    ath_data = None

    def start(self):
        self._load_ath_data()  # Load ATH data when the applet starts
        super().start()

    def _load_ath_data(self):
        """Load ATH data from the JSON file created by the initializer."""
        try:
            with open(self.ATH_FILE, "r") as f:
                self.ath_data = json.load(f)
            print(f"[{self.applet_name}] Loaded ATH data: {self.ath_data}")
        except Exception as e:
            print(f"[{self.applet_name}] Could not load {self.ATH_FILE}: {e}")
            self.ath_data = None

    def has_data(self):
        return bool(self.ath_data) and self.ath_data.get(self.ATH_KEY) is not None

    def draw_loading(self):
        self.screen_manager.draw_centered_text(self.NO_DATA_TEXT, scale=3, y_offset=0)

    def _record_new_ath(self, price):
        """Store a new ATH in ath.json. Only touches flash when it changed."""
        t = time.gmtime(self.timestamp() or time.time())  # gmtime for UTC
        date_str = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )
        print(f"[{self.applet_name}] New ATH detected: {price} "
              f"(was {self.ath_data.get(self.ATH_KEY)}) on {date_str}")
        self.ath_data[self.ATH_KEY] = price
        self.ath_data[self.ATH_DATE_KEY] = date_str
        try:
            atomic_write(self.ATH_FILE, self.ath_data)
            print(f"[{self.applet_name}] Updated {self.ATH_FILE} with new ATH.")
        except Exception as e:
            print(f"[{self.applet_name}] Error writing updated {self.ATH_FILE}: {e}")

    def render(self, data):
        screen = self.screen_manager
        ath_price = self.ath_data[self.ATH_KEY]
        ath_date = self.ath_data.get(self.ATH_DATE_KEY, "Unknown date")
        ath_date = ath_date.split("T")[0] if isinstance(ath_date, str) else "Unknown date"

        screen.draw_centered_text(self.LABEL, scale=3, y_offset=-60)
        screen.draw_centered_text(f"{self.SYMBOL}{int(ath_price):,}", y_offset=-10)
        screen.draw_centered_text(ath_date, scale=2, y_offset=25)

        current_price = None
        price_str = data.get('lastPrice') if isinstance(data, dict) else None
        if price_str is not None:
            try:
                current_price = float(price_str)
            except (ValueError, TypeError):
                print(f"[{self.applet_name}] Error converting current price: {price_str}")

        if current_price is None:
            screen.draw_centered_text("Current Price: Loading...", scale=2, y_offset=60)
            return

        if current_price > ath_price:
            self._record_new_ath(current_price)
            ath_price = current_price

        now_text = f"Now: {self.SYMBOL}{int(current_price):,}"
        try:
            percentage_diff = ((current_price - ath_price) / ath_price) * 100
            text = f"{now_text} ({percentage_diff:+.2f}% vs ATH)"
            color = (screen.theme['NEGATIVE_COLOR'] if percentage_diff < 0
                     else screen.theme['MAIN_FONT_COLOR'])
            screen.draw_centered_text(text, scale=2, y_offset=60, color=color)
        except ZeroDivisionError:
            screen.draw_centered_text(f"{now_text} (ATH Zero)", scale=2, y_offset=60,
                                      color=screen.theme['NEGATIVE_COLOR'])
        except Exception as e:
            print(f"[{self.applet_name}] Error calculating/displaying combined price/percentage: {e}")
            screen.draw_centered_text(f"{now_text} (Error %)", scale=2, y_offset=60,
                                      color=screen.theme['NEGATIVE_COLOR'])
