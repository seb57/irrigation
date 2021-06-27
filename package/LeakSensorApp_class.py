import RPi.GPIO  
import threading
import time
import os.path
from os import path
from datetime import datetime
import json
import configparser
from filelock import Timeout, FileLock
from threading import Timer
import re
import ast
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta

import stat
class myIO():

    def __init__(self, name, channel , direction, default_value=RPi.GPIO.LOW, driver=None, ack=None, debounce_ms=10, timeout_ms=0):
        self.name = name
        self.channel = channel
        self.direction = direction
        self.default_value = default_value
        self.ack  = ack
        self.driver  = driver
        self.timeout_ms  = timeout_ms
        self.debounce_ms  = debounce_ms
        self.enable_rising_edge_detect = False
        self.enable_falling_edge_detect = False
        self.rising_edge_detected  = False
        self.falling_edge_detected = False   

class IOS():
    name = {}
    debug_config = {'edge_detect_callback':False}
    timeout_toggle = False
    def edge_detect_callback(self, channel):
        if self.debug_config['edge_detect_callback']:
            print(f'Find edge change on {channel}  {RPi.GPIO.input(channel)}')
        for name in self.name:
            if self.name[name].channel == channel:
                if RPi.GPIO.input(channel) == RPi.GPIO.HIGH:
                    self.name[name].rising_edge_detected = True
                    if self.debug_config['edge_detect_callback']:
                        print(f'name:{name} {self.name[name].channel} rising_edge_detected {self.name[name].rising_edge_detected}')
                    break
                else:
                    self.name[name].falling_edge_detected = True
                    if self.debug_config['edge_detect_callback']:
                        print(f'name:{name} {self.name[name].channel} falling_edge_detected {self.name[name].falling_edge_detected}')
                    break

    
    def add(self, name, channel, direction ,default_value=RPi.GPIO.LOW, driver=None, ack_name=None, debounce_ms=10 , timeout_ms=0):
        if ack_name != None:
            if ack_name in self.name:
                self.name[name]= myIO(name=name, channel=channel, direction=direction, default_value=default_value, ack=self.name[ack_name] , debounce_ms=debounce_ms , timeout_ms=timeout_ms)

            else:
                print(f'Error: {ack_name} referenced but not defined yet')
            return

        self.name[name]= myIO(name=name, channel=channel, direction=direction, default_value=default_value, driver=driver, ack=None  , debounce_ms=debounce_ms , timeout_ms=timeout_ms)


    def setup(self, debug=False):
        RPi.GPIO.setmode(RPi.GPIO.BOARD)
        for name, ioobject in self.name.items():
            if ioobject.direction ==  RPi.GPIO.OUT:
                print(f'INFO: define io {ioobject.name} ({ioobject.channel}) as output, value = {ioobject.default_value}')
                RPi.GPIO.setup(ioobject.channel, ioobject.direction, initial=ioobject.default_value)
            else:
                print(f'INFO: define io {ioobject.name} ({ioobject.channel}) as input')
                RPi.GPIO.setup(ioobject.channel, ioobject.direction)
                
                self.name[name].enable_rising_edge_detect  = True
                self.name[name].enable_falling_edge_detect = True
                self.name[name].rising_edge_detected  = False
                self.name[name].falling_edge_detected = False
                RPi.GPIO.add_event_detect(ioobject.channel, RPi.GPIO.BOTH, callback=self.edge_detect_callback, bouncetime=self.name[name].debounce_ms)

    def cleanup(self):
        RPi.GPIO.setmode(RPi.GPIO.BOARD)
        print(f'Turn all IO as input')
        RPi.GPIO.cleanup()

    def setio(self, name , val,  require_ack=True, debug=False, raise_timeout=True, force_edge_detect=None):
        if 'setio' in self.debug_config:
            debug = True

        if val not in [ 0, 1 ]:
            print(f'Error: trying to set inccorect value io \'{name}\' : {val}')
            raise ValueError
        if name not in self.name:
            print(f'Error: trying to set unknown io name \'{name}\' , must one  of { list(self.name.keys())}')
            raise ValueError

        if not require_ack:
            if debug:
                print(f'\nINFO: Set io {name} ({self.name[name].channel}) to {val}.')

            RPi.GPIO.output(self.name[name].channel, val)
            self.success = True
            return self.success

        if self.name[name].ack == None:
            print(f'Info: trying to set unknown io name \'{name}\' , has no ack pin')
            RPi.GPIO.output(self.name[name].channel, val)
            self.success = True
            return self.success

        if self.name[name].ack.name not in self.name:
            print(f'Error: ack io for name \'{name}\'  must one  of { list(self.name.keys())}')
            raise ValueError

        if debug:
            print(f'\nINFO: Set {name} io ({self.name[name].channel}) to {val}.  current value: {RPi.GPIO.input(self.name[name].channel)}  ack: {RPi.GPIO.input(self.name[name].ack.channel)}')
            print(f'\ttimeout = {self.name[name].ack.timeout_ms:3.2f} ms debounce time = {self.name[name].ack.debounce_ms:3.2f} ms')

        if RPi.GPIO.input(self.name[name].channel) == val and RPi.GPIO.input(self.name[name].ack.channel) != val:
            print(f'Error: Set {name} io ({self.name[name].channel}) to {val}.  current value: {RPi.GPIO.input(self.name[name].channel)}  ack: {RPi.GPIO.input(self.name[name].ack.channel)}')
            self.success = False
            return self.success

        if RPi.GPIO.input(self.name[name].channel) == val:
            self.success = True
            return self.success        
        #save current setting on edge
        enable_rising_edge_detect_save  = self.name[name].enable_rising_edge_detect
        enable_falling_edge_detect_save = self.name[name].enable_falling_edge_detect
        #set the edge we want to detect
        if val == 1:
            CHECK_EDGE = RPi.GPIO.RISING
            OUTPUT     = RPi.GPIO.HIGH
            self.name[name].enable_rising_edge_detect  = True
            self.name[name].enable_falling_edge_detect = False
        else :
            CHECK_EDGE = RPi.GPIO.FALLING
            OUTPUT     = RPi.GPIO.LOW
            self.name[name].enable_rising_edge_detect  = False
            self.name[name].enable_falling_edge_detect = True

        if force_edge_detect == RPi.GPIO.RISING:
            self.name[name].enable_rising_edge_detect  = True
            self.name[name].enable_falling_edge_detect = False
            CHECK_EDGE = force_edge_detect
        elif force_edge_detect == RPi.GPIO.FALLING:
            self.name[name].enable_rising_edge_detect  = False
            self.name[name].enable_falling_edge_detect = True
            CHECK_EDGE = force_edge_detect
        elif force_edge_detect == RPi.GPIO.BOTH:
            self.name[name].enable_rising_edge_detect  = True
            self.name[name].enable_falling_edge_detect = True
            CHECK_EDGE = force_edge_detect


        def timeout_callback():
            pass
        timer= threading.Timer( self.name[name].ack.timeout_ms / 1000, timeout_callback)
        self.name[name].ack.rising_edge_detected =False
        self.name[name].ack.falling_edge_detected =False
        self.response_time = [0 , 0]
        timeout = False
        while True:
                if self.response_time[val] == 0:
                    self.response_time[val] = time.time()
                    RPi.GPIO.output(self.name[name].channel, OUTPUT)
                    timer.start()
                if not timer.isAlive():
                    self.response_time[val] = ( time.time() - self.response_time[val]) * 1000
                    timeout = True
                    break
                if (self.name[self.name[name].ack.name].rising_edge_detected and CHECK_EDGE == RPi.GPIO.RISING) or (self.name[name].ack.falling_edge_detected and CHECK_EDGE == RPi.GPIO.FALLING):
                    self.response_time[val] = ( time.time() - self.response_time[val]) * 1000
                    break
                if RPi.GPIO.input(self.name[name].channel) == RPi.GPIO.input(self.name[name].ack.channel):
                    time.sleep(self.name[name].ack.debounce_ms /1000)
                    if RPi.GPIO.input(self.name[name].channel) == RPi.GPIO.input(self.name[name].ack.channel):
                        self.response_time[val] = ( time.time() - self.response_time[val]) * 1000
                        break

        timer.cancel()

        self.name[name].enable_rising_edge_detect  = enable_rising_edge_detect_save
        self.name[name].enable_falling_edge_detect = enable_falling_edge_detect_save
        if timeout : #and  RPi.GPIO.input(self.name[name].ack.channel) != RPi.GPIO.input(self.name[name].channel) :#or self.response_time[val] > self.name[name].ack.timeout_ms:
            print(f'Error: timeout ({self.name[name].ack.timeout_ms:3.2f} ms) : {name} is {RPi.GPIO.input(self.name[name].channel)} and {self.name[name].ack.name} is {RPi.GPIO.input(self.name[name].ack.channel)} after {self.response_time[val]:3.2f} ms both are expected to be {val}')
            print(f' enable DEBUG TIMEOUT TOGGLE for futher debug')
            if  self.timeout_toggle:
                print(f"toggling {name} (IO# {self.name[name].channel}), expect to also see that toggle on {self.name[name].ack.name} (IO# {self.name[name].ack.channel})")
            while  self.timeout_toggle:
                RPi.GPIO.output(self.name[name].channel, RPi.GPIO.HIGH)
                time.sleep(0.1)
                RPi.GPIO.output(self.name[name].channel, RPi.GPIO.LOW)
                time.sleep(0.1)
                raise_timeout =False

            if raise_timeout:
                raise Exception("SetioTimeout")
            self.success = False
            return self.success

        if debug:
            print(f' success {self.name[name].ack.name} set to {val} in {self.response_time[val]:3.2f} ms')

        self.success = True
        return self.success

    def test_io_speed(self, name, test_count=1, debug=False):
        success = True
        average =[0, 0]
        for count in range(test_count):
            for val in [1 , 0]:
                res  = self.setio(name, val ,debug=debug, require_ack=True, force_edge_detect=RPi.GPIO.BOTH)
                if not res:
                    debug = True
                    success = False
                average[val] += self.response_time[val]
        print(f'average 0->1 response time {average[0]/test_count:6.2f}ms')
        print(f'average 1->0 response time {average[1]/test_count:6.2f}ms')
        self.response_time = [average[0]/test_count , average[1]/test_count]
        self.success = success
        return self.success

