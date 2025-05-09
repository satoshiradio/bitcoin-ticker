from screen_manager import ScreenManager
from system_applets.base_applet import BaseApplet
from data_manager import DataManager
from micropython import const
import gc
import ujson

class fear_and_greed_applet(BaseApplet):
    """
    Displays the Bitcoin Fear and Greed Index.
    Shows a scale from 0 (Extreme Fear) to 100 (Extreme Greed)
    with a color gradient bar and the current index value.
    Data from: https://api.alternative.me/fng/
    """
    # API updates daily. Cache for 4 hours (4 * 60 * 60 = 14400 seconds)
    TTL = const(14400)
    API_URL = "https://api.alternative.me/fng/"

    def __init__(self, screen_manager: ScreenManager, data_manager: DataManager):
        super().__init__('fear_and_greed_applet', screen_manager)
        self.data_manager = data_manager
        self.current_data = None
        self.register()

    def register(self):
        self.data_manager.register_endpoint(self.API_URL, self.TTL)

    def start(self):
        self.current_data = None
        super().start()

    def stop(self):
        super().stop()

    async def update(self):
        self.current_data = self.data_manager.get_cached_data(self.API_URL)
        gc.collect()

    def _calculate_color_for_index(self, index_value):
        """Calculates RGB color for a given index value (0-100)."""
        index_value = max(0, min(100, index_value)) # Clamp value
        if index_value <= 50:
            # Red to Yellow (Red stays 255, Green increases)
            p = index_value / 50.0
            r = 255
            g = int(255 * p)
            b = 0
        else:
            # Yellow to Green (Green stays 255, Red decreases)
            p = (index_value - 50) / 50.0
            r = int(255 * (1 - p))
            g = 255
            b = 0
        return r, g, b

    async def draw(self):
        self.screen_manager.clear()
        self.screen_manager.draw_header("Bitcoin Fear & Greed index")

        timestamp = None
        if isinstance(self.current_data, dict):
            # Use the timestamp from the DataManager's cache entry,
            # which reflects when our system last fetched the data.
            timestamp = self.current_data.get('timestamp', None)
        self.screen_manager.draw_footer(timestamp)

        if self.current_data is None:
            self.screen_manager.draw_centered_text("Loading...")
            gc.collect()
            return

        api_response_data = self.current_data.get('data', {})
        if not isinstance(api_response_data, dict) or api_response_data.get("metadata", {}).get("error") is not None:
            error_msg = api_response_data.get("metadata", {}).get("error", "API Error")
            print(f"[fng_applet] API Error: {error_msg}")
            self.screen_manager.draw_centered_text("API Error")
            gc.collect()
            return

        fng_data_list = api_response_data.get('data', [])
        if not fng_data_list or not isinstance(fng_data_list, list):
            self.screen_manager.draw_centered_text("No Data")
            gc.collect()
            return

        try:
            data_point = fng_data_list[0]
            index_value = int(data_point.get("value"))
            value_classification = data_point.get("value_classification", "N/A")
        except (ValueError, TypeError, IndexError, AttributeError) as e:
            print(f"[fng_applet] Error parsing FNG data: {e}")
            self.screen_manager.draw_centered_text("Data Error")
            gc.collect()
            return

        # --- Drawing the F&G Index Bar and Indicator ---
        bar_margin_x = 30  # Margin from screen edges for the bar
        bar_width = self.screen_manager.width - 2 * bar_margin_x
        bar_height = 25
        # Position bar slightly above true center to make space for classification text
        bar_y_start = self.screen_manager.height // 2 - bar_height // 2 - 15

        # Draw the color gradient bar
        for i in range(bar_width):
            # Calculate the index (0-100) corresponding to this segment of the bar
            segment_index = (i / bar_width) * 100
            r, g, b = self._calculate_color_for_index(segment_index)
            pen = self.screen_manager.get_pen((r, g, b)) # Pass RGB as a tuple
            self.screen_manager.display.set_pen(pen)
            self.screen_manager.display.rectangle(bar_margin_x + i, bar_y_start, 1, bar_height)

        # Draw the indicator triangle and value text
        indicator_x_on_bar = bar_margin_x + int((index_value / 100.0) * bar_width)
        
        triangle_height = 10
        triangle_half_width = 6
        
        # Triangle points downwards, sits on top of the bar
        tri_tip_x = indicator_x_on_bar
        tri_tip_y = bar_y_start # Tip touches the top edge of the bar
        tri_base_y = bar_y_start - triangle_height
        
        tri_pen = self.screen_manager.get_pen(self.screen_manager.theme['MAIN_FONT_COLOR'])
        self.screen_manager.display.set_pen(tri_pen)
        self.screen_manager.display.triangle(
            tri_tip_x, tri_tip_y,
            tri_tip_x - triangle_half_width, tri_base_y,
            tri_tip_x + triangle_half_width, tri_base_y
        )

        # Draw the index value text above the triangle
        value_text = str(index_value)
        text_scale = 2
        # Approximate text height for bitmap6 font (8px at scale 1)
        text_height_approx = 8 * text_scale 
        text_width = self.screen_manager.display.measure_text(value_text, scale=text_scale)
        text_x = tri_tip_x - text_width // 2
        text_y = tri_base_y - text_height_approx - 2 # 2px gap above triangle's base

        self.screen_manager.draw_text(value_text, text_x, text_y, scale=text_scale, color=self.screen_manager.theme['MAIN_FONT_COLOR'])

        # Draw the classification text below the bar
        self.screen_manager.draw_centered_text(value_classification, scale=3, y_offset=35) # y_offset relative to screen center

        gc.collect()
