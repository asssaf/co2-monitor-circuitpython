"""
Air quality monitor
"""
import asyncio
import time

from adafruit_display_text import label
import adafruit_il0373
from adafruit_lc709203f import LC709203F
import adafruit_scd4x
from analogio import AnalogIn
import alarm # pylint: disable=import-error
import board
import digitalio
import displayio
import neopixel
import supervisor # pylint: disable=import-error
import terminalio

WAIT_FOR_DATA_READY_SECONDS = 1
WAIT_FOR_MEASUREMENTS_TRIES = 60
MIN_TIME_BETWEEN_REFRESH_SECONDS = 180
DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128
DISPLAY_ENABLED = True
BATTERY_VOLTAGE_PIN = None
BATTERY_I2C = 0xb
DONE_PIN = board.A0

print("Starting...")

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.1
pixel.fill((0, 255, 0))


# pylint: disable=too-few-public-methods
class BatteryMonitor:
    """
    Battery monitor
    """
    def __init__(self, in_pin):
        self.voltage = None
        self.in_pin = in_pin

    async def fetch(self):
        """
        fetch the battery voltage through the analog pin
        """
        print("getting battery voltage")
        self.voltage = 3.3 * self.in_pin.value / 65536 * 2
        print(f"battery voltage: {self.voltage:0.2f} V")


class I2CBatteryMonitor:
    """
    Battery Monitor using LC709203
    """
    def __init__(self, sensor):
        self.voltage = None
        self.percent = None
        self.sensor = sensor

    async def fetch(self):
        """
        fetch the battery voltage through i2c
        """
        print("getting battery voltage")
        self.voltage = self.sensor.cell_voltage
        self.percent = self.sensor.cell_percent
        print(f"battery voltage: {self.voltage:0.2f} V  ({self.percent:0.2f}%)")


class CO2Monitor:
    """
    CO2 Monitor
    """
    def __init__(self, sensor):
        self.sensor = sensor

    async def fetch(self):
        """
        get a single measurement
        """
        print("starting co2 measurement")
        self.sensor.start_periodic_measurement()
        print("waiting for co2 measurement...")

        for _ in range(WAIT_FOR_MEASUREMENTS_TRIES):
            if self.sensor.data_ready:
                print(f"CO2: {self.sensor.CO2} ppm")
                print(f"Temperature: {self.sensor.temperature:0.1f} *C")
                print(f"Humidity: {self.sensor.relative_humidity:0.1f} %")
                print()
                break
            await asyncio.sleep(WAIT_FOR_DATA_READY_SECONDS)

        print("stopping co2 measurement...")
        self.sensor.stop_periodic_measurement()
        print("stopped co2 measurement")


def deep_sleep(seconds):
    """
    set up a wake up alarm and go to deep sleep
    """
    # trigger the done output
    if DONE_PIN:
        done_pin = digitalio.DigitalInOut(DONE_PIN)
        done_pin.direction = digitalio.Direction.OUTPUT
        while True:
            done_pin.value = True
            time.sleep(1/1000000.0)
            done_pin.value = False
            time.sleep(1/1000000.0)

    # Create a an alarm that will trigger 20 seconds from now.
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + seconds)
    # Exit the program, and then deep sleep until the alarm wakes us.
    print(f"Going to sleep for {seconds} seconds...")
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)


def shutdown():
    """
    go to sleep
    """
    pixel.fill((0, 0, 0))
    deep_sleep(MIN_TIME_BETWEEN_REFRESH_SECONDS)


# pylint: disable=too-many-locals
def update_display(co2_monitor, battery_monitor, i2c_battery_monitor):
    """
    update display
    """
    top_group = displayio.Group()

    background_color = 0xFFFFFF
    background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    palette = displayio.Palette(1)
    palette[0] = background_color
    background_tile = displayio.TileGrid(background_bitmap, pixel_shader=palette)

    font = terminalio.FONT
    color = 0x000000

    co2_text = "0"
    if co2_monitor:
        co2_text = f"{co2_monitor.sensor.CO2}"

    co2_label = label.Label(font, text=co2_text, color=color, scale=3)
    co2_label.anchor_point = (0.5, 0.5)
    co2_label.anchored_position = (DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2)

    battery_voltage_text = ""
    if battery_monitor:
        battery_voltage_text = f"{battery_monitor.voltage:0.2f} V"

    if i2c_battery_monitor:
        battery_voltage_text += f"{i2c_battery_monitor.voltage:0.2f} V"
        battery_voltage_text += f" ({i2c_battery_monitor.percent:0.2}%)"

    battery_label = label.Label(font, text=battery_voltage_text, color=color, scale=1)
    battery_label.anchor_point = (0.0, 1.0)
    battery_label.anchored_position = (10, DISPLAY_HEIGHT -10)

    top_group.append(background_tile)
    top_group.append(co2_label)
    top_group.append(battery_label)

    if not DISPLAY_ENABLED:
        return

    displayio.release_displays()
    spi = board.SPI()
    epd_cs = board.D9
    epd_dc = board.D10
    display_bus = displayio.FourWire(
        spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000
    )

    display = adafruit_il0373.IL0373(
        display_bus,
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        rotation=270,
        black_bits_inverted=False,
        color_bits_inverted=False,
        grayscale=True,
        refresh_time=1,
    )

    print(f"Display time to refresh: {display.time_to_refresh}")
    if display.time_to_refresh > 0:
        time.sleep(display.time_to_refresh)

    display.show(top_group)

    print("Refreshing display")
    display.refresh()
    #print(f"Display busy: {display.busy}")
    if DONE_PIN:
        # wait for the display to actually finish updating before cutting power
        time.sleep(5)

    print("Done refreshing display")

    displayio.release_displays()


async def main():
    """
    Main entry point
    """
    if supervisor.runtime.usb_connected and not alarm.wake_alarm and not DONE_PIN:
        print("Woke up without an alarm")
        # go to sleep to avoid refreshing the display too soon
        shutdown()

    tasks = []

    co2_monitor = None
    try:
        i2c = board.I2C()
        scd4x = adafruit_scd4x.SCD4X(i2c)
        scd4x.self_calibration_enabled = False
        co2_monitor = CO2Monitor(scd4x)

    except (RuntimeError, ValueError) as err:
        print(f"error initializing i2c: {err}")

    battery_monitor = None
    if BATTERY_VOLTAGE_PIN:
        battery_in = AnalogIn(BATTERY_VOLTAGE_PIN)
        battery_monitor = BatteryMonitor(battery_in)

    i2c_battery_monitor = None
    if BATTERY_I2C:
        try:
            i2c = board.I2C()
            lc709203f = LC709203F(board.I2C(), address=BATTERY_I2C)
            i2c_battery_monitor = I2CBatteryMonitor(lc709203f)
        except (RuntimeError, ValueError, OSError) as err:
            print(f"error initializing i2c: {err}")

    if co2_monitor:
        co2_task = asyncio.create_task(co2_monitor.fetch())
        tasks.append(co2_task)

    if battery_monitor:
        battery_task = asyncio.create_task(battery_monitor.fetch())
        tasks.append(battery_task)

    if i2c_battery_monitor:
        i2c_battery_task = asyncio.create_task(i2c_battery_monitor.fetch())
        tasks.append(i2c_battery_task)

    await asyncio.gather(*tasks)

    # update display
    update_display(co2_monitor, battery_monitor, i2c_battery_monitor)

    shutdown()
    # Does not return, so we never get here.


try:
    asyncio.run(main())

except Exception as e:
    print(f"Error: {e}")
    pixel.fill((255, 0, 0))
    pixel.brightness = 0.1
    raise
