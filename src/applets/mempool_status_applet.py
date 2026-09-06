from system_applets.base_applet import DataApplet
from micropython import const


class mempool_status_applet(DataApplet):
    TTL = const(60)
    API_URL = "https://mempool.space/api/mempool"
    HEADER = "Bitcoin Mempool Size"

    def render(self, data):
        screen = self.screen_manager
        try:
            count = int(data.get("count", 0))
            vsize = int(data.get("vsize", 0))  # in vbytes

            size_mb = vsize / 1_000_000.0

            if size_mb < 2.0:
                congestion_level = "low"
            elif size_mb < 10.0:
                congestion_level = "medium"
            else:
                congestion_level = "high"
            screen.draw_traffic_light(congestion_level)

            screen.draw_horizontal_centered_text("Mempool Size (MB)", y=60, scale=2)
            screen.draw_centered_text(f"{size_mb:.2f} MB", scale=6, y_offset=0)
            screen.draw_horizontal_centered_text(
                f"{count:,} TXs", y=screen.height - 60, scale=2
            )
        except (ValueError, TypeError, KeyError) as e:
            print(f"[{self.applet_name}] Error parsing data: {e}")
            screen.draw_centered_text("Data Error")
