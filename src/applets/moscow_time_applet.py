from system_applets.base_applet import DataApplet
from micropython import const
import time


class moscow_time_applet(DataApplet):
    TTL = const(120)
    API_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    HEADER = "Moscow Time"

    def timestamp(self):
        # Footer shows the local RTC (NTP-synced), not the fetch time.
        try:
            return int(time.time())
        except Exception as e:
            print(f"[{self.applet_name}] Failed to get local time: {e}")
            return None

    def render(self, data):
        screen = self.screen_manager
        price = data.get('lastPrice')
        if price is None:
            screen.draw_centered_text("N/A")
            return

        try:
            btc_price = float(price)
        except (ValueError, TypeError) as e:
            print(f"[{self.applet_name}] Error converting values: {e}")
            screen.draw_centered_text("Data Error")
            return

        if btc_price <= 0:
            print(f"[{self.applet_name}] BTC price is zero or negative, cannot calculate Moscow Time.")
            screen.draw_centered_text("N/A")
            return

        # Moscow Time = sats per dollar, shown as a clock (e.g. 15:32)
        moscow_time = int(100_000_000 / btc_price)
        screen.draw_centered_text(f"{moscow_time//100:02d}:{moscow_time%100:02d}", scale=12)