class sensor_watchdog_class():

    config = configparser.ConfigParser()
    status = 'online'
    def __init__(self, status_file, sampling, name, data=None):
        self.sampling = sampling
        self.data=data
        self.status_file = status_file
        self.name =name
        self.timer = Timer(self.sampling , self.update_status_file)
        self.update_status_file()

    def stop(self):
        self.status = 'offline'
        self.update_status_file()

    def update_status_file(self):
        self.config['last_update'] = {'value' : datetime.now().strftime('%D  %H:%M:%S')  , 'type' : 'date'}
        self.config['sensor_name'] = {'value' : self.name , 'type' : 'string'}
        self.config['status']      = {'value' : self.status , 'type' : 'string'}
        self.config['sampling']   = {'value' : str(self.sampling) , 'type' : 'int', 'unit' :'sec'}
        self.config['data']   = {'value' : str(self.data) }

        __folder , __name = os.path.split(self.status_file)
        lock = FileLock('{folder}/.{name}.lock'.format(folder=__folder , name=__name))

        try:
            with lock.acquire(timeout=1):
                with open(self.status_file, 'w') as file:
                    self.config.write(file)
        except Timeout:
            print(f"WARNING {self.name} :Another application currently holds the lock, try saving file later")

        ##check if thread running if so, kill it and restart
        if self.timer.isAlive():
            self.timer.cancel()
        if self.status == 'online':
            self.timer = Timer(self.sampling , self.update_status_file)
            self.timer.setName(self.name)
            self.timer.start()


