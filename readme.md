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

## 🔨 Development
### Project Structure
```
src/
├── applets/                    # Bitcoin information displays
│   ├── bitcoin_applet.py       # BTC / Dollar price display
│   ├── bitcoin_eur_applet.py   # BTC / Euro price display
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
├── system_applets/             # Core system applets
│   ├── ap_applet.py            # Access point configuration screen
│   ├── base_applet.py          # Base class for all applets
│   ├── error_applet.py         # Error display screen
│   └── splash_applet.py        # Boot splash screen
├── applet_manager.py           # Manages applet lifecycle
├── data_manager.py             # Handles API requests and caching
├── main.py                     # Application entry point
├── screen_manager.py           # Display abstraction
├── urllib_urequest.py          # HTTP client
├── web_server.py               # Configuration web interface
├── wifi_manager.py             # Network connection manager
├── transitions.py              # Utility to help manage applet transition effects
├── initialization.py           # Utility to help manage initial ticker setup and loading of big datasets
└── config.py                   # Utility to help manage configurations
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
You can create your own custom applets by subclassing BaseApplet. Add your new applet to applet_manager.py and the SRC list in the makefile.
```
from system_applets.base_applet import BaseApplet
from data_manager import DataManager

class CustomApplet(BaseApplet):
    TTL = 120  # Cache time in seconds
    
    def __init__(self, screen_manager, data_manager: DataManager):
        super().__init__('custom_applet', screen_manager)
        self.data_manager = data_manager
        self.api_url = "https://your-api-endpoint.com/data"
        self.drawn = False
        self.register()
        
    def register(self):
        self.data_manager.register_endpoint(self.api_url, self.TTL)
        
    async def draw(self):
        if self.drawn:
            return
            
        self.screen_manager.clear()
        self.screen_manager.draw_header("Custom Data")
        
        # Get data from cache
        self.data = self.data_manager.get_cached_data(self.api_url)
        
        # Draw your custom display
        self.screen_manager.draw_centered_text("Your Data Here")
        
        self.screen_manager.update()
        self.drawn = True
```
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
