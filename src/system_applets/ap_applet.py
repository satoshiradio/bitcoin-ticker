import ap_qr_image
import screen_manager
from system_applets.base_applet import BaseApplet
from wifi_manager import WiFiManager
import wifi_manager

class ApApplet(BaseApplet):
    def __init__(self, screen_manager: screen_manager.ScreenManager,wifi_manager: WiFiManager):
        super().__init__("ApApplet", screen_manager)
        self.screen_manager = screen_manager
        self.wifi_manager = wifi_manager


    def start(self):
        print("AP Applet: Starting")

    def stop(self):
        print("AP Applet: Stopping")

    async def update(self):
        print("AP Applet: Updating")
        if self.wifi_manager and self.wifi_manager.is_connected():
            return True
        return False

    async def draw(self):
        print("AP Applet: drawing")
        self.screen_manager.clear()
        self.screen_manager.draw_header('SETUP')
        self.screen_manager.draw_text(f"SSID: {self.wifi_manager.get_ap_ssid()}\nPassword: havefunstayingpoor\n\nAfter connecting to the AP,\nscan the QR code to access \nthe web interface.\n192.168.4.1", 10, 40, scale=2)

        # self.screen_manager.draw_text("After connecting to the AP,\nscan the QR code to access \nthe web interface\n 192.168.4.1", 10, 80, scale=2)
        self.screen_manager.draw_image(ap_qr_image.DATA, 10, self.screen_manager.height-84-10 )
