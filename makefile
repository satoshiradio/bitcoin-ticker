# Define variables
DEVICE_PORT=/dev/tty.usbmodem2112401
#DEVICE_PORT=/dev/tty.usbmodem2143101
SOURCE_DIR = .           # Replace with your actual source directory
AMPY = ampy -p $(DEVICE_PORT)  

# All files that need to live on the device (code, web UI and images).
# Images are Python modules holding raw JPEG bytes: MicroPython's freezer only
# picks up .py files, so a release .uf2 would otherwise ship without them.
SRC =  						src/main.py \
							src/applet_manager.py \
	 						src/screen_manager.py \
							src/data_manager.py \
							src/wifi_manager.py \
							src/wifi_monitor.py \
							src/web_server.py \
							src/config.py \
							src/initialization.py \
							src/transitions.py \
							src/utils.py \
			  				src/urllib_urequest.py \
							src/index.html \
							src/splash_image.py \
							src/ap_qr_image.py \
							src/system_applets/base_applet.py \
							src/system_applets/ap_applet.py \
							src/system_applets/error_applet.py \
							src/system_applets/splash_applet.py \
							src/applets/bitcoin_applet.py \
							src/applets/bitcoin_eur_applet.py \
							src/applets/bitcoin_gold_ratio_applet.py \
							src/applets/block_height_applet.py \
							src/applets/difficulty_applet.py \
							src/applets/dominance_applet.py \
							src/applets/ath_applet.py \
							src/applets/ath_eur_applet.py \
							src/applets/fear_and_greed_applet.py \
							src/applets/halving_countdown_applet.py \
							src/applets/fee_applet.py \
							src/applets/mempool_status_applet.py \
							src/applets/moscow_time_applet.py



# Default target: Upload all files
all: upload run

# Upload all Python files to the MicroPython device with progress feedback
upload:
	@echo "Uploading files to the MicroPython device..."
	@for file in $(SRC); do \
		echo "Uploading $$file..."; \
		dest_file=$$(echo $$file | sed 's/^src\///'); \
		$(AMPY) put $$file $$dest_file || exit 1; \
	done
	@echo "Upload complete."

upload_fzf:
	@selected_file=$$(echo "$(SRC)" | tr ' ' '\n' | fzf --prompt="Select a file to upload: "); \
	if [ -n "$$selected_file" ]; then \
		echo "Uploading $$selected_file..."; \
		dest_file=$$(echo $$selected_file | sed 's/^src\///'); \
		$(AMPY) put $$selected_file $$dest_file && echo "File uploaded successfully."; \
	else \
		echo "No file selected. Aborting."; \
	fi

run:
	$(AMPY) run -n src/main.py

restart:
	$(AMPY) reset --hard

# Clean all files from the MicroPython device (optional)
clean:
	@echo "Removing all files from the MicroPython device..."
	@for file in $(PYTHON_FILES); do \
		$(AMPY) rm $$(echo $$file | sed "s|^$(SOURCE_DIR)||"); \
	done
	@echo "Clean complete."

# List files on the MicroPython device (optional)
list:
	$(AMPY) ls

# Reset the MicroPython device (optional)
reset:
	$(AMPY) reset

# list devices
devices:
	ls -l /dev/tty.usb*

create_folders:
	$(AMPY) mkdir applets
	$(AMPY) mkdir system_applets


serial:
	screen $(DEVICE_PORT) 115200