class config_class(FileSystemEventHandler):
    config = None
    timer = None
    __file_changed__ = False
    __on_modified_timer = None

    def __init__(self, file, callback=None):
        self.file_name=file
        self.read()
        __folder , __name = os.path.split(self.file_name)
        print (f"observe this folder{__folder}  ")
        self.__last_modified__ = datetime.now()
        self.__observer__ = Observer()
        self.__observer__.schedule(self, path=__folder, recursive=False)
        self.__observer__.start()
        if callback != None:
            self.callback = callback


    def callback(self, *args):
        pass

    def stop(self):
        self.__observer__.stop()
        self.__observer__.join()
    def on_modified(self, event):
        __folder , __name = os.path.split(self.file_name)
        if not event.is_directory and event.src_path.endswith(__name):
            ## ISSUE: SAME CLASS USED BY 3 APP ON SAME FILE. ON_MODIFIED TRIGGERED TWICE..
            ## EASY FIX WHEN SAME PROCESS MODIFY THE FILE AND GET THE EVENT
            ## ISSUE WITH EXTERNAL: FIRST TRIGGER IS OPENING EMPTY FILE, WATCHING FOR LOCK WOULD BE OK BUT STILL PREVENT MANUAL FILE UPDATE
            ## SOLUTION: ON MODIFIED , WAIT UNTIL FILE IS NOT TOUCHED FOR 1 SEC.

            
            file_time_stamp_sec = os.stat ( self.file_name ) [stat.ST_MTIME ]
            ctime_sec = int(time.time())
            ## was the file changed less than 2 sec ago? YES==> check again in 3sec.
            if ctime_sec - file_time_stamp_sec < 2:
                if  self.__on_modified_timer != None:
                    self.__on_modified_timer.cancel()
                self.__on_modified_timer = Timer( 2 , self.on_modified, args = { event: event})
                self.__on_modified_timer.start()
                return

            print (f"CHANGED FOUND:{self.file_name}")
            self.__file_changed__ =True

            self.callback()

    def read(self):
        self.__read_write__(update_file = False)
        self.__file_changed__ = False

    def write(self):
        __folder , __name = os.path.split(self.file_name)
        lock = FileLock('{folder}/.{name}.lock'.format(folder=__folder , name=__name))
        if self.timer != None:
            self.timer.cancel()
        try:
            with lock.acquire(timeout=1):
                self.__read_write__(update_file=True)
                time.sleep(2)
            #raise Timeout("FFF")
        except Timeout:
            print(f"WARNING {self.file_name} :Another application currently holds the lock, will tray again in 2sec")
            if self.timer != None:
                if self.timer.isAlive():
                    self.timer.cancel()
            self.timer = Timer(2 , self.write)
            self.timer.setName("config_class_file_saving")
            self.timer.start()

    def __read_write__(self,update_file=False):
        adict ={}
        var_name = None
        new_lines= []
        f = open(self.file_name, "r")
        for line  in f:
            ## skip line starting with comment.
            if re.search("^#", line):
                if update_file:
                    new_lines.append(line)
                continue
            ##variableName
            ##  value: ....
            ##  
            ## look for name
            var_name_pattern = re.search("^([^\s:]+)", line)
            if var_name_pattern:
                var_name = var_name_pattern.group(1)
                #print(f"varname={var_name}")
                adict[var_name] = {}
                if update_file:
                    new_lines.append(line)
                continue
            if var_name == None:
                    new_lines.append(line)
            else:      
                var_attribute_pattern = re.search("^(\s+)(\S+)(\s*:\s*)(.+)$", line)
                if var_attribute_pattern == None:
                    if update_file:
                        new_lines.append(line)
                    continue
                indexing   = var_attribute_pattern.group(1)
                attr_name  = var_attribute_pattern.group(2).lower()
                name_value_space = var_attribute_pattern.group(3)
                attr_value_to_eof = var_attribute_pattern.group(4)
                ## if value starts with ' or " get data within quote and this is a text
                if re.search("^[\"\']", attr_value_to_eof):
                    prev_char = None
                    idx = 0
                    delimiter = attr_value_to_eof[idx]
                    for char in  attr_value_to_eof[1:]:
                        idx = idx + 1
                        if prev_char != "\\" and char == delimiter:
                            break
                    attr_value = attr_value_to_eof[0:idx+1]
                    comment = attr_value_to_eof[idx+1::] 
                ## if it starts with [ then it is a list
                elif re.search("^\[", attr_value_to_eof):
                    attr_value= ast.literal_eval(attr_value_to_eof)
                    comment= ""
                else:
                    var_attribute_pattern = re.search("^(\S+)(\s*#.+$)", attr_value_to_eof)
                    if var_attribute_pattern != None:
                        attr_value = var_attribute_pattern.group(1)
                        comment = var_attribute_pattern.group(2)
                    else:
                        var_attribute_pattern = re.search("^(\S+)(\s*$)", attr_value_to_eof)
                        if var_attribute_pattern == None:
                            print(f"Config Error: can't  interprete this line \n{line}")
                            raise Exception( "ConfigFileError")

                        attr_value = var_attribute_pattern.group(1)
                        comment = var_attribute_pattern.group(2)
                    attr_value = self.__string2type__(attr_value)

                adict[var_name][attr_name] = attr_value
                if self.config != None:
                    if var_name in self.config and not update_file:
                        if adict[var_name][attr_name] != self.config[var_name][attr_name]:
                            print(f"INFO: new config detected {var_name} {attr_name} : {self.config[var_name][attr_name]} => {attr_value}")
                if update_file:
                    new_line =f"{indexing}{attr_name}{name_value_space}{self.config[var_name][attr_name]}{comment}\n"
                    new_lines.append(new_line)
                else:
                    adict[var_name][attr_name] = attr_value
        if len(adict) == 0:
            print("FILE IS EMPTY")
        self.config = adict

        f.close()

        if update_file:
            f = open(self.file_name, "w")
            for line in new_lines:
                 f.write(line)
            f.close()
            print(f'file updated')
            return


    def print(self):
        for var in self.config:
            for item in self.config[var]:
                print(f'{var}: {item}= {self.config[var][item]}')

        

    def __string2type__(self, txt):
        ##1, boolean type
        if txt in ['True', 'true', 'TRUE', 'FALSE', 'False', 'false']:
            txt =  txt in ['True', 'true', 'TRUE']
            attr_type = 'bool'
        ## float type
        elif re.search("^[0-9]*\.[0-9]+$", txt):
            txt = float(txt)
            attr_type = 'float'
        ## int type
        elif re.search("^[0-9]+$", txt):
            txt = int(txt)
            attr_type = 'int'
        ## string
        else:
            txt = str(txt)
            attr_type = 'str'
        return (txt)

    def getvalue(self, var, index=None, fallback=None):
        if self.__file_changed__:
            print("Read file as it changed")
            self.read()

        if var in self.config:
            val = self.config[var].get('value', None)
            if val == None:
                return fallback
            if index != None and "list" in string(type(val)):
                ## ADD fallback if index > than len
                return val[index]
            return val
        else:
            return fallback

    def setvalue(self, var , value, update_file=False):
        if self.__file_changed__:
            print("Read file as it changed")
            self.read()

        if var not in self.config:
            print(f"Config Error: this variable is not defined in config file {var}")
            raise Exception( "ConfigFileError")
        self.config[var]['value'] = value
        if update_file:
            self.write()
    


