#from datetime import datetime, timedelta
import configparser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from filelock import Timeout, FileLock
from threading import Timer
import time
import sys , traceback
import threading
import time
import logging
from package.myclass import myobject
import re
import logging.handlers
import os, shutil
from os import path
import RPi.GPIO as GPIO
import stat
import datetime
from package.myclass import mysensor
import configparser

#LOG_FOLDER= os.path.abspath('config_and_log') + "/"
LOG_FOLDER = '/home/pi/config_and_log/'
INSTALL_FOLDER = '/home/pi/bin'

if not os.path.isdir(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)

IRRIGATIONCONTROLLER_CONFIG_FILE =  LOG_FOLDER+ 'IrrigationController.ini'
if not os.path.isfile(IRRIGATIONCONTROLLER_CONFIG_FILE):
    shutil.copyfile(f"{INSTALL_FOLDER}/default_init/Irrigationapp.ini", IRRIGATIONCONTROLLER_CONFIG_FILE)

SCHEDULER_CONFIG_FILE =  LOG_FOLDER+ 'scheduler.ini'
if not os.path.isfile(SCHEDULER_CONFIG_FILE):
    shutil.copyfile(f"{INSTALL_FOLDER}/default_init/scheduler.ini", SCHEDULER_CONFIG_FILE)
appconfig = configparser.ConfigParser()
appconfig.read( SCHEDULER_CONFIG_FILE ) 


THIS_SENSOR_NAME="scheduler"
THIS_SENSOR_STATUS_FILE = LOG_FOLDER + "scheduler.st"
THIS_SENSOR_LOG_FILE =  f"{LOG_FOLDER }scheduler_week{datetime.datetime.today().isocalendar()[1]}.log"
THIS_SENSOR_SAMPLING = 15
TANKS_STATUS_FILE =  LOG_FOLDER+ 'tank.st'


###### LOG FILE SETTING WITH FILE ROTATION

my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)
#handler = logging.handlers.RotatingFileHandler(THIS_SENSOR_LOG_FILE, maxBytes=10 *1024*1024, backupCount=7)
handler = logging.FileHandler(THIS_SENSOR_LOG_FILE, mode='a')
my_logger.addHandler(handler)

def myprint(string):
    current_time = datetime.datetime.now()
    print (f'{current_time.strftime("%a %b%d %2H:%2M:%2S :")} {string}')
    my_logger.info(f'{current_time.strftime("%a %b%d %2H:%2M:%2S :")} {string}')

def update_status_file():
    global timer_dict

    config['status']['value'] =status.lower()


    __folder , __name = os.path.split(THIS_SENSOR_STATUS_FILE)
    lock = FileLock('{folder}/.{name}.lock'.format(folder=__folder , name=__name))

    try:
        with lock.acquire(timeout=1):
            with open(THIS_SENSOR_STATUS_FILE, 'w') as file:
                config.write(file)
    except Timeout:
        print("SENSOR " + THIS_SENSOR_NAME + " :Another application currently holds the lock, try saving file later")

    ##check if thread running if so, kill it and restart
    if 'maintimer' in timer_dict:
        if timer_dict['maintimer'].isAlive():
            timer_dict['maintimer'].cancel()
    timer_dict['maintimer'] = Timer(THIS_SENSOR_SAMPLING , update_status_file)
    timer_dict['maintimer'].setName('maintimer')
    timer_dict['maintimer'].start()

