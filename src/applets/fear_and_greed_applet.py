from system_applets.base_applet import DataApplet
from micropython import const


class fear_and_greed_applet(DataApplet):
    """
    Displays the Bitcoin Fear and Greed Index.
    Shows a scale from 0 (Extreme Fear) to 100 (Extreme Greed)
    with a color gradient bar and the current index value.
    Data from: https://api.alternative.me/fng/
    """
    # API updates daily. Cache for 4 hours (4 * 60 * 60 = 14400 seconds)
    TTL = const(14400)
    API_URL = "https://api.alternative.me/fng/"
    HEADER = "Bitcoin Fear & Greed index"
    # Number of solid colour bands used to fake the gradient bar
    BANDS = const(20)
    FOOTER_ALWAYS = True
    DICT_PAYLOAD = False  # render() reports its own "API Error"

    band_pens = None

    def start(self):
        if self.band_pens is None:
            # Create the gradient pens once instead of on every frame
            self.band_pens = [
                self.screen_manager.get_pen(
                    self._calculate_color_for_index((i + 0.5) * 100.0 / self.BANDS)
                )
                for i in range(self.BANDS)
            ]
        super().start()

    def _calculate_color_for_index(self, index_value):
        """Calculates RGB color for a given index value (0-100)."""
        index_value = max(0, min(100, index_value))  # Clamp value
        if index_value <= 50:
            # Red to Yellow (Red stays 255, Green increases)
            return 255, int(255 * (index_value / 50.0)), 0
        # Yellow to Green (Green stays 255, Red decreases)
        return int(255 * (1 - (index_value - 50) / 50.0)), 255, 0

    def render(self, data):
        screen = self.screen_manager
        if not isinstance(data, dict) or data.get("metadata", {}).get("error") is not None:
            error_msg = data.get("metadata", {}).get("error", "API Error")
            print(f"[{self.applet_name}] API Error: {error_msg}")
            screen.draw_centered_text("API Error")
            return

        fng_data_list = data.get('data', [])
        if not fng_data_list or not isinstance(fng_data_list, list):
            screen.draw_centered_text("No Data")
            return

        try:
            data_point = fng_data_list[0]
            index_value = int(data_point.get("value"))
            value_classification = data_point.get("value_classification", "N/A")
        except (ValueError, TypeError, IndexError, AttributeError) as e:
            print(f"[{self.applet_name}] Error parsing FNG data: {e}")
            screen.draw_centered_text("Data Error")
            return

        # --- Drawing the F&G Index Bar and Indicator ---
        bar_margin_x = 30  # Margin from screen edges for the bar
        bar_width = screen.width - 2 * bar_margin_x
        bar_height = 25
        # Position bar slightly above true center to make space for classification text
        bar_y_start = screen.height // 2 - bar_height // 2 - 15

        # Draw the color gradient bar as a handful of solid bands
        for i in range(self.BANDS):
            band_start = (bar_width * i) // self.BANDS
            band_end = (bar_width * (i + 1)) // self.BANDS
            screen.display.set_pen(self.band_pens[i])
            screen.display.rectangle(
                bar_margin_x + band_start, bar_y_start, band_end - band_start, bar_height
            )

        # Draw the indicator triangle, pointing down onto the top edge of the bar
        tri_tip_x = bar_margin_x + int((index_value / 100.0) * bar_width)
        triangle_height = 10
        triangle_half_width = 6
        tri_base_y = bar_y_start - triangle_height

        screen.display.set_pen(screen.get_pen(screen.theme['MAIN_FONT_COLOR']))
        screen.display.triangle(
            tri_tip_x, bar_y_start,
            tri_tip_x - triangle_half_width, tri_base_y,
            tri_tip_x + triangle_half_width, tri_base_y
        )

        # Draw the index value text above the triangle
        value_text = str(index_value)
        text_scale = 2
        text_width = screen.display.measure_text(value_text, scale=text_scale)
        # 8px font height at scale 1, plus a 2px gap above the triangle's base
        text_y = tri_base_y - 8 * text_scale - 2
        screen.draw_text(value_text, tri_tip_x - text_width // 2, text_y,
                         scale=text_scale, color=screen.theme['MAIN_FONT_COLOR'])

        # Draw the classification text below the bar
        screen.draw_centered_text(value_classification, scale=3, y_offset=35)
