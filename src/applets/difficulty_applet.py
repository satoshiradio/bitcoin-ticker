from system_applets.base_applet import DataApplet
from micropython import const
import time


class difficulty_applet(DataApplet):
    TTL = const(300)
    API_URL = "https://mempool.space/api/v1/difficulty-adjustment"
    BLOCKCHAIN_API = "https://blockchain.info/q/getdifficulty"
    HEADER = "Bitcoin Difficulty Stats"
    # The mempool payload is a dict, but a bad one must not short-circuit the
    # rows below - each of them reports its own "N/A"/"Error".
    DICT_PAYLOAD = False
    MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

    difficulty_data = None

    def register(self):
        super().register()
        self.data_manager.register_endpoint(self.BLOCKCHAIN_API, self.TTL)

    def start(self):
        self.difficulty_data = None
        super().start()

    async def update(self):
        await super().update()
        self.difficulty_data = self.data_manager.get_cached_data(self.BLOCKCHAIN_API)

    def has_data(self):
        return self.current_data is not None and self.difficulty_data is not None

    def _format_difficulty(self, value):
        # Format as Trillions once large enough
        return f"{value / 1e12:.1f}T" if value >= 1e12 else f"{value:.0f}"

    def render(self, mempool_raw):
        screen = self.screen_manager
        # blockchain.info just returns the number
        difficulty_raw_str = self.difficulty_data.get("data", "0")
        y = 40  # Starting Y position for drawing key-value pairs

        # 1. Current difficulty from blockchain.info
        try:
            difficulty_str = self._format_difficulty(float(difficulty_raw_str))
        except Exception:
            difficulty_str = "N/A"
        screen.draw_row("Current diff:", difficulty_str, y)
        y += 26

        # 2. Progress % (from mempool data)
        try:
            progress = mempool_raw.get("progressPercent")
            progress_str = f"{progress:.1f}%" if progress is not None else "N/A"
        except (ValueError, TypeError):
            progress_str = "Error"
        screen.draw_row("Progress:", progress_str, y)
        y += 26

        # 3. Estimated Retarget Date (from mempool data)
        try:
            ms_ts = mempool_raw.get("estimatedRetargetDate")
            if ms_ts is not None:
                # Convert ms timestamp to seconds, using device local time
                t = time.localtime(int(ms_ts) // 1000)
                formatted_date = f"{t[2]:02d} {self.MONTHS[t[1] - 1]} {t[3]:02d}:{t[4]:02d}"
            else:
                formatted_date = "N/A"
        except (ValueError, TypeError, AttributeError):
            formatted_date = "Error"
        screen.draw_row("Retarget:", formatted_date, y)
        y += 26

        # 4. Blocks remaining (from mempool data)
        try:
            blocks_remaining = mempool_raw.get("remainingBlocks")
            blocks_str = f"{blocks_remaining:,}" if blocks_remaining is not None else "N/A"
        except (ValueError, TypeError):
            blocks_str = "Error"
        screen.draw_row("Blocks left:", blocks_str, y)
        y += 26

        # 5. Expected new difficulty (calculated using both data sources)
        try:
            diff_change = mempool_raw.get("difficultyChange")
            if diff_change is not None and difficulty_str not in ("N/A", "Error"):
                new_diff = float(difficulty_raw_str) * (1 + (float(diff_change) / 100.0))
                new_diff_str = self._format_difficulty(new_diff)
            else:
                new_diff_str = "N/A"
        except (ValueError, TypeError):
            new_diff_str = "Error"
        screen.draw_row("Expected diff:", new_diff_str, y)