def TurnRelay (value, pumpid=-1 , all=False):
  #  print(F"TurnRelay value:{value} pumpid:{pumpid} all:{all}")
    if value == 'ON':
        gpio_val = GPIO.LOW
    elif value == 'OFF':
        gpio_val = GPIO.HIGH
    else:
        myprint(f"Error GPIO: invalid parameter value : {value}. Valid data is 'ON' or 'OFF'")
        return
    ## don't do anything if we are not changin the GPIO values, so we do not update file status
    if pumpid != -1 and pumpid >= len(valve_GPIO):
        myprint(f"Error: pump_id ({pumpid}) is out of bound [0:{len(valve_GPIO)}]")
        return

    if pumpid != -1 :
        GPIO.setup(valve_GPIO[pumpid], GPIO.OUT)
        if GPIO.input(valve_GPIO[pumpid]) == gpio_val:
            return

    GPIO.setup(pump_GPIO, GPIO.OUT)
    if all:
        for valveid in range (len(valve_GPIO)-1):
            GPIO.setup(valve_GPIO[valveid], GPIO.OUT)
            GPIO.output(valve_GPIO[valveid], gpio_val)
            config[f'timer{valveid + 1}']['value'] = value
        GPIO.output(pump_GPIO, gpio_val)
        config[f'pump']['value'] = value
        update_status_file()
        return

    if pumpid != -1:
        if pumpid > len(valve_GPIO) -1  or pumpid < 0:
            myprint(f"Error GPIO: pumpid  {pumpid} is outside range [0: {len(valve_GPIO) -1  }]")
            return
        GPIO.setup(valve_GPIO[pumpid], GPIO.OUT)
        GPIO.output(valve_GPIO[pumpid], gpio_val)
        config[f'timer{pumpid + 1}']['value'] =value

    ## turn Pump On if this is VALVE ON
    if value == 'ON':
        GPIO.output(pump_GPIO, gpio_val)
        config[f'pump']['value'] = value
        update_status_file()
        return
    ## turn Pump OFF is all Valve are OFF
    for valveid in range (len(valve_GPIO)-1):
        if GPIO.input(valve_GPIO[valveid]) != gpio_val :
            myprint(f" valve {valveid} is still ON, leave Pump ON")
            update_status_file()
            return
    GPIO.output(pump_GPIO, gpio_val)
    config[f'pump']['value'] = value
    update_status_file()



valve_GPIO = [40, 38]
valve_GPIO = []
for valve in range(1, 10, 1):
    gpio =  appconfig['GPIO'].getint(f"VALVE_{valve}", 999)
    if gpio ==999 and valve == 1:
        myprint(f"Error: No GPIO set for Valve (VALVE_{valve}), at least one is required {SCHEDULER_CONFIG_FILE} ")
    if gpio == 999:
        break
    valve_GPIO.append( gpio )

pump_GPIO = 37
pump_GPIO = appconfig['GPIO'].getint('PUMP', 0)
debug = appconfig['DEBUG'].getboolean(f"verbose", False)


config = configparser.ConfigParser()
config['sensor_name'] = {'value' : THIS_SENSOR_NAME , 'type' : 'string'}
config['status']      = {'value' : 'online' , 'type' : 'string'}
config['message']     = {'value' : '' , 'type' : 'string'}
config['frequency']   = {'value' : str(THIS_SENSOR_SAMPLING) , 'type' : 'int', 'unit' :'sec'}

#    timer_list = ['timer1', 'timer2']
timer_list = []
for idx in range(1, len(valve_GPIO)+1 , 1):
    timer_list.append(f'timer{idx}')
    config[f'timer{idx}']       = {'value' : 'off' , 'type' : 'str'}
    config[f'timer{idx}_override']       = {'value' : 'False' , 'type' : 'boolean'}
config['pump']       = {'value' : 'off' , 'type' : 'str'}




status ='online'
message=''

last_modificationTime = None
special_param = {}
timer_param= {}
for timer_name in timer_list:
    timer_param[timer_name] = {}
timer_param[timer_name]['updated'] = False

