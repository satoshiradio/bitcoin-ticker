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
        self._boot_ticks = time.ticks_ms()

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
            "GET /health": self.handle_health,
        }
        # Routes that don't require auth (unauthenticated access)
        self._public_routes = {
            "GET /",
            "POST /submit",  # AP setup needs to add networks without auth
            "GET /config",  # Settings page needs to read current config
            "POST /update_config",  # Settings page needs to save config (including API key removal)
        }
        
    async def handle_root(self, request_lines, writer):
        html = self.web_page()
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "Connection: close\r\n\r\n" + html
        )
        writer.write(response.encode('utf-8'))
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
            "api_key": self.config_manager.get_api_key()
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
            actual_api_key = self.config_manager.get_api_key()

            print(f"[AsyncWebServer] Updated config: duration={actual_duration}, tz={actual_offset}, transition={actual_transition}")

            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Connection: close\r\n\r\n" +
                json.dumps({
                    "applet_duration": actual_duration,
                    "timezone_offset": actual_offset,
                    "transition_effect": actual_transition,
                    "api_key": actual_api_key
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



    async def handle_health(self, request_lines, writer):
        """Health check endpoint returning device status as JSON."""
        import network
        wlan = self.wifi_manager.wlan
        connected = wlan.isconnected()

        uptime_ms = time.ticks_diff(time.ticks_ms(), self._boot_ticks)
        uptime_s = uptime_ms // 1000

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
    # -------------------- HTML Generation --------------------
    #
    def web_page(self) -> str:
        print(f"[AsyncWebServer] IP address: {self.ip_address}")
        
        # Get current config values
        applet_duration = self.config_manager.get_applet_duration()
        timezone_offset = self.config_manager.get_timezone_offset()
        current_transition = self.config_manager.get_transition_effect()

        html = f"""
    <!DOCTYPE html>
    <html lang="en">

    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Satoshi Radio Ticker</title>
    <link rel="icon" type="image/png" href="https://pool.satoshiradio.nl/favicon-32x32.png">
    <style>
        /* General styles */
        body {{
        background-color: #000;
        color: #fff;
        font-family: sans-serif;
        text-align: center;
        text-transform: uppercase;
        margin: 0;
        padding: 20px;
        }}

        /* Drag and Drop styles */
        .applet-columns {{
            display: flex;
            gap: 20px;
            margin: 20px auto;
            max-width: 800px;
        }}

        .applet-column {{
            flex: 1;
            min-height: 300px;
            background: #333;
            border-radius: 5px;
            padding: 10px;
        }}

        .column-header {{
            color: rgb(252, 98, 43);
            text-align: center;
            padding: 10px;
            border-bottom: 1px solid #444;
            font-weight: bold;
        }}

        .applet-card {{
            background: #444;
            padding: 10px;
            margin: 5px 0;
            border-radius: 3px;
            cursor: move;
            transition: background 0.3s;
            text-align: left;
        }}

        .applet-card:hover {{
            background: #555;
        }}

        .applet-card.dragging {{
            opacity: 0.5;
        }}

        @media (max-width: 600px) {{
            .applet-columns {{
                flex-direction: column;
            }}
            
            .applet-column {{
                min-height: 200px;
            }}
        }}

        h1,
        h2 {{
        color: rgb(252, 98, 43);
        }}

        ul {{
        list-style: none;
        padding: 0;
        margin: 0;
        }}

        li {{
        margin: 10px 0;
        padding: 10px;
        background-color: #333;
        border-radius: 5px;
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        }}

        /* Button styles */
        button {{
        background-color: rgb(252, 98, 43);
        border: none;
        color: white;
        padding: 8px 12px;
        border-radius: 3px;
        cursor: pointer;
        font-size: 14px;
        }}

        button:hover {{
        background-color: #e95b33;
        }}

        /* Input fields */
        input[type="text"],
        input[type="password"],
        input[type="number"],
        button {{
        width: 100%;
        padding: 10px;
        margin: 5px 0;
        border: none;
        border-radius: 5px;
        box-sizing: border-box;
        text-transform: none;
        }}

        /* Container adjustments for mobile */
        #networks-container {{
        margin: 0 auto;
        max-width: 400px;
        }}

        @media (max-width: 600px) {{
        body {{
            padding: 10px;
        }}

        li {{
            flex-direction: column;
            align-items: stretch;
            text-align: left;
        }}

        button {{
            width: 100%;
        }}

        input[type="text"],
        input[type="password"],
        input[type="number"] {{
            width: 100%;
        }}
        }}

        #applet-container {{
        display: flex;
        flex-direction: column;
        gap: 10px;
        }}

        #applet-container label {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 10px;
        background-color: #333;
        border-radius: 5px;
        font-size: 14px;
        cursor: pointer;
        }}

        #applet-container input[type="checkbox"] {{
        width: 20px;
        height: 20px;
        cursor: pointer;
        }}

        @media (max-width: 600px) {{
        #applet-container label {{
            flex-direction: column;
            align-items: flex-start;
        }}
        }}
    </style>
    </head>

    <body>
    <h1>Satoshi Radio Ticker</h1>
    <h2>Saved Wi-Fi Networks</h2>
    <div id="networks-container">
        <ul id="networks-list">
        <!-- Networks will be dynamically rendered here -->
        </ul>
    </div>

    <h2>Add New Wi-Fi Network</h2>
    <form id="wifi-form" style="max-width: 400px; margin: 0 auto; text-align: left;">
        <label for="ssid" style="display: block; margin-bottom: 5px;">SSID:</label>
        <input type="text" id="ssid" name="ssid" placeholder="Enter Wi-Fi SSID" required>

        <label for="password" style="display: block; margin-top: 10px; margin-bottom: 5px;">Password:</label>
        <input type="password" id="password" name="password" placeholder="Enter Wi-Fi Password" required>

        <button type="submit" style="margin-top: 15px; width: 100%;">Add Network</button>
    </form>

    <h2>Applet Selection</h2>
    <p style="font-size: 14px; color: #ccc; margin-top: -10px; margin-bottom: 20px;">
        Drag applets by keeping them pressed between columns to enable/disable them.<br>
        Reorder active applets by pressing and dragging them up/down.
    </p>
    <div class="applet-columns">
        <div class="applet-column" id="available">
            <div class="column-header">Available Applets</div>
            <div id="available-container">
                <!-- Available applets will be populated here -->
            </div>
        </div>
        
        <div class="applet-column" id="active">
            <div class="column-header">Active Applets</div>
            <div id="active-container">
                <!-- Active applets will be populated here -->
            </div>
        </div>
    </div>
    <button onclick="saveAppletOrder()" style="max-width: 400px; margin: 20px auto;">Save Applets</button>
    
    <h2>Configuration</h2>
    <form id="config-form" style="max-width: 400px; margin: 0 auto; text-align: left;">
        <label for="applet-duration" style="display: block; margin-bottom: 5px;">Applet Duration (seconds):</label>
        <input type="number" id="applet-duration" name="applet_duration" min="3" max="60" step="1" value="{applet_duration}" required>
        <p style="font-size: 12px; color: #ccc;">Duration must be between 3 and 60 seconds</p>

        <label for="transition-effect" style="display: block; margin-top: 15px; margin-bottom: 5px;">Applet Transition Effect:</label>
        <select id="transition-effect" name="transition_effect" style="width: 100%; padding: 10px; margin: 5px 0; border: none; border-radius: 5px; box-sizing: border-box; background-color: #fff; color: #000;">
            <!-- Options will be populated by JavaScript -->
        </select>
    
        <label for="timezone-offset" style="display: block; margin-top: 15px; margin-bottom: 5px;">Timezone Offset (hours from UTC):</label>
        <input type="number" id="timezone-offset" name="timezone_offset" min="-12" max="14" step="1" value="{timezone_offset}" required>
        <p style="font-size: 12px; color: #ccc;">Valid values between -12 and +14</p>

        <button type="submit" style="margin-top: 15px; width: 100%;">Save Configuration</button>
    </form>

    <h2>API Security</h2>
    <form id="api-key-form" style="max-width: 400px; margin: 0 auto; text-align: left;">
        <label for="api-key" style="display: block; margin-bottom: 5px;">API Key (optional):</label>
        <input type="text" id="api-key" name="api_key" placeholder="Leave empty for open access" style="text-transform: none;">
        <p style="font-size: 12px; color: #ccc;">When set, all endpoints require <code>Authorization: Bearer &lt;key&gt;</code> header.</p>
        <button type="submit" style="margin-top: 15px; width: 100%;">Save API Key</button>
    </form>

    <button onclick="rebootDevice()" style="max-width: 400px; margin: 20px auto;">Reboot Device</button>

    <script>
const serverIP = "{self.ip_address}";

// Auth helper: attach stored API key to all fetch requests
async function apiFetch(url, options = {{}}) {{
  const apiKey = sessionStorage.getItem('api_key');
  const headers = options.headers || {{}};
  if (apiKey) {{
    headers['Authorization'] = 'Bearer ' + apiKey;
  }}
  if (!headers['Content-Type'] && options.body) {{
    headers['Content-Type'] = 'application/json';
  }}
  options.headers = headers;
  return fetch(url, options);
}}

// Fetch and render saved Wi-Fi networks
async function fetchNetworks() {{
  try {{
    const response = await apiFetch(`http://${{serverIP}}/networks`);
    if (response.ok) {{
      const networks = await response.json();
      const networksList = document.getElementById('networks-list');
      networksList.innerHTML = ''; // Clear existing list

      networks.forEach((network, i) => {{
        const li = document.createElement('li');

        // Create a container for text and actions
        const textContainer = document.createElement('div');
        textContainer.style.flex = '1';
        
        // Add sequence number and SSID
        const sequenceNumber = document.createElement('span');
        sequenceNumber.textContent = `${{i + 1}}. `;
        sequenceNumber.style.color = 'rgb(252, 98, 43)';  // Orange color to match theme
        sequenceNumber.style.marginRight = '8px';
        
        textContainer.appendChild(sequenceNumber);
        textContainer.appendChild(document.createTextNode(network.ssid));

        // Add buttons for actions
        const upButton = document.createElement('button');
        upButton.textContent = '↑';
        upButton.onclick = () => moveNetwork('up', i);

        const downButton = document.createElement('button');
        downButton.textContent = '↓';
        downButton.onclick = () => moveNetwork('down', i);

        const removeButton = document.createElement('button');
        removeButton.textContent = '✖';
        removeButton.onclick = () => removeNetwork(i);

        // Append text and buttons to the list item
        li.appendChild(textContainer);

        const buttonContainer = document.createElement('div');
        buttonContainer.style.display = 'flex';
        buttonContainer.style.gap = '10px';
        buttonContainer.appendChild(upButton);
        buttonContainer.appendChild(downButton);
        buttonContainer.appendChild(removeButton);

        li.appendChild(buttonContainer);
        networksList.appendChild(li);
      }});
    }} else {{
      alert('Failed to fetch networks');
    }}
  }} catch (error) {{
    console.error('Error fetching networks:', error);
  }}
}}

// Fetch and render applets
async function fetchApplets() {{
    try {{
        const response = await apiFetch(`http://${{serverIP}}/applets`);
        if (response.ok) {{
            const applets = await response.json();
            console.log('Fetched applets:', applets);  // Debug log
            
            const availableContainer = document.getElementById('available-container');
            const activeContainer = document.getElementById('active-container');
            
            if (!availableContainer || !activeContainer) {{
                console.error('Container elements not found');  // Debug log
                return;
            }}
            
            availableContainer.innerHTML = '';
            activeContainer.innerHTML = '';
            
            // First create all cards but don't append them yet
            const cardMap = new Map();
            applets.forEach(applet => {{
                const card = document.createElement('div');
                card.className = 'applet-card';
                card.draggable = true;
                card.textContent = applet.name;
                card.dataset.appletName = applet.name;
                
                // Add drag event listeners
                card.addEventListener('dragstart', () => {{
                    card.classList.add('dragging');
                }});
                
                card.addEventListener('dragend', () => {{
                    card.classList.remove('dragging');
                }});
                
                cardMap.set(applet.name, {{ card, enabled: applet.enabled }});
            }});
            
            // First append enabled applets in original order
            applets.forEach(applet => {{
                const cardInfo = cardMap.get(applet.name);
                console.log('Processing applet:', applet.name, 'enabled:', applet.enabled, 'cardInfo:', cardInfo);  // Debug log
                if (cardInfo && applet.enabled) {{
                    activeContainer.appendChild(cardInfo.card);
                    console.log('Appended to active:', applet.name);  // Debug log
                }}
            }});

            // Then append disabled applets in original order
            applets.forEach(applet => {{
                const cardInfo = cardMap.get(applet.name);
                if (cardInfo && !applet.enabled) {{
                    availableContainer.appendChild(cardInfo.card);
                    console.log('Appended to available:', applet.name);  // Debug log
                }}
            }});
            
            initDragAndDrop();
        }} else {{
            alert('Failed to fetch applets');
        }}
    }} catch (error) {{
        console.error('Error fetching applets:', error);
    }}
}}

function initDragAndDrop() {{
    const columns = document.querySelectorAll('.applet-column');
    
    columns.forEach(column => {{
        column.addEventListener('dragover', e => {{
            e.preventDefault();
            const draggingCard = document.querySelector('.dragging');
            const container = column.querySelector('div[id$="-container"]');
            const closestCard = getClosestCard(container, e.clientY);
            
            if (closestCard) {{
                container.insertBefore(draggingCard, closestCard);
            }} else {{
                container.appendChild(draggingCard);
            }}
        }});
    }});
}}

function getClosestCard(container, mouseY) {{
    const cards = [...container.querySelectorAll('.applet-card:not(.dragging)')];
    
    return cards.reduce((closest, card) => {{
        const box = card.getBoundingClientRect();
        const offset = mouseY - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {{
            return {{ offset: offset, element: card }};
        }} else {{
            return closest;
        }}
    }}, {{ offset: Number.NEGATIVE_INFINITY }}).element;
}}

function saveAppletOrder() {{
    const activeContainer = document.getElementById('active-container');
    
    // Get active cards in their current order
    const activeCards = [...activeContainer.querySelectorAll('.applet-card')];
    const enabledApplets = activeCards.map(card => ({{
        name: card.dataset.appletName,
        enabled: true
    }}));

    // Get the original order of all applets
    fetch(`http://${{serverIP}}/applets`)
        .then(response => response.json())
        .then(originalApplets => {{
            // First add enabled applets in their current order
            const applets = enabledApplets;
            
            // Then add disabled applets in their original order
            originalApplets.forEach(originalApplet => {{
                if (!enabledApplets.some(enabled => enabled.name === originalApplet.name)) {{
                    applets.push({{
                        name: originalApplet.name,
                        enabled: false
                    }});
                }}
            }});
            
            // Send the updated applets to the server
            return apiFetch(`http://${{serverIP}}/select_applets`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(applets)
            }});
        }})
        .then(response => {{
            if (response.ok) {{
                alert('Applet selection saved successfully! Device will reboot to apply changes.');
            }} else {{
                alert('Failed to save applet order');
            }}
        }})
        .catch(error => {{
            console.error('Error saving applet order:', error);
            alert('Error saving applet order');
        }});
}}

// Fetch configuration
async function fetchConfig() {{
  try {{
    const response = await apiFetch(`http://${{serverIP}}/config`);
    if (response.ok) {{
      const config = await response.json();
      document.getElementById('applet-duration').value = config.applet_duration;
      document.getElementById('timezone-offset').value = config.timezone_offset;
      // Set the selected transition effect in the dropdown
      const transitionSelect = document.getElementById('transition-effect');
      if (transitionSelect) {{
          transitionSelect.value = config.transition_effect;
      }}
    }} else {{
      alert('Failed to fetch configuration');
    }}
  }} catch (error) {{
    console.error('Error fetching configuration:', error);
  }}
}}

// Fetch available transitions and populate dropdown
async function fetchTransitions() {{
  try {{
    const response = await apiFetch(`http://${{serverIP}}/transitions`);
    if (response.ok) {{
      const transitions = await response.json();
      const selectElement = document.getElementById('transition-effect');
      selectElement.innerHTML = ''; // Clear existing options
      transitions.forEach(effect => {{
        const option = document.createElement('option');
        option.value = effect;
        option.textContent = effect;
        selectElement.appendChild(option);
      }});
      // After populating, fetch the current config to set the selected value
      fetchConfig();
    }} else {{
      alert('Failed to fetch transition options');
    }}
  }} catch (error) {{
    console.error('Error fetching transitions:', error);
  }}
}}

// Move a network up or down
async function moveNetwork(direction, index) {{
  try {{
    const response = await apiFetch(`http://${{serverIP}}/move_${{direction}}`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{index}}),
    }});
    if (response.ok) {{
      fetchNetworks();
    }} else {{
      alert('Failed to move network');
    }}
  }} catch (error) {{
    console.error(`Error moving network ${{direction}}:`, error);
  }}
}}

async function rebootDevice() {{
    try {{
        const response = await apiFetch(`http://${{serverIP}}/reboot`, {{
            method: 'POST',
        }});
        if (response.ok) {{
            alert('Rebooting device...');
        }} else {{
            alert('Failed to reboot device');
        }}
    }} catch (error) {{
        console.error('Error rebooting device:', error);
    }}
}}
async function addNetwork(event) {{
  event.preventDefault();
  const form = document.getElementById('wifi-form');
  const data = Object.fromEntries(new FormData(form));

  try {{
    const response = await apiFetch(`http://${{serverIP}}/submit`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(data),
    }});
    if (response.ok) {{
      alert('Network added successfully!');
      form.reset();
      fetchNetworks();
    }} else {{
      alert('Failed to add network');
    }}
  }} catch (error) {{
    console.error('Error adding network:', error);
  }}
}}

// Remove a network
async function removeNetwork(index) {{
  try {{
    const response = await apiFetch(`http://${{serverIP}}/remove`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{index}}),
    }});
    if (response.ok) {{
      fetchNetworks();
    }} else {{
      alert('Failed to remove network');
    }}
  }} catch (error) {{
    console.error('Error removing network:', error);
  }}
}}

// Save applet selections
async function saveApplets(event) {{
  event.preventDefault();
  const checkboxes = Array.from(document.querySelectorAll('#applet-form input[type="checkbox"]'));
  const applets = checkboxes.map(checkbox => ({{
    name: checkbox.value,
    enabled: checkbox.checked,
  }}));

  try {{
    const response = await apiFetch(`http://${{serverIP}}/select_applets`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(applets),
    }});
    if (response.ok) {{
      alert('Applet selection saved successfully! Device will reboot in a few seconds to apply changes.');
    }} else {{
      alert('Failed to save applet selection');
    }}
  }} catch (error) {{
    console.error('Error saving applet selection:', error);
  }}
}}

// Save configuration
async function saveConfig(event) {{
  event.preventDefault();
  const form = document.getElementById('config-form');
  const formData = new FormData(form);
  const data = {{
    applet_duration: parseInt(formData.get('applet_duration'), 10),
    timezone_offset: parseInt(formData.get('timezone_offset'), 10),
    transition_effect: formData.get('transition_effect') // Get selected transition
  }};

  try {{
    const response = await apiFetch(`http://${{serverIP}}/update_config`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(data),
    }});
    
    if (response.ok) {{
      const result = await response.json();
      // Update fields with actual values (in case they were adjusted/validated)
      document.getElementById('applet-duration').value = result.applet_duration;
      document.getElementById('timezone-offset').value = result.timezone_offset;
      document.getElementById('transition-effect').value = result.transition_effect;
      alert('Configuration saved successfully!');
    }} else {{
      alert('Failed to save configuration');
    }}
  }} catch (error) {{
    console.error('Error saving configuration:', error);
  }}
}}

document.getElementById('api-key-form').addEventListener('submit', async function(event) {{
  event.preventDefault();
  const apiKey = document.getElementById('api-key').value;
  try {{
    const response = await apiFetch(`http://${{serverIP}}/update_config`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{api_key: apiKey}})
    }});
    if (response.ok) {{
      sessionStorage.setItem('api_key', apiKey);
      alert('API key saved!');
    }} else {{
      alert('Failed to save API key');
    }}
  }} catch (error) {{
    console.error('Error saving API key:', error);
  }}
}});

// Attach handlers
document.getElementById('wifi-form').addEventListener('submit', addNetwork);
document.getElementById('config-form').addEventListener('submit', saveConfig);

// Initial fetch — load API key first, then fetch secured endpoints
(async function init() {{
  try {{
    const response = await apiFetch(`http://${{serverIP}}/config`);
    if (response.ok) {{
      const config = await response.json();
      document.getElementById('api-key').value = config.api_key || '';
      if (config.api_key) {{
        sessionStorage.setItem('api_key', config.api_key);
      }} else {{
        sessionStorage.removeItem('api_key');
      }}
    }}
  }} catch (e) {{}}
  // Now fetch everything with the key available in sessionStorage
  fetchNetworks();
  fetchApplets();
  fetchTransitions();
}})();
    </script>
    </body>

    </html>
        """
        return html
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
    # -------------------- Request Handling --------------------
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


            # 4. Reconstruct the full raw request string
            # request_line_b already includes its \r\n (or just \n if readline behaves that way)
            # header_lines_b_list items also include their \r\n
            # We need one \r\n between last header and body.
            full_request_b = request_line_b + b''.join(header_lines_b_list) + b'\r\n' + body_b
            full_request_s = full_request_b.decode('utf-8', 'ignore')
            
            print('[AsyncWebServer] Received request:\n', full_request_s) # Log the full reconstructed request

            # 5. Split into lines as expected by downstream logic
            request_lines_list = full_request_s.split("\r\n")

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
