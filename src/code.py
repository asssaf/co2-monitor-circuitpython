"""
Air quality monitor
"""
import time
import board
import adafruit_scd4x

i2c = board.I2C()
scd4x = adafruit_scd4x.SCD4X(i2c)
print("Serial number:", [hex(i) for i in scd4x.serial_number])

scd4x.start_periodic_measurement()
print("Waiting for first measurement....")

for i in range(10):
    if scd4x.data_ready:
        print(f"CO2: {scd4x.CO2} ppm")
        print(f"Temperature: {scd4x.temperature:0.1f} *C")
        print(f"Humidity: {scd4x.relative_humidity:0.1f} %")
        print()
    time.sleep(1)
