"""
WiFi Monitor — async background task that detects connection loss
and reconnects using saved networks with exponential backoff.
"""

import uasyncio as asyncio
import time
import gc
from pimoroni import RGBLED


class WiFiMonitor:
    """
    Periodically checks WiFi connectivity. If the connection drops,
    attempts to reconnect using saved networks with exponential backoff.

    :param wifi_manager: The application's WiFiManager instance.
    :param led: Optional RGBLED for status indication.
    :param base_interval: Starting check interval in seconds (default 30).
    :param max_interval: Maximum backoff interval in seconds (default 300).
    :param connect_timeout: Seconds to wait per network attempt (default 10).
    """

    def __init__(
        self,
        wifi_manager,
        led=None,
        base_interval: int = 30,
        max_interval: int = 300,
        connect_timeout: int = 10,
    ) -> None:
        self.wifi_manager = wifi_manager
        self.led = led
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.connect_timeout = connect_timeout

        self._current_interval = base_interval
        self._consecutive_failures = 0
        self._was_connected = True
        self._running = False

    def _set_led(self, state: str) -> None:
        if self.led is None:
            return
        if state == "reconnecting":
            # Slow blink orange — managed by caller for duration
            pass
        elif state == "connected":
            self.led.set_rgb(0, 255, 0)   # Green
        elif state == "failed":
            self.led.set_rgb(255, 0, 0)   # Red
        elif state == "off":
            self.led.set_rgb(0, 0, 0)

    async def run(self) -> None:
        """Main monitoring loop. Schedule as a background task."""
        self._running = True
        print("[WiFiMonitor] Started (check every %ds, max backoff %ds)" % (
            self.base_interval, self.max_interval))

        while self._running:
            try:
                await self._check_and_recover()
            except Exception as e:
                print("[WiFiMonitor] Unexpected error: %s" % e)
            await asyncio.sleep(self._current_interval)

    def stop(self) -> None:
        """Signal the monitor to stop on next loop iteration."""
        self._running = False

    async def _check_and_recover(self) -> None:
        """Check connectivity and trigger reconnect if needed."""
        wlan = self.wifi_manager.wlan

        if wlan.isconnected():
            # Connection restored — reset backoff
            if not self._was_connected:
                print("[WiFiMonitor] Connection restored. IP: %s" % wlan.ifconfig()[0])
                self._consecutive_failures = 0
                self._current_interval = self.base_interval
                self._set_led("connected")
                # Turn off LED after brief indication
                await asyncio.sleep(1)
                self._set_led("off")
            self._was_connected = True
            return

        # Not connected
        self._was_connected = False

        print("[WiFiMonitor] WiFi disconnected. Attempting reconnect...")
        self._consecutive_failures += 1

        # Calculate backoff: 30 → 60 → 120 → 240 → 300 (capped)
        self._current_interval = min(
            self.base_interval * (2 ** (self._consecutive_failures - 1)),
            self.max_interval
        )
        print("[WiFiMonitor] Backoff interval set to %ds (failure #%d)" % (
            self._current_interval, self._consecutive_failures))

        if await self._reconnect():
            # Success — reset
            self._consecutive_failures = 0
            self._current_interval = self.base_interval
            self._was_connected = True

            # Re-sync NTP after reconnect
            try:
                self.wifi_manager._sync_time()
            except Exception:
                pass

            self._set_led("connected")
            await asyncio.sleep(1)
            self._set_led("off")
        else:
            # All networks failed
            print("[WiFiMonitor] All networks failed (attempt #%d). "
                  "Will retry in %ds." % (
                      self._consecutive_failures, self._current_interval))

            if self._current_interval >= self.max_interval:
                # Max backoff reached — show persistent fail state
                print("[WiFiMonitor] Max backoff reached. Showing fail state.")
                self._set_led("failed")

    async def _reconnect(self) -> bool:
        """Try all saved networks in order. Returns True if any succeeds."""
        networks = self.wifi_manager._load_networks()
        if not networks:
            print("[WiFiMonitor] No saved networks to try.")
            return False

        wlan = self.wifi_manager.wlan

        for net in networks:
            ssid = net.get("ssid", "")
            password = net.get("password", "")

            if not ssid:
                continue

            print("[WiFiMonitor] Trying network: %s" % ssid)

            # Disconnect and clean state first
            wlan.disconnect()
            await asyncio.sleep(1)

            # Connect
            wlan.connect(ssid, password)
            deadline = time.time() + self.connect_timeout

            while time.time() < deadline:
                if wlan.isconnected():
                    ip = wlan.ifconfig()[0]
                    print("[WiFiMonitor] Connected to %s (IP: %s)" % (ssid, ip))
                    # Update stored IP
                    self.wifi_manager.ip = ip
                    return True
                await asyncio.sleep(1)

            print("[WiFiMonitor] Failed to connect to %s" % ssid)
            wlan.disconnect()
            await asyncio.sleep(0.5)
            gc.collect()

        return False
