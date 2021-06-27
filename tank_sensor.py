import smbus
import os, sys, traceback
import time
from time import sleep
from datetime import datetime
from filelock import Timeout, FileLock
import configparser
from os import path
import logging.handlers



THIS_SENSOR_NAME="tank_level"
LOG_FOLDER= os.path.abspath('config_and_log') + "/"
THIS_SENSOR_STATUS_FILE = LOG_FOLDER + "tank.st"
THIS_SENSOR_LOG_FILE =  f"{LOG_FOLDER }tank_sensor_week{datetime.datetime.today().isocalendar()[1]}.log"

THIS_SENSOR_SAMPLING = 10



###### LOG FILE SETTING WITH FILE ROTATION
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)
#handler = logging.handlers.RotatingFileHandler(THIS_SENSOR_LOG_FILE, maxBytes=10 *1024*1024, backupCount=1)
handler = logging.FileHandler(THIS_SENSOR_LOG_FILE, mode='a')
my_logger.addHandler(handler)
logging.getLogger().addHandler(logging.StreamHandler())

#my_logger=None

def print(string):
    my_logger.info(string)




##this communicate with micropico at best can do 100k IC2 while RPI runs at 400k
##sudo nano /boot/config.txt and lower very much the speed
##dtparam=i2c_arm=on,i2c_arm_baudrate=10000


config = configparser.ConfigParser()
config['sensor_name'] = {'value' : THIS_SENSOR_NAME , 'type' : 'string'}
config['status']      = {'value' : 'online' , 'type' : 'string'}
config['message']     = {'value' : '' , 'type' : 'string'}
config['frequency']   = {'value' : str(THIS_SENSOR_SAMPLING) , 'type' : 'int', 'unit' :'sec'}
config['level']       = {'value' : '0' , 'type' : 'int' , 'unit' : 'cm'}



# I2C channel 1 is connected to the GPIO pins
IC2CHANNEL = 1

#  MCP4725 defaults to address 0x60
ADDRESS = 0x8
STATUS_REG   = 0x21
MEASURE_REG  = 0x02
MEASURE_VOLT = 0x03
RESET_REG    = 0x04
LVL_ADJ_REG  = 0x05


# Write out I2C command: address, reg_write_dac, msg[0], msg[1]
def reset():
    bus.write_i2c_block_data(ADDRESS, RESET_REG, [0x01])

def adj_level( value):
    bus.write_i2c_block_data(ADDRESS, LVL_ADJ_REG, [value])

def get_status():
    return bus.read_i2c_block_data(ADDRESS, STATUS_REG, 1)

def get_level():
    return bus.read_i2c_block_data(ADDRESS, MEASURE_REG, 3)


status =''
message =''
water_level = 0

def update_status_file():
    config['status']['value'] =status.lower()
    config['message']['value'] =message.lower()
    config['level']['value'] = str(water_level)
    __folder , __name = os.path.split(THIS_SENSOR_STATUS_FILE)
    lock = FileLock('{folder}/.{name}.lock'.format(folder=__folder , name=__name))

    try:
        with lock.acquire(timeout=1):
            with open(THIS_SENSOR_STATUS_FILE, 'w') as file:
                config.write(file)
    except Timeout:
        print("SENSOR " + THIS_SENSOR_NAME + " :Another application currently holds the lock, try saving file later")



#adj_level(215)
#reset()
#val = bus.read_i2c_block_data(ADDRESS, LVL_ADJ_REG, 1)
counter = 0
issue_count = 0
data = [ 0, 0 , 0]
data_old = [ 0, 0 , 0]
status = "offline"
status_detail = ""
water_level   = 0
try:
    #handler.doRollover()
    dateTimeObj = datetime.now()
    print( dateTimeObj.strftime('%D  %H:%M:%S') + ": Program Start on")
    # Initialize I2C (SMBus)
    bus = smbus.SMBus(IC2CHANNEL)
    # reset
    reset()
    sleep(3)
    while True:
        dateTimeObj = datetime.now()
        data = get_level()
        water_level = data[2]
        status ="online"
        message = ""
        if data[0] == 1:
            if data[1] == 0:
                if data_old[1] != data[1]:
                    print(dateTimeObj.strftime('%D  %H:%M:%S') + ": SENSOR UNCONNECTED")
                    data_old[1] = data[1]
                message ="Issue with sensor, hardware unconnected"
            else:
                if data_old[2] != data[2]:
                    print(dateTimeObj.strftime('%D  %H:%M:%S') + ": Tank level: %s cm"% data[2])
                    data_old[2] = data[2]
                counter = counter + 1
                if (counter > 10):    ## if we got had to reset but able to do 10 read then we do not need to raise any issue
                    issue_count = 0
        else:
            if (issue_count > 2):
                if issue_count ==3:
                    print(dateTimeObj.strftime('%D  %H:%M:%S') + ": Issue with sensor, need user attention")
                    issue_count = issue_count + 1
                message ="Issue with sensor, hardware need user attention"
            else:
                print(dateTimeObj.strftime('%D  %H:%M:%S') + ": Issue with sensor, trying (%s)to reset" %issue_count)
                sleep(3)
                reset()
                issue_count = issue_count + 1
                counter =0
        update_status_file()
        sleep(THIS_SENSOR_SAMPLING )

except KeyboardInterrupt:
    print("User KeyboardInterrupt")
    status ="OFFLINE"
    message ="User exit"
    update_status_file()

except OSError:
    print("I2C failed")
    print("-"*60)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for item in traceback.format_exc().splitlines():
        print(item)
    print("-"*60)
    status ="OFFLINE"
    message ="ERROR OSError I2C"
    update_status_file()

except:
    print("Exception in user code:")
    print("-"*60)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for item in traceback.format_exc().splitlines():
        print(item)
    print("-"*60)

    status ="OFFLINE"
    message ="Unexpected exit"
    update_status_file()
finally:
    dateTimeObj = datetime.now()
    print(dateTimeObj.strftime('%D  %H:%M:%S') +": Program Exit")
    sys.exit(-1)
