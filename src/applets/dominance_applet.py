from system_applets.base_applet import DataApplet
from micropython import const


class dominance_applet(DataApplet):
    """
    Displays the Bitcoin Dominance percentage (BTC.D).
    Data from: https://api.coingecko.com/api/v3/global
    """
    TTL = const(600)  # 10 minutes
    API_URL = "https://api.coingecko.com/api/v3/global"
    HEADER = "Bitcoin Dominance"
    FOOTER_ALWAYS = True
    DICT_PAYLOAD = False  # render() reports its own "API Error"

    def _coingecko_data(self):
        """CoinGecko nests the real payload under another 'data' key."""
        response = self.payload()
        inner = response.get('data', {}) if isinstance(response, dict) else None
        return inner if isinstance(inner, dict) else None

    def timestamp(self):
        inner = self._coingecko_data()
        return inner.get("updated_at") if inner else None

    def render(self, data):
        screen = self.screen_manager
        if not isinstance(data, dict):
            print(f"[{self.applet_name}] API Error or unexpected data format: {data}")
            screen.draw_centered_text("API Error")
            return

        coingecko_data = self._coingecko_data()
        if coingecko_data is None:
            screen.draw_centered_text("Data Error")
            print(f"[{self.applet_name}] CoinGecko internal 'data' object not found or not a dict.")
            return

        market_cap_percentage = coingecko_data.get('market_cap_percentage', {})
        if not isinstance(market_cap_percentage, dict):
            screen.draw_centered_text("Data Error")
            print(f"[{self.applet_name}] market_cap_percentage not found or not a dict in CoinGecko data.")
            return

        btc_dominance = market_cap_percentage.get('btc')
        if btc_dominance is None:
            screen.draw_centered_text("No Data")
            print(f"[{self.applet_name}] btc_dominance value not found.")
            return

        try:
            dominance_value = float(btc_dominance)

            screen.draw_centered_text("BTC DOMINANCE", scale=3, y_offset=-60)
            # y_offset=-10 matches the ATH applet's main value position
            screen.draw_centered_text(f"{dominance_value:.2f}%", y_offset=-10)

            # --- Draw Dominance Bar ---
            bar_x = 30
            bar_width = screen.width - 2 * bar_x
            bar_height = 20
            # Position the bar below the dominance percentage text
            bar_y = screen.height // 2 + 35

            screen.display.set_pen(screen.get_pen(screen.theme['ACCENT_COLOR']))

            # Outline (4 lines)
            screen.display.line(bar_x, bar_y, bar_x + bar_width - 1, bar_y)
            screen.display.line(bar_x, bar_y + bar_height - 1, bar_x + bar_width - 1, bar_y + bar_height - 1)
            screen.display.line(bar_x, bar_y, bar_x, bar_y + bar_height - 1)
            screen.display.line(bar_x + bar_width - 1, bar_y, bar_x + bar_width - 1, bar_y + bar_height - 1)

            # Fill (inside the outline), clamped to 0-100%
            clamped_dominance = max(0.0, min(100.0, dominance_value))
            fill_width = int((clamped_dominance / 100.0) * (bar_width - 2))
            if fill_width > 0:
                screen.display.rectangle(bar_x + 1, bar_y + 1, fill_width, bar_height - 2)

        except (ValueError, TypeError) as e:
            print(f"[{self.applet_name}] Error converting dominance value or drawing bar: {e}")
            screen.draw_centered_text("Data Error")
