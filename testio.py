import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)
GPIO.cleanup()
#io=40 40 is dead
io= 37
io= 38

try:
    while True:
        GPIO.setup(io, GPIO.OUT)
        GPIO.output(io, GPIO.LOW)
        time.sleep(1)
        GPIO.output(io, GPIO.HIGH)
        time.sleep(1)
except:
    GPIO.output(io, GPIO.LOW)
    GPIO.cleanup()
