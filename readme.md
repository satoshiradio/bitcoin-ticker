![Satoshi Radio Ticker](https://i.postimg.cc/DzDmwdKK/ticker-landscape.webp "Satoshi Radio Ticker")
# 📻 Satoshi Radio Bitcoin Ticker

Welcome to the Satoshi Radio Ticker project! This compact, desk-friendly device keeps you updated on Bitcoin's price and blockchain status at a glance. Built with affordable, accessible components, it's perfect for crypto enthusiasts who want real-time information without constantly checking their phones.

This is a fully open source project that you can build yourself! We've designed it to be accessible for makers of all skill levels using readily available components. Follow our guide and you'll have your own Bitcoin ticker up and running in no time - customize it, modify it, and make it your own!

A Bitcoin price and blockchain information display built with Raspberry Pi Pico W and Pimoroni Display Pack 2.8.

**Watch the tutorial on Youtube (click on the image below):**

<a href="https://www.youtube.com/watch?v=SD7deq_Zz4w" target="_blank" rel="noopener noreferrer">
  <img src="https://img.youtube.com/vi/SD7deq_Zz4w/hqdefault.jpg" alt="Watch on YouTube" />
</a>

## ✨ Features
 
- 💰 Real-time Bitcoin price display (BTC/USD)
- 💰 Real-time Bitcoin price display (BTC/EUR)
- 💰 Real-time Bitcoin price display (BTC/Gold ounces)
- 💵 Bitcoin vs Dollar ATH display
- 💶 Bitcoin vs Euro ATH display
- ⛓️ Current Bitcoin blockchain height display
- 🏦 Bitcoin transaction fee display
- 📊 Bitcoin Mempool status display
- 🕰️ Moscow Time display
- ⛏️ Bitcoin difficulty stats
- 🔥 Bitcoin Fear & Greed index display
- 🏆 Bitcoin Dominance display
- 📶 WiFi connectivity for live data updates
- 🔄 Automatic screen cycling
- 🚦 RGB LED status indicator
- ⚡ Low power consumption

## 🔧 Hardware Requirements

To build your own Satoshi Radio Ticker, you'll need:

- [Raspberry Pi Pico 2 WH](https://shop.pimoroni.com/products/raspberry-pi-pico-2-w?variant=54852253024635)
- [Pimoroni Display Pack 2.8](https://shop.pimoroni.com/products/pico-display-pack-2-8?variant=42047194005587) (or 2.0)
- 3D printed case (files provided in this repo under "assets")
- 4x M2 x 5mm bolts
- Laser cut acrylic (files provided in this repo under "assets")
- [Angled Micro USB cable](https://www.amazon.nl/PremiumCord-USB-verbindingskabel-datakabel-ku2m1f-90/dp/B07NSQ5859)

## 🔥 Quickstart
<img src="https://i.postimg.cc/SKg2qwmT/001-EXPLODED-VIEW-TICKER-2-8-22.webp" alt="Exploded View Ticker" title="Exploded View Ticker" width="500" />

### Hardeware setup
1. Download the latest `bitcoin-ticker.uf2` file from the releases section.
2. Connect your Raspberry Pi Pico 2 W to your computer while holding the BOOTSEL button.
3. When the Pico appears as a USB drive on your computer, release the button.
4. Drag and drop the `bitcoin-ticker.uf2` file onto the Pico drive.
5. The Pico will automatically disconnect, reboot, and start running the ticker software.
6. Print the 3D enclosure files from the "assets" folder.
7. Carefully place the Pico in the enclosure and secure it with the four M2 x 5mm screws.
8. Connect the Pimoroni Display Pack to the Pico, ensuring correct alignment of pins (don't press too hard).
9. Power the Pico with a Micro USB cable to test if the display and data fetching work correctly.
10. Once everything is working, add the laser-cut acrylic top screen to complete the build.

### Network Setup
1. Power on the ticker.
2. When the setup screen appears, connect to the ticker's WiFi network. Use the SSID (SR_Ticker) and password displayed on the screen to connect from your phone or laptop.
3. After connecting, either scan the QR code or enter the IP address shown on the screen into your web browser.
4. Enter your local network credentials (SSID and password) and click "Add Network."
5. Optional: Select which applets (screens) you want to display. If you make any changes to the applets, be sure to click "Save Applets."
6. When you've finished configuration, click "Reboot Device."
7. If the ticker becomes unresponsive during reboot, perform a hard reboot by disconnecting and reconnecting the USB cable.

### Pro-tips
- To access the Settings page after initial setup, simply browse to the ticker's IP address on your local network. There's no need to connect directly to the ticker.
- You can add multiple WiFi networks! This makes it convenient to connect the ticker to both your home network and your phone's hotspot.
- You can change settings on the Settings page related to your timezone, duration of applets on screen and some cool applet transition effects. 
- You can fork the code and add your own customizations! After you're done, just use the makefile to upload your modified code to the Pi. See the development section below for details.
- Need to reset the Raspberry Pi? There is a whole in the enclosure. Just use a paperclip, you can easily reach the BOOTSEL button.

## 🖨️ 3D Print Instructions
You can print the enclosure yourself! It's straightforward. Choose between the 2.0" or 2.8" version, using the STL files provided in the assets folder. For the 2.8" version, we've also included a 3MF file that you can import into your preferred 3D printing software. This file features our Satoshi Radio Logo. The print settings I used are listed below, but feel free to experiment with your own settings.

### Print Settings
- Layer Height: 0.20mm (standard)
- Outer Wall Speed: 100mm/s
- Supports: Enabled
- Cooling: Disabled for first 3 layers
- Material: ESUN E-PLA+ Matte

### Laser Cutting Instructions
The most difficult part to complete at home. All necessary files and measurements are available in the assets folder. My recommendation is to locate a laser cutting service in your area or place an order online. You'll need translucent black acrylic with 3mm thickness. While the sticker adds a nice finishing touch, it's optional rather than required.

## 🩺 Health Check API

The ticker exposes a `GET /health` endpoint that returns real-time device status as JSON. This is useful for monitoring, home automation integrations, or debugging.

### Request
```bash
curl http://<ticker-ip>/health
```

### Response
```json
{
  "status": "ok",
  "wifi": {
    "connected": true,
    "ip": "192.168.1.23",
    "rssi": -56
  },
  "uptime_seconds": 265,
  "reset_reason": "pwron_reset",
  "current_applet": "dominance_applet",
  "active_applets": 6,
  "free_memory": 93936
}
```

### Fields
- **status:** `"ok"` if WiFi is connected, `"degraded"` otherwise
- **wifi:** connection state, IP address, and signal strength (RSSI in dBm)
- **uptime_seconds:** time since last boot
- **reset_reason:** why the device last restarted (e.g. `pwron_reset`, `soft_reset`, `wdt_reset`)
- **current_applet:** the applet currently displayed
- **active_applets:** number of enabled applets
- **free_memory:** available RAM in bytes

## 🔐 API Key Authentication (Optional)

You can protect all API endpoints with an API key. When configured, every request (except public routes) must include a valid `Authorization: Bearer <key>` header.

### Setup
1. Open the ticker's settings page in your browser
2. Enter an API key in the **API Key** field (leave empty for open access)
3. Click **Save Configuration**

### Usage
```bash
curl -H "Authorization: Bearer my-secret-key" http://<ticker-ip>/health
curl -H "Authorization: Bearer my-secret-key" http://<ticker-ip>/config
```

### Public Routes (always accessible without auth)
- `GET /` — settings page
- `POST /submit` — WiFi network setup (access point mode)
- `GET /config` — read configuration
- `POST /update_config` — save configuration (including API key changes)

Without an API key set, all endpoints are open. This makes it easy to get started — add authentication only when you need it.

## 📶 WiFi Monitor

The ticker includes an automatic WiFi monitor that detects disconnections and reconnects without a reboot. It uses exponential backoff to avoid hammering the network.

### How It Works
- Monitors WiFi connection state continuously
- On disconnect: attempts reconnect with increasing intervals (30s, 60s, 120s…)
- Resyncs NTP time after reconnect
- Restores applet cycling automatically

### Test It
```bash
curl -X POST http://<ticker-ip>/test_disconnect
```
The WiFi will disconnect and the monitor should reconnect within ~30 seconds. Check the serial output for `[WiFiMonitor]` log messages.

## 🔨 Development
### Project Structure
```
src/
├── applets/                            # Bitcoin information displays
│   ├── bitcoin_applet.py               # BTC / Dollar price display
│   ├── bitcoin_eur_applet.py           # BTC / Euro price display
│   ├── bitcoin_gold_ratio_applet.py    # BTC / Gold Ounced (oz) price display
│   ├── ath_applet.py
│   ├── ath_eur_applet.py
│   ├── block_height_applet.py
│   ├── fee_applet.py
│   ├── halving_countdown_applet.py
│   ├── moscow_time_applet.py
│   ├── fear_and_greed_applet.py
│   ├── difficulty_applet.py
│   ├── dominance_applet.py
│   └── mempool_status_applet.py
├── system_applets/                     # Core system applets
│   ├── ap_applet.py                    # Access point configuration screen
│   ├── base_applet.py                  # Base class for all applets
│   ├── error_applet.py                 # Error display screen
│   └── splash_applet.py                # Boot splash screen
├── applet_manager.py                   # Manages applet lifecycle
├── data_manager.py                     # Handles API requests and caching
├── main.py                             # Application entry point
├── screen_manager.py                   # Display abstraction
├── urllib_urequest.py                  # HTTP client
├── web_server.py                       # Configuration web interface
├── index.html                          # The settings page served by web_server.py
├── splash_image.py                     # Boot splash JPEG as raw bytes
├── ap_qr_image.py                      # Setup QR code JPEG as raw bytes
├── utils.py                            # Small shared helpers (atomic JSON writes)
├── wifi_manager.py                     # Network connection manager
├── wifi_monitor.py                     # Automatic Network WiFi monitor and fix / notify tool 
├── transitions.py                      # Utility to help manage applet transition effects
├── initialization.py                   # Utility to help manage initial ticker setup and loading of big datasets
└── config.py                           # Utility to help manage configurations
```

### Assets in the firmware

MicroPython's freezer only picks up `.py` files, so anything else under `src/`
would be missing from a device flashed with the release `.uf2`. The two JPEGs
therefore live in `splash_image.py` / `ap_qr_image.py` as a single `DATA =
b'...'` literal — frozen, that literal stays in flash and costs no RAM.
`index.html` stays a normal file (it is edited by hand); the release workflow
converts it to `index_html.py` with `tools/freeze_file.py` just before the
build, and `web_server.py` serves that module when it exists and falls back to
the file on the filesystem otherwise. So `make upload` keeps working as
before: it puts `index.html` on the device and edits show up on the next
request.

To regenerate an image module after replacing a JPEG:

```bash
python3 tools/freeze_file.py path/to/new_splash.jpg src/splash_image.py
```

### Dependencies
- MicroPython (tested with Pimoroni MicroPython distribution)

Libraries:
- picographics - Graphics library for the display
- network - Wi-Fi functionality
- uasyncio - Asynchronous I/O
- jpegdec - JPEG image support
- json - JSON parsing

APIs Used:
- Binance API: For Bitcoin price data
- Mempool.space API: For blockchain statistics (block height, fees)

### Creating Custom Applets
You can create your own custom applets by subclassing DataApplet. It registers the endpoint,
keeps the cached data fresh and draws the screen, header, footer and "Loading..." placeholder;
your applet only fills in the middle. Add your new applet to applet_manager.py and the SRC list
in the makefile.
```
from system_applets.base_applet import DataApplet

class CustomApplet(DataApplet):
    TTL = 120  # Cache time in seconds
    API_URL = "https://your-api-endpoint.com/data"
    HEADER = "Custom Data"

    def render(self, data):
        # `data` is the endpoint's own JSON, straight from the cache
        self.screen_manager.draw_centered_text("Your Data Here")
```
Applets that need something else can override `has_data()` (when one endpoint is not enough),
`timestamp()` (what the footer shows) or `draw_loading()` (the placeholder), and set
`FOOTER_ALWAYS` / `DICT_PAYLOAD`. See `system_applets/base_applet.py`.
### Basic Commands
### Check Device ID
```bash
make devices
```
This command will show the USB device ID of your connected Pico.

### Check Available Devices
```bash
make devices
```
This will list available USB devices. Look for something like `/dev/tty.usbmodem101`

### Upload Folders
```bash
make create_folders
```
This command uploads the folder structure.

### Upload Code
```bash
make upload
```
This command uploads all source files to the Pico. Watch the terminal for progress.

### Run the Code
```bash
make run
```
This executes the main program on the Pico.

### Upload and Run
```bash
make all
```
This combines both upload and run commands.

### Monitor Serial Output
```bash
make serial
```
Opens a serial monitor to view device output. Use `Ctrl-A Ctrl-\` to exit.

### Adding New Files

When adding new Python files to the project:

1. Create your new file in the appropriate directory under `/src/`
2. Add the file path to the `SRC` list in the makefile:
   ```makefile
   SRC = src/main.py \
         src/your_new_file.py \
         ...
   ```
3. Run `make upload` to include the new file in the next upload

Note: The file path in `SRC` should be relative to the project root and use forward slashes.

### Single File Upload

To upload a single file instead of the entire project, you can use the `ampy` tool directly:

```bash
ampy put src/path/to/file.py destination/path/file.py
```

Example:
```bash
ampy put src/applets/bitcoin_applet.py applets/bitcoin_applet.py
```

This is useful when making small changes and wanting to test quickly without uploading the entire project.

### Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (git checkout -b feature/amazing-feature)
3. Add your changes (git add {file})
4. Commit your changes (git commit -m 'Add some amazing feature')
5. Push to the branch (git push origin feature/amazing-feature)
6. Open a Pull Request

### Resetting the Pico

If you need to reset your Pico W:
1. Disconnect power from the device
2. Connect the ticker to your computer while holding the BOOTSEL button
3. Release the button after 2 seconds
4. Upload firmware again (see quickstart section)



## 🆘 Support

If you have questions or need help, please open an issue on the GitHub repository.

## 📜 License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/). Please refer to the LICENSE file for further details.
