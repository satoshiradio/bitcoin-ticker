import screen_manager
from system_applets.base_applet import BaseApplet


class SplashApplet(BaseApplet):
    def __init__(self, screen_manager: screen_manager.ScreenManager):
        super().__init__("splash_applet", screen_manager)
        self.screen_manager = screen_manager

    def start(self):
        print("Splash Applet: Starting")


    def stop(self):
        print("Splash Applet: Stopping")

    async def update(self):
        print("Splash Applet: Updating")
        return False

    async def draw(self):
        print("Splash Applet: drawing")
        self.screen_manager.draw_image("splash.jpg")
        self.screen_manager.draw_centered_text("Welcome",scale=4, y_offset=75)
        self.screen_manager.draw_centered_text("Trying to connect...", scale=2, y_offset=100)
        # if self.wifi_manager:
        #     print(f"Connected to: {self.wifi_manager.get_ssid()}")
        #     self.screen_manager.draw_text(f"Connected to: \n{self.wifi_manager.get_ssid()}", 0, 0)
