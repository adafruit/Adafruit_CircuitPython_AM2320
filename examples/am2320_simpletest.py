import time
import board
import busio
import adafruit_am2320

# can also use board.SDA and board.SCL for neater looking code!
i2c = busio.I2C(board.D2, board.D0)
am = adafruit_am2320.AM2320(i2c)


while True:
    try:
        print("Temperature: ", am.temperature)
        print("Humidity: ", am.relative_humidity)
    except OSError:
        # These sensors are a bit flakey, its ok if the readings fail
        pass
    except RuntimeError:
        pass
    time.sleep(2)