class sensor_class():
                        #   b012               
    const = {'CORNER'     : "001",
            'WRITE_SENSE' : "010",
            'READ_SENSE'  : "000",
            'LED_ON'      : "111",
            'LED_OFF'     : "110",
            'RESERVED'    : "101"}

    GPIO = IOS()
     
    def __init__(self, config_file, data_file, log_file,status_file, sampling, name):
        ### setup the config file
        self.config = config_class(config_file, callback=self.update_settings)

        self.GPIO.add(name='pwr_ack'      ,driver='pwr'     ,channel = 38 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('pwr_ack_timeout',    fallback=5000), debounce_ms=100)
        self.GPIO.add(name='pwr_line_ack' ,driver='pwr_line',channel = 40 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=100)
        self.GPIO.add(name='clock_ack'    ,driver='clock'   ,channel = 16 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=1)
        self.GPIO.add(name='enable_ack'   ,driver='enable'  ,channel = 36 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=100)
        self.GPIO.add(name='data_rx'      ,driver='data_tx' ,channel = 32 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=100)

        self.GPIO.add(name='pwr'      ,channel = 37 , direction=RPi.GPIO.OUT , ack_name='pwr_ack' )
        self.GPIO.add(name='pwr_line' ,channel = 22 , direction=RPi.GPIO.OUT , ack_name='pwr_line_ack')
        self.GPIO.add(name='clock'    ,channel = 15 , direction=RPi.GPIO.OUT , ack_name='clock_ack')
        self.GPIO.add(name='enable'   ,channel = 35 , direction=RPi.GPIO.OUT , ack_name='enable_ack')
        self.GPIO.add(name='data_tx'  ,channel = 31 , direction=RPi.GPIO.OUT , ack_name='data_rx')
        
        self.GPIO.timeout_toggle = self.config.getvalue('timeout_toggle',    fallback=False)

        #self.config.setvalue('pwr_ack_timeout', 2343 ,update_file=True)
        
        self.GPIO.setup()


 
        ### load the history of shorts
        self.log_file = log_file
        self.data_file = data_file
        short_dict = []
        data = None
        if path.exists(self.data_file):
            with open(self.data_file, 'r') as fp:
                short_dict = json.load(fp)
            if len(short_dict):
                if 'sensor_count_per_side' in short_dict and 'corner_sensor_id' in short_dict:
                    self.__sensor_count_per_side= short_dict['sensor_count_per_side']
                    self.__corner_sensor_id= short_dict['corner_sensor_id']
                    self.__sensor_count = self.__sensor_count_per_side[0] + self.__sensor_count_per_side[1] +self.__sensor_count_per_side[2] + self.__sensor_count_per_side[3]
                    data = short_dict[-1]
      


        self.watchdog = sensor_watchdog_class(status_file=status_file, sampling=sampling, name=name , data = data)

      
    def update_settings(self):
        print("INFO: Read config file & update settings")
        self.GPIO.timeout_toggle = self.config.getvalue('timeout_toggle',    fallback=False)
        
        for name in ['pwr_ack', 'pwr_line_ack', 'enable_ack' , 'data_rx']:
            self.GPIO.name[name].timeout_ms  =  self.config.getvalue('debounce_ms',    fallback=100)
        self.GPIO.name['clock_ack'].debounce_ms = self.config.getvalue('clk_debounce_ms',    fallback=1)
       
        for name in ['pwr_line_ack', 'clock_ack', 'enable_ack' , 'data_rx']:
            self.GPIO.name[name].timeout_ms  =  self.config.getvalue('signal_ack_timeout',    fallback=100)
        self.GPIO.name['pwr_ack'].debounce_ms = self.config.getvalue('pwr_ack_timeout',    fallback=5000)

    def io_connectivity_check(self, iolist_to_test, test_count, debug):
        for name in iolist_to_test:
            print(f'\ntest io name: {name}')
            self.GPIO.test_io_speed(name, test_count=test_count, debug=debug)
            print(f'test success: {self.GPIO.success}\n\taverage time 0->1 {self.GPIO.response_time[0]:3.2f}\n\taverage time 1->0 {self.GPIO.response_time[1]:3.2f}')

    def shift(self , data, debug=False, debug_text=None):
        if debug:
            print(f'INFO: ShiftInSensor data_in: {debug_text} \'{data}\'')
        rx =''
        for bit in reversed(list(data)):
            self.GPIO.setio('data_tx' , val=int(bit),  require_ack=False)
            self.GPIO.setio('clock' , val=1,  require_ack=True, force_edge_detect=RPi.GPIO.BOTH)
            self.GPIO.setio('clock' , val=0,  require_ack=True, force_edge_detect=RPi.GPIO.BOTH)
            rx = f"{RPi.GPIO.input(self.GPIO.name['data_rx'].channel)}{rx}"
        if debug:
            print(f'INFO: ShiftInSensor data_out: \'{rx}\'')
        return(rx)

    def set_shift_mode(self, debug=False, require_ack=True, raise_timeout=True):
        if debug:
            print(f'start shift mode sequence')
        self.GPIO.setio('enable', 1 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        self.GPIO.setio('clock',  1 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        self.GPIO.setio('enable', 0 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        self.GPIO.setio('clock',  0 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        time.sleep(1)
        if debug:
            print(f'shift mode enabled')

    def exec_cmd(self, delay_ms=None , debug=False, require_ack=True, raise_timeout=True, pause=False):
        if debug:
            print(f'start execute command')

        self.GPIO.setio('enable', 1 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        self.GPIO.setio('clock',  1 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        self.GPIO.setio('clock',  0 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        if delay_ms == None:
            time.sleep(self.config.getvalue('sensing_time', fallback=1000) /1000)
        else:
            time.sleep(delay_ms/1000)
        self.GPIO.setio('clock',  1 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        if pause:
            self.config.setval('break_point_paused', True)
            while self.config.getvalue('break_point_paused',    fallback=True):
                time.sleep(1)
        self.GPIO.setio('clock',  0 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)        
        self.GPIO.setio('enable', 0 ,debug=debug, require_ack=require_ack, raise_timeout=raise_timeout)
        if debug:
            print(f'command executed')

    def power_up(self, debug=False):
        self.GPIO.setio("pwr", 1, debug=debug, require_ack=True, raise_timeout=True)
        #self.GPIO.add_event_detect(channel=self.GPIO.name['pwr_ack'].channel,  edge=RPi.GPIO.FALLING, bouncetime=self.GPIO.name['pwr_ack'].debounce_ms, callback=self.power_lost_callback)

        time.sleep(self.config.getvalue('power_up_delay', fallback=10))

    def power_lost_callback(self,channel):
        print(f'Info: power lost {channel}')

    def power_down(self, debug=False):
        self.GPIO.setio("pwr", 0, debug=debug, require_ack=False, raise_timeout=True)
        all_io_are_low = False
        while ( not all_io_are_low):
            all_io_are_low = True
            for ioname in ['enable_ack', 'clock_ack', 'data_rx' ,'pwr_line_ack', 'pwr_ack']:
                print(f'Wait for inputs to see Low {ioname}: {RPi.GPIO.input(self.GPIO.name[ioname].channel)}')
                if RPi.GPIO.input(self.GPIO.name[ioname].channel) == RPi.GPIO.HIGH:
                    all_io_are_low=False
                    self.GPIO.setio(self.GPIO.name[ioname].driver, 0)

        time.sleep(self.config.getvalue('power_up_delay', fallback=10))

    def count_sensors(self, data='101',debug=False):
        print(f"\ncount sensors (max sensor:{self.config.getvalue('max_sensor', fallback=100)})")

        self.power_down()
        self.power_up()
        
        self.set_shift_mode(debug=False)

        data_to_send = self.const['RESERVED']
        rx_data= []
        corner_count = 0
        for i in range(self.config.getvalue('max_sensor', fallback=100)):
            rx = self.shift(data_to_send, debug=debug)
            data_to_send = '000'
            if rx == self.const['RESERVED']:
                if debug:
                    print(f'GOT DATA WE SHIFTED IN {len(rx_data)}')
                break
            rx_data.append(rx)

        if i == self.config.getvalue('max_sensor', fallback=100):
            print(f'Error: Reached MaxSensor count. please increase this number in config or check that the sensors pass connectivity check')
            raise Exception( "count_sensors")

        side_count = [0,0,0,0]
        sideid = 0
        corner_sensor_ID = [0,0,0,0]
        corner_count = 0

        for x in range (len(rx_data) )[::-1]:
            if debug:
                print(f'{x} {rx_data[x]}')
            if list(rx_data[x])[0]== '1': ## 1xx => is corner
                corner_count = corner_count + 1
                if sideid < 4:
                    corner_sensor_ID[sideid] = len(rx_data) - (x + 1)
                sideid = sideid + 1

        side_count[0] = corner_sensor_ID[1] - corner_sensor_ID[0]
        side_count[1] = corner_sensor_ID[2] - corner_sensor_ID[1]
        side_count[2] = corner_sensor_ID[3] - corner_sensor_ID[2]
        side_count[3] = len(rx_data) -corner_sensor_ID[3] + corner_sensor_ID[0]
        
        for i in range(4):
          print(f'Side {i}: First Sensor : {corner_sensor_ID[i]:3d} , sensor count {side_count[i]:3d}')
        print(f'Total of  {side_count[0] + side_count[1] + side_count[2] + side_count[3]} sensors')

        if corner_count < 4:
            print(f"Error: missing  corner sensor(s), only found {corner_count} /4")
            print(f"Ensure you have 'corner' jumper on the first sensor of each side.  Sensor0 is connected to JOUT")
            raise Exception( "count_sensors")

        if corner_count  > 4:
            print(f"Error: To many corner sensors,  found {corner_count} / 4 ")
            print(f"Ensure you have 'corner' jumper on the first sensor of each side.  Sensor0 is connected to JOUT")
            raise Exception( "count_sensors")
      
        if side_count[0] != side_count[2]:
            print(f"Error: opposite side with different number of sensors. SideA: {side_count[0]}  SideB: {side_count[2]}")
            print("Ensure you have 'corner' jumper on the first sensor of each side.  Sensor0 is connected to JOUT")
            raise Exception( "count_sensors")
        if side_count[1] != side_count[3]:
            print(f"Error: opposite side with different number of sensors. SideC: {side_count[1]}  SideD: {side_count[3]}")
            print("Ensure you have 'corner' jumper on the first sensor of each side.  Sensor0 is connected to JOUT")
            raise Exception( "count_sensors")

        self.__corner_sensor_id = corner_sensor_ID
        self.__sensor_count_per_side = side_count
        self.__sensor_count = self.__sensor_count_per_side[0] + self.__sensor_count_per_side[1] +self.__sensor_count_per_side[2] + self.__sensor_count_per_side[3]

        
    def split_tx(self,tx_data, index=False, reverse_data=False):
        data =[]
        sensoridx=[0,0,0,0]
        if index:
            dataindex=[]
            for i in range(self.__sensor_count):
                dataindex.append(f'{i:3d}')
            sensoridx[0] = dataindex[self.__corner_sensor_id[0]:self.__corner_sensor_id[1] ]
            sensoridx[1] = dataindex[self.__corner_sensor_id[1]:self.__corner_sensor_id[2]]
            sensoridx[2] = dataindex[self.__corner_sensor_id[2]:self.__corner_sensor_id[3]]
            sensoridx[3] = dataindex[self.__corner_sensor_id[3]:len(dataindex)] + dataindex[0:self.__corner_sensor_id[0]]

            sensoridx[1].reverse()
            sensoridx[2].reverse()
        if reverse_data:
            data = [ele for ele in reversed(tx_data)]
        else:
            data = tx_data

        side =[0,0,0,0]
        side[0] = data[self.__corner_sensor_id[0]:self.__corner_sensor_id[1] ]
        side[1] = data[self.__corner_sensor_id[1]:self.__corner_sensor_id[2]]
        side[2] = data[self.__corner_sensor_id[2]:self.__corner_sensor_id[3]]
        side[3] = data[self.__corner_sensor_id[3]:len(data)] + data[0:self.__corner_sensor_id[0]]
        
        side[1].reverse()
        side[2].reverse()

        for sideid in [3,1,0,2]:
            if index:
                print (f'sensor id (side {sideid} {len(sensoridx[sideid]):2d}) {sensoridx[sideid]}')
            print (f'data          ({len(side[sideid]):2d}) {i} {side[sideid]}')
       
    def check_stuck(self, debug=False):
        print (f'\nCheck that sensor line are not powered')
        data_tx = [self.const['READ_SENSE']] * self.__sensor_count
        data_tx.reverse()
        
        ##shift in
        for data in data_tx:
            self.shift(data, debug=debug)
        ##cmd
        self.exec_cmd()     
        
        for loop in range(2):
            ##shift out
            rx_data =[]
            for i in range(self.__sensor_count):
                rx_data.append(self.shift(self.const['READ_SENSE'], debug=debug))
            if debug:
                print(f'received:')
                self.split_tx(rx_data)
            rx_data.reverse()
            
            print_details = True
            for data_idx, data in enumerate(rx_data):
                if list(data)[1] == 1:
                    print(f'Error: sensor {data_idx} seems to be stuck at 1, check if LED is on')
                    print_details= True

            if print_details :
                self.split_tx(rx_data, index=True)
                print(rx_data)

            self.exec_cmd()     

    
    def check(self, debug = False):
        self.set_shift_mode(debug=debug)

        data_tx = []
        time_check = time.time()
        new_misconnection_list = []
        new_shorts_list ={}
        new_ignore_list = []

        short_dict = []
        ### load the history of shorts
        if path.exists(self.data_file):
            with open(self.data_file, 'r') as fp:
                short_dict = json.load(fp)
            self.watchdog.data = short_dict[-1]


        self.GPIO.setio('pwr_line', 1 ,debug=debug, require_ack=True, raise_timeout=True)
        for idx in range(self.__sensor_count):
            if idx in new_ignore_list:
                continue

            data_tx = [self.const['READ_SENSE']] * self.__sensor_count
            data_tx[idx] = self.const['WRITE_SENSE']
            data_tx.reverse()
            print (f'\nCheck Sensor {idx}')
            if debug:
                print (f'sensor {idx} has write 1')
                self.split_tx(data_tx, index=True)

            ##shift in
            for data in data_tx:
                self.shift(data, debug=debug)
            ##cmd
            self.exec_cmd()     
            
            ##shift out
            rx_data =[]
            for i in range(self.__sensor_count):
                rx_data.append(self.shift(self.const['READ_SENSE'], debug=debug))
            if debug:
                print(f'received:')
                self.split_tx(rx_data)
            rx_data.reverse()
            

            print_details = False
            ## check 1: must have opposite sensor connection
            opposite_sensor_data = rx_data[self.opposite_sensor_id(idx)]
            print(f' opposite sensor id:{self.opposite_sensor_id(idx)}  data: {opposite_sensor_data}')
            if list(opposite_sensor_data)[1] == '0':  #bit#1 is the value RED OR WRITTEN
                print(f' ==> Missing connection: Sensor {self.opposite_sensor_id(idx)} to {opposite_sensor_data}')
                print_details = True
                new_misconnection_list.append(self.opposite_sensor_id(idx))
            
            ## check :2 must not have any other connection then,
            short_list = []
            if False:
                for elem_idx, elem in enumerate(rx_data):
                    #print (f'{elem_idx} {elem}')
                    if list(elem)[1] == '1' and elem_idx != idx and elem_idx != self.opposite_sensor_id(idx):
                        print(f' ==> unexpected connection with sensor id {elem_idx} data: {elem}')
                        print_details = True
                        short_list.append(elem_idx)
                if len(short_list):
                    mindx = min([self.opposite_sensor_id(idx) , idx])
                    short_list.append(mindx)
                    if mindx in new_shorts_list:
                        short_list = short_list + new_shorts_list[mindx]
                    newlist =[]
                    for item in  (sorted (short_list)):
                        if item not in newlist:
                            newlist.append(item)
                    nindex =newlist.pop(0)
                    new_shorts_list[nindex] = newlist

                    if nindex != mindx and mindx in new_shorts_list:
                        del new_shorts_list[mindx]
                    
                    print(f'short_dict= {new_shorts_list}')
            

            if print_details :
                self.split_tx(rx_data, index=True)
                print(rx_data)
            
        self.GPIO.setio('pwr_line', 0 ,debug=debug, require_ack=True, raise_timeout=True)
        time_check =  time.time()  - time_check

        print(f"check done in {self.sec_to_string(time_check)}  (sensing time is {self.config.getvalue('sensing_time', fallback=1000)} ms")
        print(f'short_dict= {new_shorts_list}  => {len(new_shorts_list)} shorts')
        print(f'missing_connection= {new_misconnection_list} => {len(new_misconnection_list)/2} dangling sensors')
            

        ##check the new short with the last entry
        add_new_data = False
        if len(short_dict) == 0:
                add_new_data = True
                short_dict.append({"date": datetime.now().strftime('%D  %H:%M:%S')  , 'sensor_count_per_side': self.__sensor_count_per_side ,'corner_sensor_id': self.__corner_sensor_id,'short': new_shorts_list , 'misconnection': new_misconnection_list  , 'ignore': new_ignore_list })
        else:
            if sorted(new_shorts_list) != sorted(short_dict[-1]['short']) or sorted(new_misconnection_list) != sorted(short_dict[-1]['misconnection']) or sorted(new_ignore_list) != sorted(short_dict[-1]['ignore']):
                short_dict.append({"date": datetime.now().strftime('%D  %H:%M:%S')  , 'sensor_count_per_side': self.__sensor_count_per_side ,'corner_sensor_id': self.__corner_sensor_id,'short': new_shorts_list , 'misconnection': new_misconnection_list  , 'ignore': new_ignore_list })

                print(f'prev data: {short_dict[-2]}')
                print(f'new  data: {short_dict[-1]}')

                add_new_data = True
        ### save into Json format
        if add_new_data:
            with open(self.data_file, 'w') as fp:
                json.dump(short_dict, fp)

        self.watchdog.data = short_dict[-1]


    def sec_to_string(self, sec):
        minutes = int(sec//60)
        seconds = int(sec -(minutes *60))
        msec    = int((sec -(minutes *60) - seconds) *100)
        return(f'{minutes:1d}mn {seconds:02d}sec {msec:03}ms')

    def opposite_sensor_id(self,idx):
        if idx < self.__corner_sensor_id[0]:
            corner = self.__corner_sensor_id[0]
            next_corner = self.__corner_sensor_id[1]
        elif idx < self.__corner_sensor_id[1]:
            corner = self.__corner_sensor_id[1]
            next_corner = self.__corner_sensor_id[2]
        elif idx < self.__corner_sensor_id[2]:
            corner = self.__corner_sensor_id[2]
            next_corner = self.__corner_sensor_id[3]
        elif idx < self.__corner_sensor_id[3]:
            corner = self.__corner_sensor_id[3]
            next_corner = self.__corner_sensor_id[0]
        else:
            corner = self.__corner_sensor_id[0]
            next_corner = self.__corner_sensor_id[1]

        distance = corner - idx
        if distance < 0:
            distance = distance + self.__sensor_count

        equivalent = next_corner + distance -1
        if equivalent >= self.__sensor_count:
            equivalent = equivalent - self.__sensor_count


    #    print ("idx %s distance to %s : %s equivalent %s" %(idx, corner, distance, equivalent))
        return equivalent

    def dark_mode(self, debug=False):
        print('Enabling Dark Mode (LED OFF)')
        time_check =  time.time()

        self.set_shift_mode(debug=debug)

        data = self.const['LED_OFF']
        print(f'Send data {data}')
        for idx in range(self.__sensor_count):
            self.shift( data, debug=debug, debug_text=idx)
        
        self.exec_cmd(require_ack=True, raise_timeout=False)
        ##this raise timeout 207
        time_check =  time.time()  - time_check
        print(f"done in {self.sec_to_string(time_check)}  (sensing time is {self.config.getvalue('sensing_time', fallback=1000)} ms")

