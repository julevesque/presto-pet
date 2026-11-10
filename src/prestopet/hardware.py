# Everything specific to the Pimoroni Presto: screen, touch, backlight, the 7 LEDs on the
# back and the optional
# Wi-Fi used only to set the clock. Nothing else in the game imports the firmware modules.

import time

NTP_RESYNC_S = 12 * 3600
NTP_RETRY_S = 300
WIFI_CONNECT_S = 20


class Presto:
    def __init__(self, backlight=0.01):
        from presto import Presto as Board
        try:
            self.board = Board(ambient_light=False, full_res=True, layers=1)
        except TypeError:
            self.board = Board(full_res=True)
        self.display = self.board.display
        self.touch = self.board.touch
        self.backlight = backlight
        self.leds = hasattr(self.board, "set_led_rgb")
        self.board.set_backlight(0)

    def screen_on(self, on):
        self.board.set_backlight(self.backlight if on else 0)

    def set_leds(self, colours):
        """One (r, g, b) from 0 to 255 per LED. Quietly does nothing on a firmware without them."""
        if not self.leds:
            return
        try:
            for i, (r, g, b) in enumerate(colours):
                self.board.set_led_rgb(i, r, g, b)
        except Exception as e:
            print("LEDs unavailable:", repr(e))
            self.leds = False

    def read_touch(self):
        """(down, x, y)"""
        try:
            self.touch.poll()
            return bool(self.touch.state), self.touch.x, self.touch.y
        except Exception:
            return False, 0, 0


def load_wifi():
    """(ssid, password) from secrets.py, as in Pimoroni's examples, or None. The network is
    optional: it only sets the clock."""
    try:
        import secrets
    except ImportError:
        return None
    ssid = getattr(secrets, "WIFI_SSID", "")
    password = getattr(secrets, "WIFI_PASSWORD", "")
    if not isinstance(ssid, str) or not ssid or ssid == "...":
        return None
    return ssid, password


class TimeSync:
    """Connects to Wi-Fi without blocking the game, sets the clock by NTP, then switches the
    radio off until the next synchronisation."""

    def __init__(self, ssid, password, ntp_host=None):
        import network
        self.network = network
        self.ssid = ssid
        self.password = password
        self.ntp_host = ntp_host
        self.wlan = None
        self.started = None
        self.next_try = time.ticks_ms()
        self.synced = False

    def _radio(self, on):
        if on:
            if self.wlan is None:
                self.wlan = self.network.WLAN(self.network.STA_IF)
            self.wlan.active(True)
        elif self.wlan is not None:
            try:
                self.wlan.disconnect()
            except Exception:
                pass
            self.wlan.active(False)

    def poll(self, now):
        if self.started is None:
            if time.ticks_diff(now, self.next_try) < 0:
                return
            print("Wi-Fi: connecting to", self.ssid)
            try:
                self._radio(True)
                self.wlan.connect(self.ssid, self.password)
            except Exception as e:
                print("Wi-Fi:", repr(e))
                self._retry(now)
                return
            self.started = now
            return
        if self.wlan.isconnected():
            try:
                import ntptime
                if self.ntp_host:
                    ntptime.host = self.ntp_host
                try:
                    ntptime.timeout = 2
                except AttributeError:
                    pass
                ntptime.settime()  # the hardware clock in UTC
                self.synced = True
                print("Clock set by NTP")
                self.started = None
                self._radio(False)
                self.next_try = time.ticks_add(now, NTP_RESYNC_S * 1000)
            except Exception as e:
                print("NTP:", repr(e))
                self._retry(now)
        elif time.ticks_diff(now, self.started) > WIFI_CONNECT_S * 1000:
            print("Wi-Fi: no connection")
            self._retry(now)

    def _retry(self, now):
        self.started = None
        self._radio(False)
        self.next_try = time.ticks_add(now, NTP_RETRY_S * 1000)
