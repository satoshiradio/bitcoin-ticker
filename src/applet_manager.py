import gc
import os
import uerrno
from system_applets import base_applet
import uasyncio as asyncio
import json
import time
import transitions # Import the new transitions module

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
    difficulty_applet,
    ath_applet, # Import the new applet
    fear_and_greed_applet, # Import the Fear and Greed applet
    dominance_applet, # Import the Bitcoin Dominance applet
    ath_eur_applet # Import the Bitcoin EUR ATH applet
)
from config import ConfigManager


class AppletManager:
    # Add config_manager parameter
    def __init__(self, screen_manager, data_manager, wifi_manager, config_manager: ConfigManager) -> None:
        self.screen_manager = screen_manager
        self.data_manager = data_manager
        self.wifi_manager = wifi_manager
        self.config_manager = config_manager # Use the passed instance

        self.current_applet = None
        self.current_index = 0
        self.running = True

        self.next_applet_data = None

        gc.collect()
        # Remove instantiation here, use the passed instance
        # self.config_manager = ConfigManager()

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
            "ath_applet": ath_applet.ath_applet, # Add the new applet here
            "fear_and_greed_applet": fear_and_greed_applet.fear_and_greed_applet, # Add Fear and Greed applet
            "dominance_applet": dominance_applet.dominance_applet, # Add Bitcoin Dominance applet
            "ath_eur_applet": ath_eur_applet.ath_eur_applet, # Add Bitcoin EUR ATH applet
        }
        self.applets = self.load_applets()

    def update_applets(self, applets, filename="applets.json"):
        with open(filename, "w") as f:
            # The 'applets' parameter is expected to be a list of dicts:
            # [{"name": "applet_name", "enabled": True/False}, ...]
            # This list comes directly from the web_server's parsed JSON body.
            json.dump(applets, f) # Directly dump the received list, assuming it's correctly formatted
        self.applets = self.load_applets(filename)
        self.current_index = 0
        print(f"[AppletManager] Applets updated and reloaded.")

    def refresh_applet_list(self):
        """Reloads the applet list from applets.json. Called after potential initialization."""
        print("[AppletManager] Refreshing applet list after potential initialization.")
        self.applets = self.load_applets()
        self.current_index = 0 # Reset index as the list might have changed
        if self.applets:
            print(f"[AppletManager] Applet list refreshed. {len(self.applets)} applets loaded.")
        else:
            print("[AppletManager] Applet list refreshed, but no applets were loaded (file might be empty or all disabled).")

    def get_applets_list(self):
        saved_data = [] # Initialize to empty list
        try:
            with open("applets.json", "r") as f:
                saved_data = json.load(f)
        except OSError as e:
             if e.args[0] == uerrno.ENOENT:
                 print("[AppletManager] applets.json not found in get_applets_list. Returning defaults.")
                 # Initializer should have created it, but proceed with defaults if missing.
             else:
                 print(f"[AppletManager] OS Error reading applets.json in get_applets_list: {e}")
             # saved_data remains []
        except ValueError:
             print("[AppletManager] Value Error parsing applets.json in get_applets_list.")
             # saved_data remains []

        # Default all known applets to disabled
        default_data = [{"name": name, "enabled": False} for name in self.all_applets.keys()]

        # Build a lookup from the saved file
        applet_map = {entry["name"]: entry.get("enabled", False) for entry in saved_data}

        # Merge saved state into the full list
        for entry in default_data:
            name = entry["name"]
            entry["enabled"] = applet_map.get(name, False)

        return default_data # Return the merged list


    def load_applets(self, filename="applets.json"):
        data = None
        try:
            # Check if file exists first without trying to open it directly
            os.stat(filename)
            # File exists, try to open and load
            with open(filename, "r") as f:
                data = json.load(f)
                print(f"[AppletManager] Loaded applets from {filename}")
        except OSError as e:
            if e.args[0] == uerrno.ENOENT: # Check if the error is "No such file or directory"
                # File not found - Initializer should have created it.
                # If it's still not here, something went wrong. Log error and return empty.
                print(f"[AppletManager] ERROR: {filename} not found, even after initialization step. Returning empty applet list.")
                return []
            else:
                # Handle other potential OS errors (permissions, etc.)
                print(f"[AppletManager] WARNING: OS error reading {filename}: {e}. Returning empty applet list.")
                return []
        except ValueError:
            # Handle JSON parsing errors
            print(f"[AppletManager] WARNING: Failed to parse JSON from {filename}. Invalid format. Returning empty applet list.")
            return []

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
            # Instantiate the applet
            applet_instance = applet_class(self.screen_manager, self.data_manager)
            # Register its data requirements with the DataManager
            applet_instance.register()
            applets.append(applet_instance)
        return applets

    def _get_applet_class(self, name):
        return self.all_applets.get(name)

    async def start_applets(self) -> None:
        # Removed redundant enabled_applets = self.applets
        # The loop below checks self.applets directly

        if not self.applets: # Check initial state
            print("[AppletManager] No applets registered or enabled at start. Displaying error.")
            await self._display_error("No applets registered or enabled.")
            return

        asyncio.create_task(self.data_manager.run())

        while self.running:
            # Check if the applet list is empty (e.g., user disabled all)
            if not self.applets:
                print("[AppletManager] No enabled applets. Waiting...")
                # Display a message or just wait? Let's wait to avoid constant error screen.
                # Consider adding a dedicated "No Applets Enabled" applet later if needed.
                await asyncio.sleep(5)
                continue # Skip the rest of the loop and re-check

            # Ensure the current index is valid for the *current* list length
            # This handles cases where the list was modified (e.g., by web UI)
            if self.current_index >= len(self.applets):
                print(f"[AppletManager] Current index {self.current_index} out of bounds (len={len(self.applets)}). Resetting to 0.")
                self.current_index = 0

            # Check again if list became empty after index reset
            if not self.applets:
                await asyncio.sleep(1)
                continue

            # Get the current applet using the potentially updated index and list
            # Get the current applet using the potentially updated index and list
            current_applet = self.applets[self.current_index]
            await self._run_applet(current_applet)


    async def _run_applet(self, applet, is_system_applet: bool = False) -> None:
        gc.collect()

        # --- Transition Out ---
        if self.current_applet:
            print(f"[AppletManager] Stopping applet: {self.current_applet.__class__.__name__}")
            # Get the *current* transition setting just before potentially running the exit transition
            selected_transition_name = self.config_manager.get_transition_effect()
            # print(f"[AppletManager] Read transition for exit: '{selected_transition_name}'") # REMOVED LOGGING
            exit_transition, _ = transitions.TRANSITIONS.get(selected_transition_name, (None, None)) # Only need exit func here
            if exit_transition:
                print(f"[AppletManager] Running exit transition: {selected_transition_name}")
                await exit_transition(self.screen_manager) # Run exit transition before stopping
            self.current_applet.stop()
            gc.collect()

        # --- Start New Applet ---
        print(f"[AppletManager] Starting applet: {applet.__class__.__name__}")
        self.screen_manager.clear() # Clear screen before starting new applet or entry transition
        self.current_applet = applet
        self.current_applet.start()

        # Prepare the applet's data *before* the transition starts
        await self.current_applet.update()

        # --- Transition In ---
        # Get the *current* transition setting just before potentially running the entry transition
        selected_transition_name = self.config_manager.get_transition_effect()
        # print(f"[AppletManager] Read transition for entry: '{selected_transition_name}'") # REMOVED LOGGING
        _, entry_transition = transitions.TRANSITIONS.get(selected_transition_name, (None, None)) # Only need entry func here

        if entry_transition:
            print(f"[AppletManager] Running entry transition: {selected_transition_name}")
            # Check if the transition name indicates a wipe effect requiring the applet instance
            if "Wipe" in selected_transition_name:
                 # All Wipe transitions require the applet instance to draw during the wipe
                await entry_transition(self.screen_manager, self.current_applet)
            elif selected_transition_name == "Fade":
                # Fade In draws the first frame, then fades the backlight
                await self.current_applet.draw() # Draw first frame
                self.screen_manager.update()      # Update display buffer
                await entry_transition(self.screen_manager) # Run fade_in
            else:
                 # Handle other potential future transitions or default to just drawing
                 # Check against the actual key used in transitions.py
                 print(f"[AppletManager] Unknown or unsupported entry transition '{selected_transition_name}', drawing directly.")
                 await self.current_applet.draw()
                 self.screen_manager.update()
                 self.screen_manager.display.set_backlight(1.0) # Ensure backlight is on
        else:
            # No transition ("None")
            print("[AppletManager] No entry transition, drawing directly.")
            self.screen_manager.display.set_backlight(1.0) # Ensure backlight is on
            await self.current_applet.draw() # Draw the applet content
            self.screen_manager.update() # Update display buffer


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
                    await self._advance_to_next_applet()
                    break # Exit the _run_applet loop to let start_applets pick the next one

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
            gc.collect()
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
            gc.collect()

        error_message = str(exception)
        error_applet = ErrorApplet(self.screen_manager, error_message)
        await self._run_applet(error_applet, is_system_applet=True)
        self.running = False
