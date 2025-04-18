from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc
import time

class difficulty_applet(BaseApplet):
    TTL = const(300)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('difficulty_applet', screen_manager)
        self.screen_manager = screen_manager
        self.data_manager = data_manager
        self.mempool_api = "https://mempool.space/api/v1/difficulty-adjustment"
        self.blockchain_api = "https://blockchain.info/q/getdifficulty"
        self.drawn = False
        self.register()

    def start(self):
        super().start()

    def stop(self):
        super().stop()
        self.drawn = False

    def register(self):
        self.data_manager.register_endpoint(self.mempool_api, self.TTL)
        self.data_manager.register_endpoint(self.blockchain_api, self.TTL)

    async def update(self):
        return await super().update()

    def draw_kv(self, label: str, value: str, y: int):
        """Draw a label left-aligned and a value right-aligned."""
        self.screen_manager.draw_text(label, 10, y, scale=2)
        text_width = self.screen_manager.display.measure_text(value, 2)
        self.screen_manager.draw_text(value,
            self.screen_manager.width - 10 - text_width, y, scale=2)

    async def draw(self):
        if self.drawn:
            return

        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Difficulty Stats")

        mempool_data = self.data_manager.get_cached_data(self.mempool_api)
        difficulty_data = self.data_manager.get_cached_data(self.blockchain_api)

        if mempool_data is None or difficulty_data is None:
            gc.collect()
            await self.data_manager._update_cache(self.mempool_api)
            await self.data_manager._update_cache(self.blockchain_api)
            mempool_data = self.data_manager.get_cached_data(self.mempool_api)
            difficulty_data = self.data_manager.get_cached_data(self.blockchain_api)
            if mempool_data is None or difficulty_data is None:
                return

        self.screen_manager.draw_footer(mempool_data.get('timestamp', None))
        raw = mempool_data.get("data", {})
        y = 40  # Room for 5 rows

        # 1. Current difficulty from blockchain.info
        try:
            raw_diff_str = difficulty_data.get("data", "0")
            difficulty = float(raw_diff_str)
            if difficulty >= 1e12:
                difficulty_str = f"{difficulty / 1e12:.1f}T"
            else:
                difficulty_str = f"{difficulty:.0f}"
        except Exception:
            difficulty_str = "N/A"
        self.draw_kv("Current diff:", difficulty_str, y)
        y += 26

        # 2. Progress %
        try:
            progress = raw.get("progressPercent")
            progress_str = f"{progress:.1f}%" if progress is not None else "N/A"
        except Exception:
            progress_str = "N/A"
        self.draw_kv("Progress:", progress_str, y)
        y += 26

        # 3. Estimated Retarget Date
        try:
            ms_ts = int(raw.get("estimatedRetargetDate", 0))
            if ms_ts > 0:
                ts = ms_ts // 1000
                t = time.localtime(ts)
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                formatted_date = f"{t[2]:02d} {months[t[1] - 1]} {t[3]:02d}:{t[4]:02d}"
            else:
                formatted_date = "N/A"
        except Exception:
            formatted_date = "N/A"
        self.draw_kv("Retarget:", formatted_date, y)
        y += 26

        # 4. Blocks remaining
        try:
            blocks_remaining = raw.get("remainingBlocks")
            blocks_str = str(blocks_remaining) if blocks_remaining is not None else "N/A"
        except Exception:
            blocks_str = "N/A"
        self.draw_kv("Blocks left:", blocks_str, y)
        y += 26

        # 5. Expected new difficulty
        try:
            diff_change = raw.get("difficultyChange")
            if diff_change is not None and difficulty_str != "N/A":
                # Calculate expected new difficulty
                current_diff = float(raw_diff_str)
                new_diff = current_diff * (1 + diff_change / 100)
        
                # Format similarly to current difficulty
                if new_diff >= 1e12:
                    new_diff_str = f"{new_diff / 1e12:.1f}T"
                else:
                    new_diff_str = f"{new_diff:.0f}"
            else:
                new_diff_str = "N/A"
        except Exception:
            new_diff_str = "N/A"
        self.draw_kv("Expected diff:", new_diff_str, y)
        y += 26

        self.screen_manager.update()
        self.drawn = True
        gc.collect()
