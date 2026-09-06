from screen_manager import ScreenManager


class BaseApplet:
    # Set to True by applets whose frame changes with the wall clock (a live
    # clock, a countdown). Those are redrawn once a second; everything else is
    # only redrawn when the data behind it actually changed.
    TIME_DEPENDENT = False

    def __init__(self, applet_name, screen_manager):
        self.screen_manager: ScreenManager = screen_manager
        self.applet_name = applet_name

    def register(self):
        """Registers the applet's data requirements."""
        print(f"Registering applet {self.applet_name}")

    def start(self):
        """Called when the applet is started."""
        print(f"Starting applet {self.applet_name}")

    def stop(self):
        """Called when the applet is stopped."""
        self.screen_manager.clear()
        print(f"Stopping applet {self.applet_name}")

    async def update(self):
        """Called every tick to refresh the applet's state."""

    async def draw(self):
        """Called when the applet's output has to be (re)drawn."""


class DataApplet(BaseApplet):
    """
    Base class for every applet that renders one cached HTTP endpoint.

    A subclass normally only sets API_URL / TTL / HEADER and implements
    render(data), which receives the endpoint's own JSON. Everything around it
    - registering the endpoint, pulling the cached copy in update(), clearing
    the screen, the header, the footer and the "Loading..." placeholder - is
    handled here.

    Hooks for the few applets that need more:
      FOOTER_ALWAYS   draw the footer before the loading check, not after
      DICT_PAYLOAD    show "Data Error" when the payload is not a dict
      TIME_DEPENDENT  redraw every second, not only when the data changed
      has_data()      when a frame needs more than this one endpoint
      timestamp()     where the footer time comes from
      draw_loading()  the placeholder shown while has_data() is False
    """

    API_URL = None
    TTL = 120
    HEADER = ""
    FOOTER_ALWAYS = False
    DICT_PAYLOAD = True
    TIME_DEPENDENT = False

    def __init__(self, screen_manager, data_manager):
        super().__init__(self.__class__.__name__, screen_manager)
        self.data_manager = data_manager
        self.current_data = None
        self.register()

    def register(self):
        self.data_manager.register_endpoint(self.API_URL, self.TTL)

    def start(self):
        self.current_data = None
        super().start()

    async def update(self):
        self.current_data = self.data_manager.get_cached_data(self.API_URL)

    def has_data(self):
        """True once there is enough data to draw a real frame."""
        return self.current_data is not None

    def timestamp(self):
        """Fetch time shown in the footer."""
        if isinstance(self.current_data, dict):
            return self.current_data.get('timestamp', None)
        return None

    def payload(self):
        """The endpoint's own JSON, unwrapped from the cache envelope."""
        if isinstance(self.current_data, dict):
            return self.current_data.get('data', {})
        return {}

    def draw_loading(self):
        self.screen_manager.draw_centered_text("Loading...")

    async def draw(self):
        screen = self.screen_manager
        screen.clear()
        screen.draw_header(self.HEADER)

        if self.FOOTER_ALWAYS:
            screen.draw_footer(self.timestamp())

        if not self.has_data():
            self.draw_loading()
            return

        if not self.FOOTER_ALWAYS:
            screen.draw_footer(self.timestamp())

        data = self.payload()
        if self.DICT_PAYLOAD and not isinstance(data, dict):
            print(f"[{self.applet_name}] Unexpected data format: {data}")
            screen.draw_centered_text("Data Error")
            return

        self.render(data)

    def render(self, data):
        """Draw the applet's own content. Subclasses override this."""
