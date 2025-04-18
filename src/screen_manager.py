from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY_2
import jpegdec
import time
import ubinascii
import uio

class ScreenManager:
    def __init__(self, theme=None, config_manager=None):
        self.display = PicoGraphics(display=DISPLAY_PICO_DISPLAY_2)
        self.display.set_backlight(1.0)
        self.theme = theme or self.COLOR_SCHEME
        self.display.set_font("bitmap6")
        self.j = jpegdec.JPEG(self.display)
        self.pens = {}
        self.width, self.height = self.display.get_bounds()
        self.config_manager = config_manager


    COLOR_SCHEME = {
        "BACKGROUND_COLOR": (0, 0, 0),  # Black
        "ACCENT_FONT_COLOR": (252, 98, 43),  # Orange
        "MAIN_FONT_COLOR": (255, 255, 255),  # White
        "FOOTER_COLOR": (100, 100, 100),  # Gray
        "POSITIVE_COLOR": (0, 255, 0),  # Green
        "NEGATIVE_COLOR": (255, 0, 0)  # Red
    }
    def get_pen(self, color):
        if color not in self.pens:
            self.pens[color] = self.display.create_pen(*color)
        return self.pens[color]

    def get_screen(self):
        return self.display

    def update(self):
        self.display.update()

    def clear(self):
        color = self.theme["BACKGROUND_COLOR"]
        pen = self.get_pen(color)
        self.display.set_pen(pen)
        self.display.clear()  # Clear the display (which will fill it with the current pen color)

    def draw_text(self, text, x, y, scale=2, color=None):
        self.display.set_pen(self.get_pen(color or self.theme['MAIN_FONT_COLOR']))
        self.display.text(text, x, y, scale=scale)

    def draw_image(self, image_base64, x=0, y=0):
        try:
            clean_b64 = image_base64.strip().split(",")[-1]
            # Decode the base64 string into raw bytes
            image_bytes = ubinascii.a2b_base64(clean_b64)
            
            # Optional: Check the JPEG header
            if image_bytes[:2] != b'\xff\xd8':
                print("Warning: Data does not start with a valid JPEG header:", image_bytes[:4])
            
            # Convert to a mutable bytearray (which supports the buffer protocol)
            buf = bytearray(image_bytes)
            
            # Call open_RAM with the proper buffer
            self.j.open_RAM(buf)
            
            # Proceed with decoding
            self.j.decode(x, y, jpegdec.JPEG_SCALE_FULL, dither=True)
        except Exception as e:
            print(f"Error decoding base64 image: {e}")

    def draw_centered_text(self, text, color=None, scale=8, y_offset=0):
        color = color or self.theme['MAIN_FONT_COLOR']
        text_width = self.display.measure_text(text, scale=scale)
        text_height = 8 * scale  # bitmap8 font height is 8 pixels, multiplied by scale
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2 + y_offset
        self.draw_text(text, x, y, color=color, scale=scale)

    def draw_horizontal_centered_text(self, text, y, color=None, scale=2):
        color = color or self.theme['MAIN_FONT_COLOR']
        text_width = self.display.measure_text(text, scale=scale)
        x = (self.width- text_width) // 2
        self.draw_text(text, x, y, color=color, scale=scale)

    def draw_header(self, text):
        self.draw_text(text, 10, 10, scale=2, color=self.theme['ACCENT_FONT_COLOR'])
        self.display.set_pen(self.get_pen(self.theme['ACCENT_FONT_COLOR']))
        self.display.line(10, 35, self.width - 10, 35)

    def draw_footer(self, last_fetch_time=None):
        # Get timezone offset from config or default to 0 (UTC)
        timezone_offset = 0
        if self.config_manager:
            timezone_offset = self.config_manager.get_timezone_offset()
        
        # Convert hours to seconds for time calculation
        timezone_seconds = timezone_offset * 3600
        
        # Create timezone label (e.g., UTC+2, UTC-5, or just UTC for offset 0)
        if timezone_offset > 0:
            timezone_label = f"UTC+{timezone_offset}"
        elif timezone_offset < 0:
            timezone_label = f"UTC{timezone_offset}"  # Negative sign is automatically included
        else:
            timezone_label = "UTC"
        
        # Draw footer line
        self.display.set_pen(self.get_pen(self.theme['FOOTER_COLOR']))
        self.display.line(10, self.height - 35, self.width - 10, self.height - 35)

        date = None
        if last_fetch_time is not None:
            # Convert Unix timestamp to local time with configured timezone offset
            local_timestamp = last_fetch_time + timezone_seconds
            t = time.localtime(local_timestamp)
            date_str = "{:04}-{:02}-{:02} {:02}:{:02}:{:02} {}".format(
                t[0], t[1], t[2], t[3], t[4], t[5], timezone_label
            )
            date = date_str

        footer_text = "Last updated: " + (date or "N/A")
        self.draw_text(footer_text, 15, self.height - 30, scale=1, color=self.theme['FOOTER_COLOR'])

    def draw_label_and_value(self, label, value, x, y, scale=2):
        self.draw_text(f"{label}:", x, y, scale, color=self.theme['ACCENT_FONT_COLOR'])
        value_x = x + self.display.measure_text(f"{label}:", scale) + 10
        self.draw_text(str(value), value_x, y, scale)

    def format_unix_timestamp(self, timestamp):
        # Convert the Unix timestamp to a local time tuple
        tm = time.localtime(timestamp)
        
        # Format the time tuple into a readable string
        formatted_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            tm[0], tm[1], tm[2],  # Year, Month, Day
            tm[3], tm[4], tm[5]   # Hour, Minute, Second
        )
        
        return formatted_time

    def draw_traffic_light(self, level):
        """
        Draws a small circle (or square) at the top-right of the screen to indicate congestion.
        Level should be 'low', 'medium', or 'high'.
        """
        color_map = {
            "low": (0, 255, 0),      # Green
            "medium": (252, 160, 0), # Orange
            "high": (255, 0, 0),     # Red
        }
        color = color_map.get(level, (255, 255, 255))  # fallback: white

        pen = self.get_pen(color)
        self.display.set_pen(pen)

        radius = 8
        x = self.width - radius - 10
        y = 20

        # No circle draw in PicoGraphics yet, so draw a small square
        self.display.rectangle(x - radius, y - radius, radius * 2, radius * 2)
