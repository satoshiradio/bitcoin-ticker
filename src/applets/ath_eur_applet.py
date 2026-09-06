from applets.ath_applet import ath_applet


class ath_eur_applet(ath_applet):
    """Same as ath_applet, but against the euro price from Binance."""
    API_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR"
    HEADER = "BITCOIN vs EURO ATH"
    LABEL = "BTC/EUR ATH"
    # "E" without a space: the bitmap font has no euro glyph.
    SYMBOL = "E"
    ATH_KEY = "ath_eur"
    ATH_DATE_KEY = "ath_date_eur"
    NO_DATA_TEXT = "ATH EUR Data N/A"