IrrigationControllerAppConfig = myobject(file =IRRIGATIONCONTROLLER_CONFIG_FILE, debug=False ,allowfieldexpension=False, logger=my_logger)
@IrrigationControllerAppConfig.changed.register
def IrrigationControllerAppConfig_changed(obj=None, key=None, value=None, check_timer_name=None):
    global last_modificationTime , special_param, timer_param
    config['message']['value'] = ""

    fileStatsObj = os.stat ( IRRIGATIONCONTROLLER_CONFIG_FILE )
    modificationTime = time.ctime ( fileStatsObj [ stat.ST_MTIME ] )
    if modificationTime == last_modificationTime:
        return
    if debug:
        myprint(f"IrrigationControllerAppConfig_changed:\n{IRRIGATIONCONTROLLER_CONFIG_FILE}\n mofidied @ {modificationTime}")
    last_modificationTime = modificationTime

    for parameter_id in [ 'Max_Level' , 'Min_Level','overflow_enabled']:
        value = IrrigationControllerAppConfig.get_parameterid_value(parameter_id)[0]
        if parameter_id not in special_param or special_param[parameter_id] != value:
            special_param[parameter_id] = value

    for timer_name in timer_list:
        parameter_id = f"{timer_name}_mode_select"
        value =  IrrigationControllerAppConfig.get_parameterid_choices(parameter_id, with_indexes=False)[IrrigationControllerAppConfig.get_parameterid_value(parameter_id)[0] ]
        if parameter_id not in special_param or special_param[parameter_id] != value:
            special_param[parameter_id] = value
        value = IrrigationControllerAppConfig.get_parameterid_choices_value(parameter_id)[IrrigationControllerAppConfig.get_parameterid_value(parameter_id)[0]]
        special_param[f"{parameter_id}_time"] = value
        special_param[f"{timer_name}_group"] = IrrigationControllerAppConfig.get_parameterid_group(parameter_id)
    for timer_name in timer_list:
        x = 1000000
        timer_param[timer_name]['pump_id'] =        int( re.sub(r'timer', '', timer_name)) -1


        timer_param[timer_name]['updated'] = False

        if timer_name not in timer_param:
            timer_param[timer_name] = {}
        for parameter_id in ['enabled', 'ON_HH', 'ON_MM', 'ON_duration' , 'repeat_monday' , 'repeat_tuesday',  'repeat_wednesday', 'repeat_thursday', 'repeat_friday', 'repeat_saturday', 'repeat_sunday'] :
            parameter_name = f'{timer_name}_{parameter_id}'
            if not IrrigationControllerAppConfig.parameterid_exists(parameter_name):
                myprint(f"Warning IrrigationControllerAppConfig: {parameter_name} missing parameter for {timer_name}.")
            else:
                new_value = IrrigationControllerAppConfig.get_parameterid_value(parameter_name)
                #print(new_value)
                #print(len(new_value))
                if parameter_id not in timer_param[timer_name] or timer_param[timer_name][parameter_id] != new_value:
                    timer_param[timer_name][parameter_id] =new_value
                    x = min ( x, len(new_value) )
                    timer_param[timer_name]['updated'] = True
        if x != 1000000:
            timer_param[timer_name]['group_count'] = x
        timer_param[timer_name]['OFF_HH'] = timer_param[timer_name]['ON_HH'].copy()
        timer_param[timer_name]['OFF_MM'] = timer_param[timer_name]['ON_MM'].copy()
        #print(f"timer-pre: {timer_name}\n {timer_param[timer_name]}")
        timer_param[timer_name]['on_time'] = []
        timer_param[timer_name]['off_time'] = []
        for idx in range (timer_param[timer_name]['group_count'] ) :
            #print(f"test {idx}")
            #print (timer_param[timer_name]['OFF_MM'][idx])
            #print (timer_param[timer_name]['ON_duration'][idx])
            timer_param[timer_name]['OFF_MM'][idx] =   timer_param[timer_name]['OFF_MM'][idx] + timer_param[timer_name]['ON_duration'][idx]

            #print (timer_param[timer_name]['OFF_MM'][idx])
            if timer_param[timer_name]['OFF_MM'][idx] > 59 :
                timer_param[timer_name]['OFF_MM'][idx] = timer_param[timer_name]['OFF_MM'][idx] - 60
                timer_param[timer_name]['OFF_HH'][idx] = timer_param[timer_name]['OFF_MM'][idx] + 1
                if timer_param[timer_name]['OFF_HH'][idx] > 23:
                    timer_param[timer_name]['OFF_HH'][idx] = 0

            #print (timer_param[timer_name]['OFF_MM'][idx])

            timer_param[timer_name]['on_time'].append(  datetime.time( timer_param[timer_name]['ON_HH'][idx], timer_param[timer_name]['ON_MM'][idx] ) )
            timer_param[timer_name]['off_time'].append( datetime.time( timer_param[timer_name]['ON_HH'][idx], timer_param[timer_name]['OFF_MM'][idx] ) )





    for timer_name in timer_list:
        if timer_param[timer_name]['updated']:
            group_name = special_param[timer_name+"_group"]
            if debug:
                myprint(f"timer-post: {timer_name} ({group_name})\n {timer_param[timer_name]}")
            get_next_on_time(timer_name)

