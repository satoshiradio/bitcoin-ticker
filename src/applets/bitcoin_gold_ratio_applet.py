from system_applets.base_applet import DataApplet
from micropython import const


class bitcoin_gold_ratio_applet(DataApplet):
    """
    Displays the Bitcoin to Gold price ratio:
    - Current BTC price in USD
    - Current Gold price per oz in USD
    - The ratio between them (BTC/Gold)
    """
    TTL = const(300)  # 5 minutes, gold price updates less frequently
    API_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    GOLD_API_URL = "https://api.gold-api.com/price/XAU"
    HEADER = "Bitcoin/Gold Ratio"
    DICT_PAYLOAD = False  # render() reports its own "BTC Data Error"

    gold_price_data = None

    def register(self):
        super().register()
        self.data_manager.register_endpoint(self.GOLD_API_URL, self.TTL)

    def start(self):
        self.gold_price_data = None
        super().start()

    async def update(self):
        await super().update()
        new_gold_data = self.data_manager.get_cached_data(self.GOLD_API_URL)
        if new_gold_data:
            self.gold_price_data = new_gold_data

    def has_data(self):
        return self.current_data is not None and self.gold_price_data is not None

    def draw_loading(self):
        text = "Loading BTC Price..." if self.current_data is None else "Loading Gold Price..."
        self.screen_manager.draw_centered_text(text)

    def render(self, bitcoin_data):
        screen = self.screen_manager
        if not isinstance(bitcoin_data, dict):
            print(f"[{self.applet_name}] Unexpected BTC data format: {bitcoin_data}")
            screen.draw_centered_text("BTC Data Error")
            return

        # Gold data from the API cache is wrapped in an envelope; a direct
        # reading is used as-is.
        if isinstance(self.gold_price_data, dict) and 'data' in self.gold_price_data:
            gold_data = self.gold_price_data.get('data', {})
        else:
            gold_data = self.gold_price_data or {}

        try:
            btc_price = float(bitcoin_data.get('lastPrice', 0))
            gold_price = float(gold_data.get('price', 0))

            if btc_price <= 0 or gold_price <= 0:
                screen.draw_centered_text("Invalid Price Data")
                return

            ratio = btc_price / gold_price
            screen.draw_centered_text("BTC/Gold (oz)", scale=3, y_offset=-60)
            screen.draw_centered_text(f"{ratio:.2f}", scale=8, y_offset=0)

            prev_ratio = float(bitcoin_data.get('prevClosePrice', btc_price)) / gold_price
            change_percent = ((ratio - prev_ratio) / prev_ratio) * 100
            screen.draw_change(f"24h change: {change_percent:+.2f}%", change_percent)

        except (ValueError, TypeError, KeyError) as e:
            print(f"[{self.applet_name}] Error: {e}")
            screen.draw_centered_text("Data Error")
