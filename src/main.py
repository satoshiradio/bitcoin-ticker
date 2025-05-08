import applet_manager
import uasyncio as asyncio
from pimoroni import RGBLED

from screen_manager import ScreenManager
from data_manager import DataManager
from wifi_manager import WiFiManager
from web_server import AsyncWebServer
from applet_manager import AppletManager
from system_applets import ap_applet
from config import ConfigManager
from initialization import Initializer # Import the new Initializer

RGBLED(6, 7, 8).set_rgb(0, 0, 0)

async def main() -> None:
    """
    Main entry point for the application.
    Initializes managers (screen, data, Wi-Fi), launches the appropriate applets,
    and starts the web server. It keeps an asynchronous loop alive to service
    other tasks such as applets and data retrieval.
    """
    config_manager = ConfigManager()
    screen_manager = ScreenManager(config_manager=config_manager)
    data_manager = DataManager()
    wifi_manager = WiFiManager()

    # Pass the single config_manager instance
    applet_manager_instance = AppletManager(screen_manager, data_manager, wifi_manager, config_manager)
    # Create Initializer instance
    initializer = Initializer(screen_manager, config_manager)

    splash_applet = applet_manager.SplashApplet(screen_manager)
    print("[Main] Starting splash applet.")
    await applet_manager_instance.run_applet_once(splash_applet)

    # Attempt to connect to known Wi-Fi networks
    if wifi_manager.connect_to_saved_networks():
        print("[Main] Connected to a known Wi-Fi network.")

        # --- Run Initializer ---
        await initializer.run_initialization()
        # ---------------------

        # Store the IP address after successful connection
        ip_address = "N/A"
        if wifi_manager.wlan.isconnected():
            ip_config = wifi_manager.wlan.ifconfig()
            ip_address = ip_config[0] if ip_config and len(ip_config) > 0 else "N/A"
            print(f"[Main] Device IP Address: {ip_address}")
        else:
             print("[Main] WLAN disconnected unexpectedly after connect attempt.")
        config_manager.set_ip_address(ip_address)

        # Start the main applet loop *after* initialization
        asyncio.create_task(applet_manager_instance.start_applets())
    else:
        print("[Main] No saved networks found or unable to connect. Setting up AP mode.")
        # Optionally run parts of initializer even in AP mode? For now, only run in STA mode.
        # Optionally clear or set a specific IP when in AP mode
        config_manager.set_ip_address("AP Mode") # Or keep the last known IP / "N/A"
        wifi_manager.setup_ap()
        ap_mode_applet = ap_applet.ApApplet(screen_manager, wifi_manager)
        asyncio.create_task(applet_manager_instance._run_applet(ap_mode_applet, is_system_applet=True))

    # Pass the single config_manager instance to the web server
    web_server = AsyncWebServer(wifi_manager, applet_manager_instance, config_manager)
    asyncio.create_task(web_server.start_web_server())

    # Keep the main event loop alive
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
