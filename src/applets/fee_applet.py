from system_applets.base_applet import DataApplet
from micropython import const


class fee_applet(DataApplet):
    TTL = const(120)
    API_URL = "https://mempool.space/api/v1/fees/recommended"
    HEADER = "Bitcoin Mempool Fees"
    FEES = (
        ("Fast:", 'fastestFee'),
        ("Medium:", 'halfHourFee'),
        ("Slow:", 'hourFee'),
    )

    def render(self, data):
        y = 60  # Starting Y position for fee lines
        for label, key in self.FEES:
            fee = data.get(key)
            fee_text = f"{fee} sat/vB" if isinstance(fee, (int, float)) else "N/A"
            self.screen_manager.draw_row(label, fee_text, y)
            y += 40  # Move to next line
