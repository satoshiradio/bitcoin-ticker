from applets.bitcoin_applet import bitcoin_applet


class bitcoin_eur_applet(bitcoin_applet):
    API_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR"
    HEADER = "Bitcoin Euro Price"
    LABEL = "BTC/EUR"
    # "E" without a space: the bitmap font has no euro glyph.
    SYMBOL = "E"
