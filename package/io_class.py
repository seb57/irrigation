import RPi.GPIO  
import threading
import time
import os.path
from os import path
from threading import Timer



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

    def callback(self, *args):
        pass
    def set_io_interupt_callback(self,callback):
        self.callback = callback
        
    def edge_detect_callback(self, channel):
        if self.debug_config['edge_detect_callback']:
            print(f'io_class edge_detect_callback: Find edge change on {channel}  {RPi.GPIO.input(channel)}')
        for name in self.name:
            if self.name[name].channel == channel:
                if RPi.GPIO.input(channel) == RPi.GPIO.HIGH:
                    self.name[name].rising_edge_detected = True
                    if self.debug_config['edge_detect_callback']:
                        print(f'name:{name} {self.name[name].channel} rising_edge_detected {self.name[name].rising_edge_detected}')
                    self.callback(self.name[name])
                    break
                else:
                    self.name[name].falling_edge_detected = True
                    if self.debug_config['edge_detect_callback']:
                        print(f'name:{name} {self.name[name].channel} falling_edge_detected {self.name[name].falling_edge_detected}')
                    self.callback(self.name[name])
                    break

    
    def add(self, name, channel, direction ,default_value=RPi.GPIO.LOW, driver=None, ack_name=None, debounce_ms=10 , timeout_ms=0, debug=False):
        if ack_name != None:
            if ack_name in self.name:
                self.name[name]= myIO(name=name, channel=channel, direction=direction, default_value=default_value, ack=self.name[ack_name] , debounce_ms=debounce_ms , timeout_ms=timeout_ms)
                if debug:
                    print(f'name={name}, channel={channel}, direction={direction}, default_value={default_value}, driver={driver}, ack={self.name[ack_name].name}  , debounce_ms={debounce_ms} , timeout_ms={timeout_ms}')
            else:
                print(f'Error: {ack_name} referenced but not defined yet')
            return

        self.name[name]= myIO(name=name, channel=channel, direction=direction, default_value=default_value, driver=driver, ack=None  , debounce_ms=debounce_ms , timeout_ms=timeout_ms)
        if debug:
            print(f'name={name}, channel={channel}, direction={direction}, default_value={default_value}, driver={driver}, ack={None}  , debounce_ms={debounce_ms} , timeout_ms={timeout_ms}')

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
                print(f'INFO: add edge detect on {ioobject.channel} ({ioobject.channel})')
                if self.name[name].debounce_ms == 0:
                    RPi.GPIO.add_event_detect(ioobject.channel, RPi.GPIO.BOTH, callback=self.edge_detect_callback )#, bouncetime=self.name[name].debounce_ms)
                else:
                    RPi.GPIO.add_event_detect(ioobject.channel, RPi.GPIO.BOTH, callback=self.edge_detect_callback , bouncetime=self.name[name].debounce_ms)

    def cleanup(self):
        RPi.GPIO.setmode(RPi.GPIO.BOARD)
        print(f'Turn all IO as input')
        RPi.GPIO.cleanup()

    def setio_rrr(self, name , val,  require_ack=True, debug=False, raise_timeout=True, force_edge_detect=None):
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
                ## set GPIO TO VALUE AND LAUNCH TIMER
                if self.response_time[val] == 0:
                    self.response_time[val] = time.time()
                    RPi.GPIO.output(self.name[name].channel, OUTPUT)
                    timer.start()
                ## IF TIMER EXPIRE, EXIT.. TIMOUT
                if not timer.isAlive():
                    self.response_time[val] = ( time.time() - self.response_time[val]) * 1000
                    timeout = True
                    break
                ## WE GOT PROPER INT ON IO
                if (self.name[self.name[name].ack.name].rising_edge_detected and CHECK_EDGE == RPi.GPIO.RISING) or (self.name[name].ack.falling_edge_detected and CHECK_EDGE == RPi.GPIO.FALLING):
                    self.response_time[val] = ( time.time() - self.response_time[val]) * 1000
                    break
                ## CATCHING CHANGE WITHOUT INTERRUPT
                # if RPi.GPIO.input(self.name[name].channel) == RPi.GPIO.input(self.name[name].ack.channel):
                #     time.sleep(self.name[name].ack.debounce_ms /1000)
                #     if RPi.GPIO.input(self.name[name].channel) == RPi.GPIO.input(self.name[name].ack.channel):
                #         self.response_time[val] = ( time.time() - self.response_time[val]) * 1000
                #         break

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
                time.sleep(0.4)
                RPi.GPIO.output(self.name[name].channel, RPi.GPIO.LOW)
                time.sleep(0.4)
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
        rmin = 10000
        rmax = -1
        for count in range(test_count):
            for val in [1 , 0]:
                res  = self.setio(name, val ,debug=debug, require_ack=True, force_edge_detect=RPi.GPIO.BOTH)
                if not res:
                    debug = True
                    success = False
                average[val] += self.response_time[val]
                if rmax < self.response_time[val]:
                    rmax = self.response_time[val]
                if rmin > self.response_time[val]:
                    rmin = self.response_time[val]
        print(f'average 0->1 response time {average[0]/test_count:6.2f}ms range: [{rmin}:{rmax}]ms')
        print(f'average 1->0 response time {average[1]/test_count:6.2f}ms range: [{rmin}:{rmax}]ms')
        self.response_time = [average[0]/test_count , average[1]/test_count]
        self.success = success
        return self.success

