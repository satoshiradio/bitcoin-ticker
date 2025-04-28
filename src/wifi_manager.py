import network
import time
import json
import ntptime

class WiFiManager:
    def __init__(self):
        self.ap_ssid = "SR_Ticker"
        self.ap_password = "havefunstayingpoor"
        self.wlan = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.networks = []
        self.ip = None

    def connect_to_saved_networks(self):
        """
        Attempts to connect to saved networks in the JSON file.
        Returns True if a connection is successful, otherwise False.
        """
        self.wlan.active(True)
        self.networks = self._load_networks()

        if not self.networks:
            print("No networks found in the list.")
            return False

        for network_info in self.networks:
            if self._connect_to_wifi(network_info['ssid'], network_info['password']):
                self.ip = self.wlan.ifconfig()[0]
                return True
        return False

    def _connect_to_wifi(self, ssid, password):
        """
        Attempts to connect to a given Wi-Fi network.
        Returns True if connected successfully, otherwise False.
        """
        self.wlan.connect(ssid, password)
        for _ in range(10):  # Try for up to 10 seconds
            if self.wlan.isconnected():
                self._sync_time()
                print(f'Connected to Wi-Fi network: {ssid}')
                print('IP:', self.wlan.ifconfig())
                return True
            time.sleep(1)

        print(f'Failed to connect to Wi-Fi network: {ssid}')
        return False

    def setup_ap(self):
        """
        Configures and activates the device as an Access Point (AP).
        """
        best_channel = self.select_best_channel()
        self.ap.config(essid=self.ap_ssid, password=self.ap_password, channel=best_channel)
        self.ap.active(True)
        if self.ap.active():
            print('Access Point is active.')
            print('AP IP:', self.ap.ifconfig())
            self.ip = self.ap.ifconfig()[0]

        else:
            print('Failed to activate Access Point.')

    def select_best_channel(self):
        """
        Automatically selects the best Wi-Fi channel by scanning nearby networks.
        Returns the least congested channel (1-11) for 2.4 GHz.
        """
        self.wlan.active(True)
        channel_usage = {ch: 0 for ch in range(1, 12)}  # Initialize channel usage counters (1-11)

        # Scan for networks and count channel usage
        networks = self.wlan.scan()  # Returns: (SSID, BSSID, channel, RSSI, authmode, hidden)
        for net in networks:
            channel = net[2]
            if channel in channel_usage:
                channel_usage[channel] += 1

        # Find the channel with the least congestion
        best_channel = min(channel_usage, key=channel_usage.get)
        print(f"Channel usage: {channel_usage}")
        print(f"Selected best channel: {best_channel}")

        return best_channel
    def is_connected(self):
        """
        Checks if the device is connected to a Wi-Fi network.
        """
        return self.wlan.isconnected()

    def get_ap_ssid(self):
        """
        Returns the SSID of the Access Point.
        """
        return self.ap_ssid

    def save_network(self, ssid, password):
        """
        Saves a new Wi-Fi network to the JSON file if it's not already saved.
        """
        networks = self.networks
        new_network = {"ssid": ssid, "password": password}

        if new_network not in networks:
            networks.append(new_network)
            self._save_networks_to_file(networks)

    def _load_networks(self):
        """
        Loads the list of saved networks from the JSON file.
        """
        try:
            with open("networks.json", "r") as f:
                data = json.load(f)
            return data.get('networks', [])
        except (OSError, ValueError):
            return []

    def _save_networks_to_file(self, networks):
        """
        Saves the list of networks to the JSON file.
        """
        self.networks = networks
        with open("networks.json", "w") as f:
            json.dump({"networks": networks}, f)

    def move_network(self, index, direction):
        """
        Moves a network up or down in the list.
        """
        networks = self.networks
        if direction == "up" and index > 0:
            networks[index], networks[index - 1] = networks[index - 1], networks[index]
        elif direction == "down" and index < len(networks) - 1:
            networks[index], networks[index + 1] = networks[index + 1], networks[index]
        self._save_networks_to_file(networks)

    def remove_network(self, index):
        """
        Removes a network from the saved list.
        """
        networks = self.networks
        if 0 <= index < len(networks):
            networks.pop(index)
            self._save_networks_to_file(networks)

    def _sync_time(self):
        """
        Synchronizes system time with NTP.
        """
        try:
            print("Syncing time with NTP...")
            ntptime.settime(server="pool.ntp.org")
            print("Time synchronized")
        except Exception as e:
            print("Failed to sync time:", e)
