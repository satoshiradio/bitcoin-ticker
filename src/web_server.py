from applet_manager import AppletManager
import applet_manager
import uasyncio as asyncio
import json
import machine
import gc
import time
import wifi_manager  # Your custom WiFiManager module
from config import ConfigManager  # Added import for ConfigManager

def safe_convert_to_int(value, default=0) -> int:
    """
    Safely convert a value to int, returning `default` on error.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class AsyncWebServer:
    """
    A fully asynchronous web server for configuring Wi-Fi networks,
    selecting applets, and optionally rebooting the device.
    Uses uasyncio.start_server for non-blocking I/O.

    :param wifi_manager: An instance responsible for loading,
                         saving, and manipulating Wi-Fi credentials.
    """
    # Add config_manager parameter - This was the intended change
    def __init__(self, wifi_manager: wifi_manager.WiFiManager, applet_manager: applet_manager.AppletManager, config_manager: ConfigManager) -> None:
        self.wifi_manager = wifi_manager
        self.applet_manager = applet_manager
        self.config_manager = config_manager # Use the passed instance
        self.ip_address = self.wifi_manager.ip
        self._boot_time = time.time()

        # Remove instantiation here, use the passed instance
        # self.config_manager = ConfigManager()

        # No need to cache applets here, get dynamically
        # self.applets = self.applet_manager.get_applets_list()
        self.routes = {
            "GET /": self.handle_root,  # Serve the main HTML page
            "GET /networks": self.handle_get_networks,
            "GET /applets": self.handle_get_applets,
            "GET /config": self.handle_get_config,
            "GET /transitions": self.handle_get_transitions, # Route to get available transitions
            "POST /submit": self.handle_submit_network,
            "POST /move_up": self.handle_move_up,
            "POST /move_down": self.handle_move_down,
            "POST /remove": self.handle_remove_network,
            "POST /select_applets": self.handle_select_applets,
            "POST /update_config": self.handle_update_config,  # New route to update config
            "POST /reboot": self.handle_reboot,
            "POST /test_disconnect": self.handle_test_disconnect,
            "GET /health": self.handle_health,
        }
        # Routes that don't require auth (unauthenticated access)
        self._public_routes = {
            "GET /",
            "POST /submit",  # AP setup needs to add networks without auth
        }

    async def handle_root(self, request_lines, writer):
        """Stream index.html straight off flash; it is far too big to hold in RAM."""
        gc.collect()
        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/html\r\n"
            b"Connection: close\r\n\r\n"
        )
        await writer.drain()
        try:
            with open(self.HTML_FILE, "rb") as f:
                while True:
                    chunk = f.read(512)
                    if not chunk:
                        break
                    writer.write(chunk)
                    await writer.drain()
        except OSError as e:
            print(f"[AsyncWebServer] Error serving {self.HTML_FILE}: {e}")
            writer.write(b"<html><body>Page not available</body></html>")
            await writer.drain()

    async def handle_get_networks(self, request_lines, writer):
        ssids = [{"ssid": network["ssid"]} for network in self.wifi_manager.networks]
        response_body = json.dumps(ssids)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n\r\n" + response_body
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()
        
    async def handle_get_applets(self, request_lines, writer):
        # Fetch the current applet list directly from the manager
        applets_list = self.applet_manager.get_applets_list()
        response_body = json.dumps(applets_list)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n\r\n" + response_body
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_get_transitions(self, request_lines, writer):
        """Handle GET request for available transition effects"""
        # Import locally or ensure it's available
        from transitions import AVAILABLE_TRANSITIONS
        response_body = json.dumps(AVAILABLE_TRANSITIONS)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n\r\n" + response_body
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_get_config(self, request_lines, writer):
        """Handle GET request for configuration settings"""
        config = {
            "applet_duration": self.config_manager.get_applet_duration(),
            "timezone_offset": self.config_manager.get_timezone_offset(),
            "transition_effect": self.config_manager.get_transition_effect(),
            # Never expose the key itself, only whether one is configured
            "api_key_set": bool(self.config_manager.get_api_key())
        }
        response_body = json.dumps(config)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n\r\n" + response_body
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_submit_network(self, request_lines, writer):
        _, body = self.parse_request_body(request_lines)
        try:
            params = json.loads(body)
            ssid = params.get("ssid", "")
            password = params.get("password", "")
            self.wifi_manager.save_network(ssid, password)
            print(f"[AsyncWebServer] Added Wi-Fi network: {ssid}")
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Wi-Fi network added successfully!"
            )
        except Exception:
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Could not add Wi-Fi network"
            )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_select_applets(self, request_lines, writer):
        print("Select Applets")
        _, body = self.parse_request_body(request_lines)
        try:
            request = json.loads(body)
            # Ensure request is a list and has required fields
            if not isinstance(request, list):
                raise ValueError("Invalid request format - expected list")
            
            for item in request:
                if not isinstance(item, dict) or 'name' not in item or 'enabled' not in item:
                    raise ValueError("Invalid applet format - missing required fields")
            
            # Update applets with validated data
            self.applet_manager.update_applets(request)
            print("[AsyncWebServer] Updated applet selection:", request)
            
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Applet selection updated. Rebooting device..."
            )
            writer.write(response.encode('utf-8'))
            await writer.drain()
            await writer.wait_closed()
            
            # Small delay before reboot to ensure response is sent
            await asyncio.sleep(0.5)
            
            # Trigger device reboot after ensuring response is sent
            import machine
            machine.reset()
        except Exception as e:
            print(e)
            error_message = str(e)  # Convert exception to string
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                f"Could not update applet selection. Error: {error_message}"
            )
            writer.write(response.encode('utf-8'))
            await writer.drain()
    
    async def handle_update_config(self, request_lines, writer):
        """Handle POST request to update configuration settings"""
        _, body = self.parse_request_body(request_lines)
        try:
            params = json.loads(body)

            # Only update fields that are explicitly provided in the request
            if "applet_duration" in params:
                self.config_manager.set_applet_duration(params["applet_duration"])
            if "timezone_offset" in params:
                self.config_manager.set_timezone_offset(params["timezone_offset"])
            if "transition_effect" in params:
                self.config_manager.set_transition_effect(params["transition_effect"])
            if "api_key" in params:
                self.config_manager.set_api_key(params["api_key"])

            # Read back actual values for response
            actual_duration = self.config_manager.get_applet_duration()
            actual_offset = self.config_manager.get_timezone_offset()
            actual_transition = self.config_manager.get_transition_effect()
            actual_api_key_set = bool(self.config_manager.get_api_key())

            print(f"[AsyncWebServer] Updated config: duration={actual_duration}, tz={actual_offset}, transition={actual_transition}")

            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Connection: close\r\n\r\n" +
                json.dumps({
                    "applet_duration": actual_duration,
                    "timezone_offset": actual_offset,
                    "transition_effect": actual_transition,
                    "api_key_set": actual_api_key_set
                })
            )
        except Exception as e:
            print(f"[AsyncWebServer] Error updating config: {e}")
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Could not update configuration"
            )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_move_up(self, request_lines, writer):
        await self.handle_move("up", request_lines, writer)

    async def handle_move_down(self, request_lines, writer):
        await self.handle_move("down", request_lines, writer)

    async def handle_move(self, direction, request_lines, writer):
        _, body = self.parse_request_body(request_lines)
        params = json.loads(body)
        index = params.get("index", -1)
        if index >= 0:
            self.wifi_manager.move_network(index, direction)
            print(f"[AsyncWebServer] Moved network at index {index} {direction}")
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Network moved successfully"
            )
        else:
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Invalid index"
            )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_remove_network(self, request_lines, writer):
        _, body = self.parse_request_body(request_lines)
        params = json.loads(body)
        index = params.get("index", -1)
        if index >= 0:
            self.wifi_manager.remove_network(index)
            print(f"[AsyncWebServer] Removed network at index {index}")
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Network removed successfully"
            )
        else:
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Invalid index"
            )
        writer.write(response.encode('utf-8'))
        await writer.drain()



    async def handle_test_disconnect(self, request_lines, writer):
        """Temporarily disconnect WiFi to test WiFiMonitor reconnect logic."""
        self.wifi_manager.wlan.disconnect()
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n\r\n"
            "WiFi disconnected. Monitor should reconnect within 30s."
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_health(self, request_lines, writer):
        """Health check endpoint returning device status as JSON."""
        import network
        wlan = self.wifi_manager.wlan
        connected = wlan.isconnected()

        uptime_s = int(time.time() - self._boot_time)

        reset_cause = machine.reset_cause()
        RESET_CAUSES = {}
        for attr in ("PWRON_RESET", "HARD_RESET", "WDT_RESET", "DEEPSLEEP_RESET", "SOFT_RESET"):
            if hasattr(machine, attr):
                RESET_CAUSES[getattr(machine, attr)] = attr.lower()
        reset_reason = RESET_CAUSES.get(reset_cause, str(reset_cause))

        wifi_info = {
            "connected": connected,
            "ip": self.wifi_manager.ip if connected else None,
            "rssi": wlan.status('rssi') if connected else None,
        }

        current_applet_name = None
        if self.applet_manager.current_applet:
            try:
                current_applet_name = self.applet_manager.current_applet.__class__.__name__
            except Exception:
                current_applet_name = "unknown"

        enabled_count = len(self.applet_manager.applets) if hasattr(self.applet_manager, 'applets') else 0

        payload = {
            "status": "ok" if connected else "degraded",
            "wifi": wifi_info,
            "uptime_seconds": uptime_s,
            "reset_reason": reset_reason,
            "current_applet": current_applet_name,
            "active_applets": enabled_count,
            "free_memory": gc.mem_free(),
        }

        response_body = json.dumps(payload)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n\r\n" + response_body
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_reboot(self, request_lines, writer):
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n\r\n"
            "Rebooting device..."
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()
        await writer.wait_closed()
        import machine
        machine.reset()

    def parse_request_body(self, request_lines):
        if isinstance(request_lines, list):
            request_lines = "\n".join(request_lines)  # Ensure it's a single string
        if "\r\n\r\n" in request_lines:
            headers, body = request_lines.split("\r\n\r\n", 1)
        elif "\n\n" in request_lines:
            headers, body = request_lines.split("\n\n", 1)
        else:
            headers, body = (request_lines, "")
        return headers, body.strip()  # Strip extra whitespace
    #
    # -------------------- HTML Page --------------------
    #
    # The page is static and fetches its own configuration over /config,
    # so it is served verbatim from flash.
    HTML_FILE = "index.html"
    #
    # -------------------- URL/Form Parsing --------------------
    #
    def url_decode(self, s: str) -> str:
        """
        Decode URL-encoded form data, replacing '+' with space
        and '%xx' with the corresponding character.
        """
        result = ''
        i = 0
        while i < len(s):
            c = s[i]
            if c == '+':
                result += ' '
                i += 1
            elif c == '%':
                hex_value = s[i+1:i+3]
                try:
                    result += chr(int(hex_value, 16))
                except ValueError:
                    print(f"[AsyncWebServer] Malformed percent-encoding: %{hex_value}")
                i += 3
            else:
                result += c
                i += 1
        return result

    def parse_form_data(self, form_data: str) -> dict:
        """
        Parse the URL-encoded form data into a dictionary.
        e.g. 'key1=value1&key2=value2' -> {'key1': 'value1', 'key2': 'value2'}.
        """
        params = {}
        for pair in form_data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = self.url_decode(key)
                value = self.url_decode(value)
                params[key] = value
        return params

    def update_applets(self, selected_applets) -> None:
        """
        Save the user-selected applets to a JSON file.
        """
        self.applet_manager.update_applets(selected_applets)

    #
    def _check_auth(self, method, path, request_lines):
        """Check API key authentication. Returns True if authorized."""
        api_key = self.config_manager.get_api_key()
        if not api_key:
            return True  # No key configured = open access

        route_key = f"{method} {path}"
        if route_key in self._public_routes:
            return True  # Public routes always allowed

        # Extract Authorization header from request lines
        for line in request_lines:
            if line.lower().startswith("authorization:"):
                token = line.split(":", 1)[1].strip()
                if token == f"Bearer {api_key}":
                    return True
        return False

    # -------------------- Request Handling --------------------
    #
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            # 1. Read request line
            request_line_b = await reader.readline()
            if not request_line_b:
                await writer.aclose()
                return
            request_line_s = request_line_b.decode('utf-8', 'ignore').strip()
            method, path, *_ = request_line_s.split(" ", 2) # Use maxsplit=2

            # 2. Read headers
            header_lines_b_list = []
            content_length = 0
            while True:
                line_b = await reader.readline()
                if not line_b: # Connection closed prematurely
                    await writer.aclose()
                    return
                if line_b == b'\r\n': # End of headers
                    break
                header_lines_b_list.append(line_b)
                line_s_decoded = line_b.decode('utf-8', 'ignore').strip()
                if ':' in line_s_decoded:
                    key, value = line_s_decoded.split(":", 1)
                    if key.strip().lower() == 'content-length':
                        try:
                            content_length = int(value.strip())
                        except ValueError:
                            print(f"[AsyncWebServer] Malformed Content-Length: {value.strip()}")
                            content_length = 0 # Treat as no body or handle error

            # 3. Read body
            body_b = b''
            if content_length > 0:
                try:
                    body_b = await reader.readexactly(content_length)
                except asyncio.IncompleteReadError as e:
                    print(f"[AsyncWebServer] IncompleteReadError: expected {e.expected} got {e.partial}")
                    # Handle incomplete body read - e.g., send error response or close
                    await writer.aclose()
                    return


            # 4. Build the line list expected by downstream logic, without ever
            # holding a second copy of the whole request (and without logging
            # headers - they carry the Authorization token).
            print(f"[AsyncWebServer] {method} {path}")

            request_lines_list = [request_line_s]
            for line_b in header_lines_b_list:
                request_lines_list.append(line_b.decode('utf-8', 'ignore').strip())
            header_lines_b_list = None
            # Empty line marks the end of the headers, then the body
            request_lines_list.append("")
            request_lines_list.append(body_b.decode('utf-8', 'ignore'))
            body_b = None

            # Check authentication before route handling
            if not self._check_auth(method, path, request_lines_list):
                unauthorized = (
                    "HTTP/1.1 401 Unauthorized\r\n"
                    "Content-Type: application/json\r\n"
                    "Connection: close\r\n\r\n"
                    '{"error": "unauthorized"}'
                )
                writer.write(unauthorized.encode('utf-8'))
                await writer.drain()
                await writer.aclose()
                return

            # Match the route using the parsed method and path from step 1
            handler = self.routes.get(f"{method} {path}")
            if handler:
                # Call the handler with the correctly formed request_lines_list
                await handler(request_lines_list, writer)
            else:
                # Default response for unknown routes
                response = (
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/plain\r\n"
                    "Connection: close\r\n\r\n"
                    "404 Not Found"
                )
                writer.write(response.encode('utf-8'))
                await writer.drain()
        except Exception as e:
            print(f"[AsyncWebServer] Error handling request: {e}")
            try:
                error_resp = "HTTP/1.1 500 Internal Server Error\r\n\r\n"
                writer.write(error_resp.encode('utf-8'))
                await writer.drain()
            except Exception:
                pass
        finally:
            await writer.aclose()

    #
    # -------------------- Starting the Server --------------------
    #
    async def start_web_server(self) -> None:
        """
        Create an asynchronous server listening on port 80.
        Each new client is handled in `handle_client`.
        """
        server = await asyncio.start_server(self.handle_client, '0.0.0.0', 80)
        print('[AsyncWebServer] Listening on 0.0.0.0:80')
        # Serve forever (non-blocking)
        try:
            while True:
                print("[AsyncWebServer] Waiting for incoming connections...")
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            server.close()
            await server.wait_closed()
            print('[AsyncWebServer] Server stopped.')
