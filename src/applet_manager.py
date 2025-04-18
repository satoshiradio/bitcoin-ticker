import gc
import os
from system_applets import base_applet
import uasyncio as asyncio
import json
import time

from system_applets.splash_applet import SplashApplet
from system_applets.error_applet import ErrorApplet
from applets import (
    bitcoin_applet,
    bitcoin_eur_applet,
    block_height_applet,
    fee_applet,
    moscow_time_applet,
    halving_countdown_applet,
    mempool_status_applet,
    difficulty_applet
)
from config import ConfigManager


class AppletManager:
    def __init__(self, screen_manager, data_manager, wifi_manager) -> None:
        self.screen_manager = screen_manager
        self.data_manager = data_manager
        self.wifi_manager = wifi_manager

        self.current_applet = None
        self.current_index = 0
        self.running = True

        self.next_applet_data = None

        gc.collect()
        self.config_manager = ConfigManager()

        self._register_applets()

    def _register_applets(self) -> None:
        self.all_applets = {
            "bitcoin_applet": bitcoin_applet.bitcoin_applet,
            "bitcoin_eur_applet": bitcoin_eur_applet.bitcoin_eur_applet,
            "block_height_applet": block_height_applet.block_height_applet,
            "fee_applet": fee_applet.fee_applet,
            "moscow_time_applet": moscow_time_applet.moscow_time_applet,
            "halving_countdown_applet": halving_countdown_applet.halving_countdown_applet,
            "mempool_status_applet": mempool_status_applet.mempool_status_applet,
            "difficulty_applet": difficulty_applet.difficulty_applet,
        }
        self.applets = self.load_applets()

    def update_applets(self, applets, filename="applets.json"):
        with open(filename, "w") as f:
            data = []
            for applet in applets:
                data.append({"name": applet["name"], "enabled": applet["enabled"]})
            json.dump(data, f)

    def get_applets_list(self):
        applets = []
        for applet in self.applets:
            applets.append({"name": applet.__class__.__name__, "enabled": True})
        for applet_name in self.all_applets.keys():
            if applet_name not in [applet["name"] for applet in applets]:
                applets.append({"name": applet_name, "enabled": False})
        return applets

    def load_applets(self, filename="applets.json"):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                print(f"[AppletManager] Loaded applets from {filename}")
        except OSError:
            print(f"[AppletManager] Failed to load applets from {filename}. Starting with defaults.")
            data = []
            for applet_name in self.all_applets.keys():
                data.append({"name": applet_name, "enabled": True})
            self.update_applets(data)
        except (ValueError):
            print(f"[AppletManager] Failed to load applets from {filename}. Starting with defaults.")
            data = []
            for applet_name in self.all_applets.keys():
                data.append({"name": applet_name, "enabled": True})
            self.update_applets(data)

        applets = []
        for applet in data:
            if not applet.get('enabled', False):
                continue
            applet_name = applet.get('name')
            if not applet_name:
                print(f"[AppletManager] Invalid applet entry: {applet}")
                continue
            applet_class = self.all_applets.get(applet_name)
            if not applet_class:
                print(f"[AppletManager] Applet not found: {applet_name}")
                continue
            applets.append(applet_class(self.screen_manager, self.data_manager))
        return applets

    def _get_applet_class(self, name):
        return self.all_applets.get(name)

    async def start_applets(self) -> None:
        enabled_applets = self.applets

        if not enabled_applets:
            print("[AppletManager] No applets registered. Displaying error.")
            await self._display_error("No applets registered or enabled.")
            return

        asyncio.create_task(self.data_manager.run())

        while self.running:
            current_applet = enabled_applets[self.current_index]
            await self._run_applet(current_applet)
            self.current_index = (self.current_index + 1) % len(enabled_applets)

    async def _run_applet(self, applet, is_system_applet: bool = False) -> None:
        gc.collect()
        print(f"[AppletManager] Starting applet: {applet.__class__.__name__}")

        if self.current_applet:
            self.current_applet.stop()

        self.screen_manager.clear()
        self.current_applet = applet
        self.current_applet.start()

        applet_duration = max(3, self.config_manager.get_applet_duration())
        print(f"[AppletManager] Using applet duration: {applet_duration} seconds")

        self.running = True

        try:
            start = time.ticks_ms()
            while self.running:
                await self.current_applet.update()
                await self.current_applet.draw()
                self.screen_manager.update()

                elapsed = time.ticks_diff(time.ticks_ms(), start) / 1000
                if elapsed >= applet_duration and not is_system_applet:
                    print(f"[AppletManager] Duration expired after {elapsed:.2f}s")
                    await self._advance_to_next_applet()
                    break

                await asyncio.sleep(0.1)

        except Exception as e:
            await self._handle_exception(e)
        finally:
            gc.collect()

    async def run_applet_once(self, applet) -> None:
        gc.collect()
        print(f"[AppletManager] Starting applet: {applet.__class__.__name__}")
        if self.current_applet:
            self.current_applet.stop()
        try:
            self.screen_manager.clear()
            self.current_applet = applet
            self.current_applet.start()
            await self.current_applet.draw()
            self.screen_manager.update()
        except Exception as e:
            await self._handle_exception(e)
        finally:
            gc.collect()

    async def _advance_to_next_applet(self) -> None:
        if not self.applets:
            print("[AppletManager] No applets to advance to.")
            return

        self.current_index = (self.current_index + 1) % len(self.applets)
        next_applet = self.applets[self.current_index]
        if self.next_applet_data:
            next_applet.set_preloaded_data(self.next_applet_data)
            self.next_applet_data = None

        print(f"[AppletManager] Advancing to applet: {next_applet.__class__.__name__}")

    async def _display_error(self, message: str) -> None:
        error_applet = ErrorApplet(self.screen_manager, message)
        await self._run_applet(error_applet, is_system_applet=True)

    async def _handle_exception(self, exception: Exception) -> None:
        print(f"[AppletManager] Exception occurred: {exception}")
        if self.current_applet:
            self.current_applet.stop()

        error_message = str(exception)
        error_applet = ErrorApplet(self.screen_manager, error_message)
        await self._run_applet(error_applet, is_system_applet=True)
        self.running = False
