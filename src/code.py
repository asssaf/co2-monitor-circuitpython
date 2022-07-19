"""
Air quality monitor
"""
import time

from adafruit_display_text import label
import adafruit_il0373
from analogio import AnalogIn
import alarm # pylint: disable=import-error
import adafruit_scd4x
import board
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

print("Starting...")

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.1
pixel.fill((0, 255, 0))

i2c = board.I2C()
scd4x = adafruit_scd4x.SCD4X(i2c)
scd4x.self_calibration_enabled = False

battery_in = AnalogIn(board.A0)


def get_measurement():
    """
    get a single measurement
    """
    for _ in range(WAIT_FOR_MEASUREMENTS_TRIES):
        if scd4x.data_ready:
            print(f"CO2: {scd4x.CO2} ppm")
            print(f"Temperature: {scd4x.temperature:0.1f} *C")
            print(f"Humidity: {scd4x.relative_humidity:0.1f} %")
            print()
            return
        time.sleep(WAIT_FOR_DATA_READY_SECONDS)


def get_battery_voltage():
    """
    get the battery voltage using an analog pin
    """
    battery_voltage = 3.3 * battery_in.value / 65536 * 2
    return battery_voltage


def deep_sleep(seconds):
    """
    set up a wake up alarm and go to deep sleep
    """
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
def main():
    """
    Main entry point
    """
    if supervisor.runtime.usb_connected and not alarm.wake_alarm:
        print("Woke up without an alarm")
        # go to sleep to avoid refreshing the display too soon
        shutdown()

    #print("Serial number:", [hex(i) for i in scd4x.serial_number])

    scd4x.start_periodic_measurement()
    print("Waiting for first measurement....")

    get_measurement()

    scd4x.stop_periodic_measurement()

    # update display
    top_group = displayio.Group()

    background_color = 0xFFFFFF
    background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    palette = displayio.Palette(1)
    palette[0] = background_color
    background_tile = displayio.TileGrid(background_bitmap, pixel_shader=palette)

    co2_text = f"{scd4x.CO2}"
    font = terminalio.FONT
    color = 0x000000

    co2_label = label.Label(font, text=co2_text, color=color, scale=3)
    co2_label.anchor_point = (0.5, 0.5)
    co2_label.anchored_position = (DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2)

    battery_voltage = get_battery_voltage()
    battery_voltage_text = f"{battery_voltage:0.2f} V"
    print(f"Battery voltage: {battery_voltage_text}")
    battery_label = label.Label(font, text=battery_voltage_text, color=color, scale=1)
    battery_label.anchor_point = (0.0, 1.0)
    battery_label.anchored_position = (10, DISPLAY_HEIGHT -10)

    top_group.append(background_tile)
    top_group.append(co2_label)
    top_group.append(battery_label)

    if DISPLAY_ENABLED:
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

        displayio.release_displays()

    shutdown()
    # Does not return, so we never get here.


try:
    main()

except Exception as e:
    print(f"Error: {e}")
    pixel.fill((255, 0, 0))
    pixel.brightness = 0.1
    raise
