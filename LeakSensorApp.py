import RPi.GPIO  
import package.sensor_class as sensor_class


import os, sys, traceback, time
from datetime import datetime

GLOBAL_DEBUG_CONFIG_DICT = {}
def printexception():
    print("-"*60)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for item in traceback.format_exc().splitlines():
        print(item)
    print("-"*60)





try:
    #LOG_FOLDER= os.path.abspath('config_and_log') + "/"
    LOG_FOLDER = '/home/pi/config_and_log/'
    if not os.path.isdir(LOG_FOLDER):
        os.mkdir(LOG_FOLDER)

    THIS_SENSOR_STATUS_FILE = LOG_FOLDER + "LeakSensor.st"
    THIS_SENSOR_LOG_FILE = LOG_FOLDER + "LeakSensor.log"
    THIS_SENSOR_DATA_FILE = LOG_FOLDER + "LeakSensor.json"
    THIS_SENSOR_CONFIG = LOG_FOLDER + "LeakSensor.cfg"
    THIS_SENSOR_SAMPLING = 2

    sensor= sensor_class.sensor_class(config_file=THIS_SENSOR_CONFIG , log_file=THIS_SENSOR_LOG_FILE, status_file=THIS_SENSOR_STATUS_FILE, data_file=THIS_SENSOR_DATA_FILE, sampling=THIS_SENSOR_SAMPLING, name="LeakSensor")
    retry_count = 0
    max_trial_count = 2
    while True:
        try:
            if retry_count >= max_trial_count :
                print("\n\nWaiting for User feedback")
                while True:
                    time.sleep(10)
            elif retry_count > 0 and retry_count <  max_trial_count :
                print('\n\nRESTART PROGRAM')
                print('Powerdown first')
                sensor.power_down(debug=True)

                
            print('STARTING')
            sensor.update_settings()

            sensor.power_up(debug=False)

            if sensor.config.getvalue('continuity_test',    fallback=False):
                sensor.check_io_continuity(debug=sensor.config.getvalue('continuity_test_debug',    fallback=False))

           # sensor.set_LED_OFF()
            sensor.check_com_short()
            sensor.count_sensor(debug=False)
      
            while sensor.config.getvalue('manual_debug',    fallback=False):
                sensor.manual_debug(debug=False)

            while sensor.config.getvalue('check_for_leak',    fallback=True):
                sensor.check_all_nodes()

        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as exception:
            print(f'ERROR: EXPECTION RAISED: {str(exception)}')        
            if str(exception) == "SetioTimeout" or str(exception) == "count_sensors" :
                retry_count = retry_count + 1
            else:
                raise exception
                    





except KeyboardInterrupt:
        sensor.watchdog.stop()
        print('STATUS: KeyboardInterrupt')

except :
        print("Exception in user code:")
        printexception()
finally:
        print('cleanup and exit')
        sensor.power_down(debug=True)
        sensor.GPIO.cleanup()
        sensor.watchdog.stop()

        sys.exit(0)


