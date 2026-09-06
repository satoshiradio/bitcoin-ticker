from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import time

class difficulty_applet(BaseApplet):
    TTL = const(300)

    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('difficulty_applet', screen_manager)
        self.screen_manager = screen_manager
        self.data_manager = data_manager
        self.mempool_api = "https://mempool.space/api/v1/difficulty-adjustment"
        self.blockchain_api = "https://blockchain.info/q/getdifficulty"
        self.mempool_data = None # Store data for mempool API
        self.difficulty_data = None # Store data for blockchain API
        self.register()

    def start(self):
        # Reset data when applet starts
        self.mempool_data = None
        self.difficulty_data = None
        super().start()

    def stop(self):
        # No need for drawn flag handling
        super().stop()

    def register(self):
        self.data_manager.register_endpoint(self.mempool_api, self.TTL)
        self.data_manager.register_endpoint(self.blockchain_api, self.TTL)

    async def update(self):
        # Fetch data for both endpoints
        self.mempool_data = self.data_manager.get_cached_data(self.mempool_api)
        self.difficulty_data = self.data_manager.get_cached_data(self.blockchain_api)
        # No need to call super().update()

    def draw_kv(self, label: str, value: str, y: int):
        """Draw a label left-aligned and a value right-aligned."""
        self.screen_manager.draw_text(label, 10, y, scale=2)
        text_width = self.screen_manager.display.measure_text(value, 2)
        self.screen_manager.draw_text(value,
            self.screen_manager.width - 10 - text_width, y, scale=2)

    async def draw(self):
        # Draw uses data fetched by update()
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Difficulty Stats")

        # Use the data fetched in update()
        if self.mempool_data is None or self.difficulty_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            # No footer if no data
            return

        # Use mempool data timestamp for footer as it's more detailed
        self.screen_manager.draw_footer(self.mempool_data.get('timestamp', None))

        # Extract nested data dictionaries
        mempool_raw = self.mempool_data.get("data", {})
        difficulty_raw_str = self.difficulty_data.get("data", "0") # blockchain.info just returns the number

        y = 40  # Starting Y position for drawing key-value pairs

        # 1. Current difficulty from blockchain.info
        try:
            difficulty = float(difficulty_raw_str)
            if difficulty >= 1e12: # Format as Trillions if large enough
                difficulty_str = f"{difficulty / 1e12:.1f}T"
            else:
                difficulty_str = f"{difficulty:.0f}"
        except Exception:
            difficulty_str = "N/A"
        self.draw_kv("Current diff:", difficulty_str, y)
        y += 26

        # 2. Progress % (from mempool data)
        try:
            progress = mempool_raw.get("progressPercent")
            progress_str = f"{progress:.1f}%" if progress is not None else "N/A"
        except (ValueError, TypeError):
            progress_str = "Error"
        self.draw_kv("Progress:", progress_str, y)
        y += 26

        # 3. Estimated Retarget Date (from mempool data)
        try:
            ms_ts = mempool_raw.get("estimatedRetargetDate")
            if ms_ts is not None:
                # Convert ms timestamp to seconds for time.localtime
                ts = int(ms_ts) // 1000
                # Apply timezone offset from config manager if needed (assuming localtime uses system time)
                # Note: Pico might not have full timezone support in time module.
                # offset_seconds = self.screen_manager.config_manager.get_timezone_offset() * 3600
                # t = time.localtime(ts + offset_seconds)
                t = time.localtime(ts) # Using device local time for now
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                formatted_date = f"{t[2]:02d} {months[t[1] - 1]} {t[3]:02d}:{t[4]:02d}"
            else:
                formatted_date = "N/A"
        except (ValueError, TypeError, AttributeError):
            formatted_date = "Error"
        self.draw_kv("Retarget:", formatted_date, y)
        y += 26

        # 4. Blocks remaining (from mempool data)
        try:
            blocks_remaining = mempool_raw.get("remainingBlocks")
            blocks_str = f"{blocks_remaining:,}" if blocks_remaining is not None else "N/A"
        except (ValueError, TypeError):
            blocks_str = "Error"
        self.draw_kv("Blocks left:", blocks_str, y)
        y += 26

        # 5. Expected new difficulty (calculated using both data sources)
        try:
            diff_change = mempool_raw.get("difficultyChange")
            if diff_change is not None and difficulty_str not in ["N/A", "Error"]:
                current_diff = float(difficulty_raw_str) # Use the raw string from blockchain.info
                new_diff = current_diff * (1 + (float(diff_change) / 100.0))

                # Format similarly to current difficulty
                if new_diff >= 1e12:
                    new_diff_str = f"{new_diff / 1e12:.1f}T"
                else:
                    new_diff_str = f"{new_diff:.0f}"
            else:
                new_diff_str = "N/A"
        except (ValueError, TypeError):
             new_diff_str = "Error" # Handle potential float conversion errors
        self.draw_kv("Expected diff:", new_diff_str, y)
        y += 26

        # screen_manager.update() is called by AppletManager or transition
