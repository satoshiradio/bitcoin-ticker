from system_applets.base_applet import DataApplet
from micropython import const


class bitcoin_applet(DataApplet):
    TTL = const(61)
    API_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    HEADER = "Bitcoin US Dollar Price"
    LABEL = "BTC/USD"
    SYMBOL = "$"

    def render(self, data):
        screen = self.screen_manager
        price = data.get('lastPrice')
        change_percent = data.get('priceChangePercent')

        if price is None or change_percent is None:
            screen.draw_centered_text("N/A")
            return

        try:
            value = float(price)
            change = float(change_percent)

            screen.draw_centered_text(self.LABEL, scale=3, y_offset=-60)
            screen.draw_centered_text(f"{self.SYMBOL}{int(value):,}")
            screen.draw_change(f"24h change: {change:+.2f}%", change)
        except (ValueError, TypeError) as e:
            print(f"[{self.applet_name}] Error converting values: {e}")
            screen.draw_centered_text("Data Error")