def get_next_on_time( timer_name):
    group_name = special_param[timer_name+"_group"]
    current_dayoftheweek = datetime.datetime.now().weekday()
    dayoftheweek = current_dayoftheweek
    weekday_list = [ 'monday' , 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for each_day_of_the_week  in range(7):
        dayoftheweek += 1
        if dayoftheweek == 7:
            dayoftheweek = 0
        if dayoftheweek == current_dayoftheweek:
            myprint(f"Next irrigation for {timer_name} ({group_name}) never , timer not enabled")
            return

        for idx , on_time in enumerate( timer_param[timer_name]['on_time'] ):
            #print(f"repeat_{ weekday_list[dayoftheweek] } {idx}" )
            if timer_param[timer_name][ f"repeat_{ weekday_list[dayoftheweek] }" ][idx] and timer_param[timer_name]['enabled'][idx]:
                myprint(f"Next irrigation for {timer_name} ({group_name}): {weekday_list[dayoftheweek]} @ {on_time}")
                return


def check_time( timer_name , idx):
    if not timer_param[timer_name]['enabled'][idx]:
        if debug:
            myprint(f"{timer_name} ({idx}) is not enabled")
        return False
    dayoftheweek = datetime.datetime.now().weekday()
    repeatday_list = [ 'repeat_monday' , 'repeat_tuesday', 'repeat_wednesday', 'repeat_thursday', 'repeat_friday', 'repeat_saturday', 'repeat_sunday']

    if debug:
        myprint (f"idx = {idx} day of the week {dayoftheweek} : {repeatday_list[dayoftheweek]}  =  {timer_param[timer_name][ repeatday_list[dayoftheweek] ][idx]}")

    if not timer_param[timer_name][ repeatday_list[dayoftheweek] ][idx]:
        return False

    current_time = datetime.datetime.now().time()
    on_time  = timer_param[timer_name]['on_time'][idx]
    off_time = timer_param[timer_name]['off_time'][idx]
    if on_time > off_time:
        if current_time > on_time or current_time < off_time:
            return True
    elif on_time < off_time:
        if current_time > on_time and current_time < off_time:
            return True
    elif current_time == on_time:
        return True
    return False

try:
    OVERFLOW = False
    Min_Level = -1000000000
    Max_Level = 100000000
    tank_sensor_alive = False
    ## reach time we start this script we do a roll over
    #handler.doRollover()

    myprint(f"Program Started.")

    timer_dict ={}
    update_status_file()
    GPIO.setmode(GPIO.BOARD)
    GPIO.cleanup()

    TurnRelay('OFF', all=True)
    IrrigationControllerAppConfig_changed()

    main_tank =mysensor(file =TANKS_STATUS_FILE, field_list=['level'] ,logger=my_logger)
    # @main_tank.changed.register
    # def main_tank_changed(obj, key, value):
    #     #print('Key %s changed to %s' % (key, value))
    #     print (main_tank.field_status['sensor_name'])
    #     print (main_tank.field_status['level'])
    #     print (main_tank.field_status['status'])


    mode_save ={}
    print_once= {}
    for timer_name in timer_list:
        mode_save[f"{timer_name}_mode_select"] = None
        print_once[timer_name] = None
    WATER_TOO_LOW = False
    print_once['tank_status'] = None

    while True:
        current_time = datetime.datetime.now().time()
        ### if water leve enabled and sensor alive proceed based on reading.
        if special_param['overflow_enabled']:
            if "ONLINE" in main_tank.field_status['status'].upper():
                if main_tank.field_status['level'] < special_param['Min_Level']:
                    WATER_TOO_LOW = True
                    if print_once['tank_status'] != "LOW":
                        print_once['tank_status'] = "LOW"
                        myprint(f"Warning: Water tank is too low {main_tank.field_status['level']}  , irrigation skipped")
                elif main_tank.field_status['level'] >= special_param['Min_Level'] + 3:
                    WATER_TOO_LOW = False
                    if print_once['tank_status'] != "OK":
                        print_once['tank_status'] = "OK"
                        myprint(f"Warning: Water tank above min level {main_tank.field_status['level']} , irrigation will proceed per schedule enabled")
            else:
                WATER_TOO_LOW = False
                if print_once['tank_status'] != "OFFLINE":
                    print_once['tank_status'] = "OFFLINE"
                    myprint(f"water sensor offline , skipping level sensor , irrigation will proceed per schedule enabled")
        else:
            WATER_TOO_LOW = False


        ### turn on/off based on mode and schedule settings
        for timer_name in timer_list:
            mode_select = f"{timer_name}_mode_select"

            if special_param[mode_select] != mode_save[mode_select]:
                group_name = special_param[timer_name+"_group"]
                myprint(f"Mode changed: {group_name} ({timer_name}) {mode_save[mode_select]} =>{special_param[mode_select]}")
                mode_save[mode_select]=special_param[mode_select]

            if "OFF" in special_param[mode_select].upper() or WATER_TOO_LOW:
                if print_once[timer_name] != "OFF":
                    force_time = special_param[mode_select+"_time"]
                    group_name = special_param[timer_name+"_group"]
                    myprint(f"Force {group_name} ({timer_name}) OFF for {force_time} sec")
                    TurnRelay('OFF' , pumpid=timer_param[timer_name]['pump_id'])
                    get_next_on_time(timer_name)
                    print_once[timer_name] = "OFF"
                else:
                    TurnRelay('OFF' , pumpid=timer_param[timer_name]['pump_id'])


            elif "AUTO" in special_param[mode_select].upper():
                TurnON = False
                for idx in range (timer_param[timer_name]['group_count']):
                    res = check_time( timer_name , idx )
                    TurnON = TurnON or res
                if TurnON:
                    value = "ON"
                else:
                    value = "OFF"

                ## print stuff once
                if print_once[timer_name] != value:
                    group_name = special_param[timer_name+"_group"]
                    myprint(f"Turn {group_name} ({timer_name}) {value}")
                    print_once[timer_name] = value
                    TurnRelay(value , pumpid=timer_param[timer_name]['pump_id'])
                    if value == 'OFF':
                        get_next_on_time(timer_name)
                else:
                    TurnRelay(value , pumpid=timer_param[timer_name]['pump_id'])


            elif "ON" in special_param[mode_select].upper():
                if print_once[timer_name] != "ON":
                    force_time = special_param[mode_select+"_time"]
                    group_name = special_param[timer_name+"_group"]
                    myprint(f"Force {group_name} ({timer_name}) ON for {force_time} sec")
                    print_once[timer_name] = "ON"
                TurnRelay('ON' , pumpid=timer_param[timer_name]['pump_id'])
            else:
                if print_once[timer_name] != "OUPS":
                    group_name = special_param[timer_name+"_group"]
                    myprint(f"Error: Something wrong {group_name} ({timer_name}) mode is neither ON/OFF P:{special_param[mode_select]}")
                    print_once[timer_name] = "OUPS"

        time.sleep(1)



except KeyboardInterrupt:
    myprint("User KeyboardInterrupt.")
    status ="offline"
    config['message']['value'] ="User exit"
    update_status_file()

except OSError:
    myprint("OSError")
    myprint("-"*60)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for item in traceback.format_exc().splitlines():
        myprint(item)
    myprint("-"*60)
    status ="offline"
    config['message']['value'] ="ERROR OSError"
    update_status_file()

except:
    myprint("Exception in user code:")
    myprint("-"*60)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for item in traceback.format_exc().splitlines():
        myprint(item)
    myprint("-"*60)
    status ="offline"
    config['message']['value'] ="Unexpected exit"
    update_status_file()

finally:
    myprint("Stopping all threads")
    print(f"\t{timer_dict.keys()}")

    for timer in list(timer_dict):
        timer_dict[timer].cancel()


    myprint("Turn all Pumps off.")

    TurnRelay("OFF", all=True)
    GPIO.cleanup()
    myprint("Program exit.")
    sys.exit(-1)
