# Presto-Pet: entry point on the Pimoroni Presto.
#
# Copy this file, config.py and the prestopet/ folder to the root of the device. Wi-Fi is
# optional (secrets.py with WIFI_SSID and WIFI_PASSWORD): it only sets the clock.

import time


def run():
    try:
        import config
    except ImportError:
        config = None

    from prestopet.app import App
    from prestopet.hardware import Presto, TimeSync, load_wifi

    hw = Presto()
    wifi = load_wifi()
    sync = None
    if wifi is not None:
        try:
            sync = TimeSync(wifi[0], wifi[1], getattr(config, "NTP_HOST", None))
        except Exception as e:
            print("No network:", repr(e))
    App(hw, config, sync).run()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        raise
    except Exception as e:
        # Failure at boot: try again from scratch rather than leaving a black screen.
        print("Unexpected stop:", repr(e))
        time.sleep(10)
        import machine
        machine.reset()
