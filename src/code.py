"""
Air quality monitor
"""
import time

import alarm # pylint: disable=import-error
import board
import adafruit_scd4x

DEEP_SLEEP_SECONDS = 20
WAIT_FOR_DATA_READY_SECONDS = 1
WAIT_FOR_MEASUREMENTS_TRIES = 60

print("Starting...")

i2c = board.I2C()
scd4x = adafruit_scd4x.SCD4X(i2c)
scd4x.self_calibration_enabled = False
#print("Serial number:", [hex(i) for i in scd4x.serial_number])

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

def deep_sleep(seconds):
    """
    set up a wake up alarm and go to deep sleep
    """
    # Create a an alarm that will trigger 20 seconds from now.
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + seconds)
    # Exit the program, and then deep sleep until the alarm wakes us.
    print(f"Going to sleep for {seconds} seconds...")
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)

scd4x.start_periodic_measurement()
print("Waiting for first measurement....")

get_measurement()

scd4x.stop_periodic_measurement()

deep_sleep(DEEP_SLEEP_SECONDS)
# Does not return, so we never get here.
