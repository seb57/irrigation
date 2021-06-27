
import RPi.GPIO  
import package.io_class as io_class
import package.config_class as config_class
import package.watchdog_class as watchdog_class
import time
import threading 

class sensor_class():
                        #   b012               
    const = {'CORNER'     : "001",
            'WRITE_SENSE' : "010",
            'READ_SENSE'  : "000",
            'LED_ON'      : "111",
            'LED_OFF'     : "110",
            'RESERVED'    : "101"}

    GPIO = io_class.IOS()
    __mode = None
    __fsm_step = 0
    __io_int_timer = None
    __interrupt_debug = False
    __data_rx_raw = []
    __shift_debug =False
    __max_sensor = 100
    __expect_clock_int = False
    __led_on = True
    __sensor_count = 100
    __first_sensor_offset = 0
    __test =0
    __int_debug = False
    orphan_list = []
    short_dict = {}
    __toggling = []
    def __reset(self):
        self.__mode = None
        self.__fsm_step = 0
        self.__io_int_timer = None
        self.__interrupt_debug = False
        self.__data_rx_raw = []
        self.__shift_debug =False
        self.__max_sensor = 100
        self.__expect_clock_int = False
        self.__led_on = True
        self.debug_break_point =True
        self.__toggling = []

    def __init__(self, config_file, data_file, log_file,status_file, sampling, name):
        ### setup the config file
        self.config = config_class.config_class(config_file, callback=self.update_settings)

        self.GPIO.add(name='pwr_ack'      ,driver='pwr'     ,channel = 38 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('pwr_ack_timeout',    fallback=5000), debounce_ms=1000)
        self.GPIO.add(name='pwr_line_ack' ,driver='pwr_line',channel = 33 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=100)
        self.GPIO.add(name='clock_ack'    ,driver='clock'   ,channel = 16 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=0)
        self.GPIO.add(name='enable_ack'   ,driver='enable'  ,channel = 36 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=0)
        self.GPIO.add(name='data_rx'      ,driver='data_tx' ,channel = 32 , direction=RPi.GPIO.IN, timeout_ms= self.config.getvalue('signal_ack_timeout', fallback=1000), debounce_ms=0)

        self.GPIO.add(name='pwr'      ,channel = 37 , direction=RPi.GPIO.OUT , ack_name='pwr_ack' )
        self.GPIO.add(name='pwr_line' ,channel = 22 , direction=RPi.GPIO.OUT , ack_name='pwr_line_ack')
        self.GPIO.add(name='clock'    ,channel = 15 , direction=RPi.GPIO.OUT , ack_name='clock_ack')
        self.GPIO.add(name='enable'   ,channel = 35 , direction=RPi.GPIO.OUT , ack_name='enable_ack')
        self.GPIO.add(name='data_tx'  ,channel = 31 , direction=RPi.GPIO.OUT , ack_name='data_rx')
        
        self.timeout_toggle = self.config.getvalue('timeout_toggle',    fallback=False)
        self.timeout_raise_error = self.config.getvalue('timeout_raise_error',    fallback=True)
        self.GPIO.set_io_interupt_callback(self.io_interrupt)
        

        self.GPIO.setup()
        self.GPIO.debug_config['edge_detect_callback']= False
        self.watchdog = watchdog_class.sensor_watchdog_class(status_file=status_file, sampling=sampling, name=name , data = None)

        ### enable watchdog for all IOs

   # def io_interrupt(self, *args):
    def io_interrupt(self,io):
        if self.__interrupt_debug or self.__shift_debug:
            print(f'Info: Interrupt on {io.name} {io.channel} Raising Edge {io.rising_edge_detected} Falling Edge {io.falling_edge_detected}')
        self.clock_int_check(io.name)
        self.enable_int_check(io.name)
        self.power_check(io.name)
    
    def power_check(self, name, debug=False):
        if name != 'pwr_line_ack' and name != 'pwr_ack':
            return

        ## are we doing debug toggling? if so tell we can see it and return
        if  len(self.__toggling) != 0:
            if name not in self.__toggling:
                print(f'Info: toggle on {name} detected ({RPi.GPIO.input(self.GPIO.name[name].channel)})')
                self.__toggling.append(name)
            return


        if RPi.GPIO.input(self.GPIO.name[self.GPIO.name[name].driver].channel) == RPi.GPIO.HIGH and RPi.GPIO.input(self.GPIO.name[name].channel) == RPi.GPIO.LOW:
            print(f"\nWarning: power line lost: '{self.GPIO.name[name].driver}' is OFF but '{name}' is ON ")

    def clock_int_check(self, name, debug=False):
        if name != 'clock_ack':
            return

        ## are we doing debug toggling? if so tell we can see it and return
        if  len(self.__toggling) != 0:
            if name not in self.__toggling:
                print(f'Info: toggle on {name} detected ({RPi.GPIO.input(self.GPIO.name[name].channel)})')
                self.__toggling.append(name)
            return

        ## check we have an interrupt on this
        self.GPIO.name['clock_ack']
        clock_in = RPi.GPIO.input(self.GPIO.name['clock_ack'].channel)



        fsm_step = self.__fsm_step 

        if self.__fsm_step == 1:
            if  clock_in == 1:
                self.__fsm_step = 2
        elif self.__fsm_step == 2:
            if  clock_in == 0:
                self.__fsm_step = 5
        elif self.__fsm_step == 3:
            if  clock_in == 0:
                self.__fsm_step = 4
        elif self.__fsm_step == 5:
            if  clock_in == 1:
                self.__fsm_step = 6
        elif self.__fsm_step == 6:
            if  clock_in == 0:
                self.__fsm_step = 7
        
        self.__FSM_COMMAND()
        if self.__fsm_step != fsm_step and self.__int_debug:
            print(f'DEBUG: CLOCK changed. {self.__fsm_step} {self.__mode}')

        if self.__mode == 'shift' and RPi.GPIO.input(self.GPIO.name['enable_ack'].channel) == 0 and clock_in ==  1:
            if self.__expect_clock_int:
                self.__expect_clock_int = False
            else:
                raise Exception( "Got a glitch on clock")
            self.__data_rx_raw.append( RPi.GPIO.input(self.GPIO.name['data_rx'].channel))
            if self.__shift_debug:
                print(f'received new data {self.__data_rx_raw}')

    def enable_int_check(self, name):
        if name != 'enable_ack':
            return

        ## are we doing debug toggling? if so tell we can see it and return
        if  len(self.__toggling) != 0:
            if name not in self.__toggling:
                print(f'Info: toggle on {name} detected ({RPi.GPIO.input(self.GPIO.name[name].channel)})')
                self.__toggling.append(name)
            return

        enable_in = RPi.GPIO.input(self.GPIO.name['enable_ack'].channel)
        fsm_step = self.__fsm_step 



        if self.__fsm_step == 0:
            if  enable_in == 1:
                self.__fsm_step = 1
        elif self.__fsm_step ==  1:   
            if  enable_in == 0:
                self.__fsm_step = 0
        elif self.__fsm_step ==  2:   
            if  enable_in == 0:
                self.__fsm_step = 3
        elif self.__fsm_step ==  3:   
            if  enable_in == 1:
                self.__fsm_step = 0
        elif self.__fsm_step ==  5:   
            if  enable_in == 0:
                self.__fsm_step = 8
        elif self.__fsm_step ==  6:   
            if  enable_in == 0:
                self.__fsm_step = 8
        elif self.__fsm_step ==  7:   
            if  enable_in == 0:
                self.__fsm_step = 4

        self.__FSM_COMMAND()

        if self.__fsm_step != fsm_step  and self.__int_debug:
            print(f'DEBUG: ENABLE changed. {self.__fsm_step} {self.__mode}')

    def __FSM_COMMAND(self):
        if self.__fsm_step == 8:
            if self.__mode != 'shift'  and self.__int_debug:
                print('INFO: entering shift mode')
            self.__mode ='shift'
            self.__fsm_step = 0
        elif self.__fsm_step == 4:
            if self.__mode != 'shift'  and self.__int_debug:
                print('INFO: entering shift mode')
            self.__mode ='shift'
            self.__fsm_step = 0
        elif self.__fsm_step == 5:
            if self.__mode != 'cmd'  and self.__int_debug:
                print('INFO: entering cmd mode')
            self.__mode = 'cmd'

    def set_io(self, name, val):
        RPi.GPIO.output(self.GPIO.name[name].channel, val)


    def check_io_continuity(self, debug=False ):
        for name in ['enable', 'data_tx' , 'clock', 'pwr_line']:

            toggle_count = 10
            data = [0,1] * toggle_count
            data.append(0)
            delay = [0,0]
            print(f'\ncheck continuity for {name}\n{data}')
            rmax = [0 ,0]
            rmin = [ 10000 , 1000]
            tcount = [0 , 0]
            for val in data:
                success, dly = self.set_io_and_wait_for_ack(name, val, debug=debug)
                if dly == 0:
                    continue
                time.sleep(0.5)
                tcount[val] += 1
                rmax[val] = max(dly,rmax[val])
                rmin[val] = min(dly,rmin[val])
                delay[val] = delay[val] + dly
            print(f'average 0->1 delay {delay[1]/tcount[1] :3.2f} ms range [{rmin[1]:3.2f}:{rmax[1]:3.2f}]ms')
            print(f'average 1->0 delay {delay[0]/tcount[0] :3.2f} ms range [{rmin[0]:3.2f}:{rmax[0]:3.2f}]ms')

    def __timeout_callback(self, name , value):
        if (self.GPIO.name[name].rising_edge_detected and value == 1) or (self.GPIO.name[name].falling_edge_detected and value == 0):
            self.__timeout=False
        else:
            self.__timeout=True

    def set_io_and_wait_for_ack(self, name, val, debug = False):
        if self.__io_int_timer != None:
            self.__io_int_timer.cancel()

        if debug:
            print(f'\nset_io_and_wait_for_ack: {name} =>  {RPi.GPIO.input(self.GPIO.name[name].channel)} => {val}')

            
        response_time = [0 , 0]

        if RPi.GPIO.input(self.GPIO.name[name].channel) != val:
            self.__timeout=False
            self.__io_int_timer = threading.Timer( self.GPIO.name[name].ack.timeout_ms / 1000, self.__timeout_callback, (self.GPIO.name[name].ack.name , val))
            retry_count = 0
            self.GPIO.name[name].ack.rising_edge_detected =False
            self.GPIO.name[name].ack.falling_edge_detected =False
            if debug:
                print(f' rising_edge_detected: {self.GPIO.name[self.GPIO.name[name].ack.name].rising_edge_detected}')
                print(f' falling_edge_detected: {self.GPIO.name[self.GPIO.name[name].ack.name].falling_edge_detected}')
            retry_count = 0
            while True:
                    ## set GPIO TO VALUE AND LAUNCH TIMER
                    if RPi.GPIO.input(self.GPIO.name[name].channel) != val:
                        RPi.GPIO.output(self.GPIO.name[name].channel, val)
                        response_time[val] = time.time()
                    elapsed_time = ( time.time() - response_time[val]) * 1000
                    if (self.GPIO.name[self.GPIO.name[name].ack.name].rising_edge_detected and val == 1) or (self.GPIO.name[name].ack.falling_edge_detected and val == 0):
                        response_time[val] = elapsed_time
                        if debug:
                            print(f" GOT {self.GPIO.name[name].ack.name} ack in {elapsed_time:3.2f}ms")
                        break
                    if elapsed_time > self.GPIO.name[name].ack.timeout_ms:
                        print(f"{elapsed_time:6.2f}ms since we set io to {val}, expected ack withing {self.GPIO.name[name].ack.timeout_ms:6.2f}ms. retrying")
                        retry_count += 1
                        print(f"Warning: something fishy check your ligth blicking. A Note has is not responding well (retry # {retry_count})")
                        if val == 1:
                                RPi.GPIO.output(self.GPIO.name[name].channel, 0)
                        else:
                                RPi.GPIO.output(self.GPIO.name[name].channel, 1)
                        time.sleep(0.1)

                    ## IF TIMER EXPIRE, EXIT.. TIMOUT                    
            if debug:
                print(f' success {self.GPIO.name[name].ack.name} set to {val} in {response_time[val]:3.2f} ms')

        return True , response_time[val]

    def set_io_and_wait_for_ack_not_clean(self, name, val, debug = False):
        if self.__io_int_timer != None:
            self.__io_int_timer.cancel()

        if debug:
            print(f'\nset_io_and_wait_for_ack: {name} =>  {RPi.GPIO.input(self.GPIO.name[name].channel)} => {val}')

            
        response_time = [0 , 0]

        if RPi.GPIO.input(self.GPIO.name[name].channel) != val:
            self.__timeout=False
            self.__io_int_timer = threading.Timer( self.GPIO.name[name].ack.timeout_ms / 1000, self.__timeout_callback, (self.GPIO.name[name].ack.name , val))
            retry_count = 0
            self.__io_int_timer.setName(self.GPIO.name[name].ack.name)
            self.GPIO.name[name].ack.rising_edge_detected =False
            self.GPIO.name[name].ack.falling_edge_detected =False
            if debug:
                print(f' rising_edge_detected: {self.GPIO.name[self.GPIO.name[name].ack.name].rising_edge_detected}')
                print(f' falling_edge_detected: {self.GPIO.name[self.GPIO.name[name].ack.name].falling_edge_detected}')
            while True:
                    ## set GPIO TO VALUE AND LAUNCH TIMER
                    if response_time[val] == 0:
                        response_time[val] = time.time()
                        self.__io_int_timer.start()
                        RPi.GPIO.output(self.GPIO.name[name].channel, val)
                    ## IF TIMER EXPIRE, EXIT.. TIMOUT
                    if self.__timeout:
                        response_time[val] = ( time.time() - response_time[val]) * 1000

                        if retry_count == 0 and self.GPIO.name[self.GPIO.name[name].ack.name].rising_edge_detected == False and self.GPIO.name[self.GPIO.name[name].ack.name].falling_edge_detected == False:
                            print("No interrupt detected. Try to toggle again once")
                            retry_count += 1
                            if val == 1:
                                RPi.GPIO.output(self.GPIO.name[name].channel, 0)
                            else:
                                RPi.GPIO.output(self.GPIO.name[name].channel, 1)
                            time.sleep(0.1)
                            response_time[val] = 0
                            self.__io_int_timer.cancel()
                            self.__io_int_timer = threading.Timer( self.GPIO.name[name].ack.timeout_ms / 1000, self.__timeout_callback, (self.GPIO.name[name].ack.name , val))
                            self.__io_int_timer.setName(self.GPIO.name[name].ack.name)

                        else:
                            break
                    ## WE GOT PROPER INT ON IO
                    if (self.GPIO.name[self.GPIO.name[name].ack.name].rising_edge_detected and val == 1) or (self.GPIO.name[name].ack.falling_edge_detected and val == 0):
                        self.__io_int_timer.cancel()
                        response_time[val] = ( time.time() - response_time[val]) * 1000
                        break
                    #if ( RPi.GPIO.input(self.GPIO.name[name].ack.channel) == val) and not ((self.GPIO.name[self.GPIO.name[name].ack.name].rising_edge_detected and val == 1) or (self.GPIO.name[name].ack.falling_edge_detected and val == 0)):
                    #    print("force edge detection")
                    #    self.GPIO.edge_detect_callback(self.GPIO.name[self.GPIO.name[name].ack.name].channel)

            self.__io_int_timer.cancel()
            
            if self.__timeout :
                raise_timeout =  True
                print(f'Error: timeout ({self.GPIO.name[name].ack.timeout_ms:3.2f} ms) : {name} is {RPi.GPIO.input(self.GPIO.name[name].channel)} and {self.GPIO.name[name].ack.name} is {RPi.GPIO.input(self.GPIO.name[name].ack.channel)} after {response_time[val]:3.2f} ms both are expected to be {val}')
                if not self.timeout_toggle:
                    print(f' enable timeout_toggle for futher debug')
                if debug:
                    print(f' rising_edge_detected: {self.GPIO.name[self.GPIO.name[name].ack.name].rising_edge_detected}')
                    print(f' falling_edge_detected: {self.GPIO.name[self.GPIO.name[name].ack.name].falling_edge_detected}')
                if  self.timeout_toggle:
                    self.__toggling.append(name)
                    print(f"toggling {name} (IO# {self.GPIO.name[name].channel}), expect to also see that toggle on {self.GPIO.name[name].ack.name} (IO# {self.GPIO.name[name].ack.channel})")
                    if  self.config.getvalue('break_point_paused',    fallback=False):
                        self.config.setvalue('break_point_paused', True, update_file=True)
                        print(f'INFO break_point_paused set to True, set it to False to continue')
                    print(f"{RPi.GPIO.input(self.GPIO.name[name].channel)} => {RPi.GPIO.input(self.GPIO.name[name].ack.channel)}")

                    while  self.config.getvalue('break_point_paused',    fallback=True):
                        if RPi.GPIO.input(self.GPIO.name[name].channel) == 1:
                            print(f"Set {name} to Low")
                            RPi.GPIO.output(self.GPIO.name[name].channel, RPi.GPIO.LOW)
                        else :
                            RPi.GPIO.output(self.GPIO.name[name].channel, RPi.GPIO.HIGH)
                            print(f"Set {name} to High")
                        time.sleep(0.1)
                        raise_timeout =False
                    self.__toggling= []

                if  not self.timeout_raise_error:
                    return True , response_time[val]
                if raise_timeout:
                    raise Exception("SetioTimeout")
                return False , response_time[val]

            if debug:
                print(f' success {self.GPIO.name[name].ack.name} set to {val} in {response_time[val]:3.2f} ms')

        return True , response_time[val]
                    




    def update_settings(self):
        print("UPDATE SETTINGS")
        self.GPIO.timeout_toggle = self.config.getvalue('timeout_toggle',    fallback=False)
        
        for name in ['pwr_ack', 'pwr_line_ack', 'enable_ack' , 'data_rx']:
            self.GPIO.name[name].debounce_ms  =  self.config.getvalue('debounce_ms',    fallback=100)
        self.GPIO.name['clock_ack'].debounce_ms = self.config.getvalue('clk_debounce_ms',    fallback=1)
       
        for name in ['pwr_line_ack', 'clock_ack', 'enable_ack' , 'data_rx']:
            self.GPIO.name[name].timeout_ms  =  self.config.getvalue('signal_ack_timeout',    fallback=100)
        self.GPIO.name['pwr_ack'].timeout_ms = self.config.getvalue('pwr_ack_timeout',    fallback=5000)

        self.debug_break_point = self.config.getvalue('debug_break_point',    fallback=False)

    def power_up(self, debug=False):
        print(f'INFO: Powering up')

        res = self.set_io_and_wait_for_ack("pwr", 1, debug = debug)
        if not res[0]:
            raise Exception( "PowerUp Fail")
        time.sleep(self.config.getvalue('power_up_delay', fallback=10))        
        self.__reset()
        print(f'INFO: power is now on')



    def power_down(self, debug=False):
        ## set all output to 0 first
        print(f'INFO: Powering down')

        all_io_are_low = False
        x = {'enable' : False , 'clock' : False,  'data_tx' : False ,'pwr_line' : False, 'pwr' : False}
        while ( not all_io_are_low):
            all_io_are_low = True
            for ioname in ['enable', 'clock',  'data_tx' ,'pwr_line', 'pwr']:
                if RPi.GPIO.input(self.GPIO.name[ioname].ack.channel) == RPi.GPIO.HIGH:
                    if not x[ioname]:
                        print(f'  =>Wait for inputs {self.GPIO.name[ioname].ack.name} to be low {RPi.GPIO.input(self.GPIO.name[ioname].ack.channel)}')
                        x[ioname] = True
                    all_io_are_low=False
                    RPi.GPIO.output(self.GPIO.name[ioname].channel, 0)
        time.sleep(self.config.getvalue('power_up_delay', fallback=10))
        self.__reset()
        print(f'INFO: power is now off')




    def set_cmd_mode(self, debug=False, wait_sec=0):
        if debug:
            print(f'start cmd mode sequence {self.__fsm_step} {self.__mode}')
        if debug:
            print(f'  set enable to 1')
        self.set_io_and_wait_for_ack('enable', 1)
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')
            print(f'  set clock to 1')
        self.set_io_and_wait_for_ack('clock',  1 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')
            print(f'  set clock to 0')
        self.set_io_and_wait_for_ack('clock',  0 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')
        
        time.sleep(wait_sec)
        
    def exit_cmd_mode(self, debug=False):
           
        if debug:
            print(f'exit cmd mode sequence {self.__fsm_step} {self.__mode}')

        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')        
            print(f'  set clock to 1')
        self.set_io_and_wait_for_ack('clock',  1 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')

        if  self.config.getvalue('enable_break_point',    fallback=False):
            self.config.setvalue('break_point_paused', True, update_file=True)
            print("DEBUG: enable_break_point is enabled, systems is paused. at in exit_cmd_mode set break_point_paused to False to continue")
            while self.config.getvalue('break_point_paused',    fallback=True) or not self.config.getvalue('enable_break_point',    fallback=False) :
                time.sleep(1)

        if debug:
            print(f'  set clock to 0')
        self.set_io_and_wait_for_ack('clock',  0 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')
            print(f'  set enable to 0')
        self.set_io_and_wait_for_ack('enable', 0 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')

        if debug:
            print(f'cmd mode enabled')


    def set_shift_mode(self, debug=False):
        if debug:
            print(f'start shift mode sequence __fsm_step: {self.__fsm_step} __mode:{self.__mode}')
        self.set_io_and_wait_for_ack('enable', 1 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')
        self.set_io_and_wait_for_ack('clock',  1 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')
        self.set_io_and_wait_for_ack('enable', 0 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')
        self.set_io_and_wait_for_ack('clock',  0 )
        if debug:
            print(f'  fsm= {self.__fsm_step} =>{self.__mode}')

        time.sleep(1)
        if self.__mode != 'shift':
            print(f"Error: can't enter shift mode ({self.__mode}) {self.__mode}")
            raise Exception( "ShiftMode Fail")

        if debug:
            print(f'shift mode enabled')



    def shift(self, data_tx, debug=False):
        self.__shift_debug=debug
        self.set_io_and_wait_for_ack('clock', 0, debug=debug)
        self.set_io_and_wait_for_ack('enable', 0,  debug=debug)

        if self.__mode != 'shift':
            self.set_shift_mode(debug=debug)

        if self.__shift_debug:
            print(f'mode= {self.__mode}')

        self.__data_rx_raw = []
        for data in data_tx:
            if self.__shift_debug:
                print(f'INFO: send {data}')
            for bit in reversed(list(data)):
                if self.__shift_debug:
                    print(f'INFO: send {bit}')
                RPi.GPIO.output(self.GPIO.name['data_tx'].channel, int(bit))
                self.__expect_clock_int = True
                self.set_io_and_wait_for_ack('clock', 1, debug=debug)
                self.set_io_and_wait_for_ack('clock', 0, debug=debug)

        time.sleep(2)
        self.reorder_data_tx()
    
    def count_sensor(self,reset=False, debug=False):
        print(f'INFO: count number of sensors')
        if reset:
            self.power_down(debug=False)
            self.power_up(debug=False)
        else:
            data_tx = ['000'] * self.__max_sensor
            self.shift(data_tx)
       
        data_tx = ['000'] * self.__max_sensor
        data_tx[0] ='101'
        if debug:
            print('Send the following:')
            self.print_array(data_tx , 10)
        self.shift(data_tx)
        if debug:
            print('Received the following:')
            self.print_array(self.__data_rx_ordered , 10)

        self.__sensor_count = self.__data_rx_ordered.index('101')

        if self.__sensor_count == self.config.getvalue('max_sensor', fallback=100):
            print(f'Error: Reached MaxSensor count. please increase this number in config or check that the sensors pass connectivity check')
            raise Exception( "count_sensors")

        print(f'INFO: Detected {self.__sensor_count} sensors')

        ### now detect the corners
        print(f'INFO: Looking for corners ID')
        self.set_cmd_mode(debug=False)
        self.exit_cmd_mode(debug=False)
        data_tx = []
        data_tx = ['000'] * self.__sensor_count
        if debug:
            print('Send the following:')
            self.print_array(data_tx , 10)
        self.shift(data_tx)
        if debug:
            print('Received the following:')
            self.print_array(self.__data_rx_ordered , 10)

        self.__corner_id = [key for key, val in enumerate(self.__data_rx_ordered) 
                        if val in set(['001', '011' , '111'])] 
        print (f'INFO: found {len(self.__corner_id)} corners , corner id {self.__corner_id}')
        if len(self.__corner_id) < 4:
            print(f"Error: you must at least have 4 sensors, and 4 corners")
            raise Exception('MinSensorRequired')
        self.__first_sensor_offset = self.__sensor_count - self.__corner_id[3] - 2

    def set_LED_ON(self, debug = False):
        print(f'INFO: set no led mode')
        self.set_shift_mode()
        data_tx = []
        data_tx = ['111'] * self.__sensor_count
        self.shift(data_tx)
        self.set_cmd_mode(debug=False)
        time.sleep(4)
        self.exit_cmd_mode(debug=False)
        self.__led_on = True

    def set_LED_OFF(self, debug = False):
        print(f'INFO: set no led mode')
        self.set_shift_mode()
        data_tx = []
        data_tx = ['011'] * self.__sensor_count
        self.shift(data_tx)
        self.set_cmd_mode(debug=False)
        time.sleep(4)
        self.exit_cmd_mode(debug=False)
        self.__led_on = False


    def check_com_short(self, debug = False):
        print(f'INFO: check there are not short on com line')
        self.set_shift_mode(debug=debug)
        data_tx = []
        data_tx = ['110'] * self.__sensor_count
        self.shift(data_tx, debug=debug)
        print(f'INFO: If we get glitch we have a com short')
        self.set_cmd_mode(debug=False)
        time.sleep(4)
        self.exit_cmd_mode(debug=False)
        self.__led_on = False



    #bit 012
    ###  101 -> ok  ==> na
    ###  000 -> ok  ==> na
    ###  001 -> ok  ==> na read
    ###  110 -> nok ==> Write 1 ===> issue is it takes too much current triggering reset/ even with in no LED mode, max is 20 SENSOR "ON" ~ 600mA
    ###  010 -> ok  ==> Write 1
    ###  100 -> ok  ==> NA read
    ###  111 -> Ok  ==> LED ON
    ###  011 -> Ok  ==> LED OFF
    valid_data= {'100': 'Read Sense Line', '110': 'Set Sense Line High' , '111': 'Enable Shift LED' , '011': 'Disable Shift LED'}
    def manual_debug(self, debug = False):
        
        data_tx = []
        data_tx = ['100'] * self.__sensor_count
        id = None
        while id != '1' and id != '2' and id != '3':
            id = input("Send data to all/some/one Sensor? (1/2/3) ")
            if id == "":
                id = 2
        data = None
        while data not in self.valid_data:
            for valid_data in self.valid_data:
                print(f"  {valid_data}\t{self.valid_data[valid_data]}")
            data = input("What data to do you want send?(110) ")
            if data == "":
                data = '110'
        
        if id == '1':
            data_tx = [data] * self.__sensor_count
            print(f'Send data {data} to all {self.__sensor_count} sensors')   
        elif id == '2':
            start = -1
            while start < 0 or start >= self.__sensor_count:
                start = input(f"First Sendor id ([0:{self.__sensor_count-1}]):(0)  ")
                if start == "":
                    start = 0
                start = int(start)
            last = -1
            while last < 0 or last >= self.__sensor_count:
                last = input(f"Last Sendor id ([0:{self.__sensor_count-1}]):({start}) ")
                if last == "":
                    last = start
                last = int(last)
            for x in range(start, last +1):
                data_tx[x] = data
                print (f'Send {data} to sensor {x}')
        else:            
            id = self.__sensor_count
            while id < 0 or id >= self.__sensor_count:
                id = input(f"Select a Sensor ([0:{self.__sensor_count-1}]): ")
                id = int(id)  
            data_tx[id]= data
            print(f'Send data {data} to sensor {id}')   

        self.shift(data_tx)
        self.set_io_and_wait_for_ack('pwr_line', 1)
        print("Enter CMD Mode")
        self.set_cmd_mode(debug=False)
        input("Press Enter to continue (exit CMD mode)")
        self.exit_cmd_mode(debug=False)
        self.set_io_and_wait_for_ack('pwr_line', 0)

        input("Press Enter to shift out data")
        self.shift(['000'] * self.__sensor_count)

        if debug:
            print('Received the following:')
            self.print_array(self.__data_rx_ordered , 10)

        ## check if we get any 1 on read: 101 -> -1-
        stuck_sensor_list = [key for key, val in enumerate(self.__data_rx_ordered) 
                        if val in set(['110', '010', '011' , '111'])] 
        print (f'Sensor reading 1 on their Sensing Line = {stuck_sensor_list}')

    def print_array(self, alist, length):
        txt = ""
        for i in range(len(alist)):
            txt = txt + f'{i:3d} {alist[i]} '
            if (i + 1) % 10 == 0 or i == len(alist)-1:
                print(txt)
                txt = ""

    def reorder_data_tx(self):
        self.__data_rx_ordered = []
        __data_rx_raw = self.__data_rx_raw
        for i in range(0,len(__data_rx_raw), 3):
            count = 3
            elem = ""
            while count > 0 and len(__data_rx_raw) > 0:
                elem +=  str(__data_rx_raw.pop(0))
                count = count -1
            self.__data_rx_ordered.append(elem)

    def check_all_nodes(self, debug=False):
        data_tx = []
        data_tx = ['100'] * self.__sensor_count
        if debug:
            print(f"Set {thisnode} high")
        data_tx[0]= '110'
        ### first shift is done but next time we shift out and in with one process
        self.shift(data_tx)
        node_connection = {}
        prev_node_connection = {}
        for thisnode in range(self.__sensor_count):
            cur_time = thisnode
            self.set_io_and_wait_for_ack('pwr_line', 1)
            #Enter CMD Mode
            self.set_cmd_mode(debug=False, wait_sec= self.config.getvalue('sensing_time',    fallback=100) / 1000)

            #Exit CMD mode
            self.exit_cmd_mode(debug=False)
            self.set_io_and_wait_for_ack('pwr_line', 0)

            #shift out data but prep for next test
            data_tx = []
            data_tx = ['100'] * self.__sensor_count
            if thisnode == self.__sensor_count -1:
                data_tx[0]= '110'
            else:
                data_tx[thisnode + 1]= '110'

            self.shift(data_tx)
            ## check if we get any 1 on read: 101 -> -1-
            stuck_sensor_list = [key for key, val in enumerate(self.__data_rx_ordered) 
                            if val in set(['110', '010', '011' , '111']) and key != thisnode]
            if thisnode not in prev_node_connection:
                prev_node_connection[thisnode]  = stuck_sensor_list.copy()

            node_connection[thisnode] = stuck_sensor_list.copy()
            
            print (f'Sensor #{thisnode:3d} connected to {node_connection[thisnode]}')
            if prev_node_connection[thisnode] != node_connection[thisnode]:
                print(f"Warning connection changed: {prev_node_connection[thisnode]} => {node_connection[thisnode]}")
            
            if len(node_connection[thisnode]) == 0:
                print(f"Warning missing collateral sensor: {self.equivalent(thisnode)}")
                if thisnode not in self.orphan_list:
                    self.orphan_list.append(thisnode)
                
                for anode in node_connection:
                    if thisnode in node_connection[anode]:
                        if anode not in node_connection[thisnode]:
                            print(f"Warning {anode} can observe {thisnode}, but {thisnode} can't observe {anode}")

            elif len(node_connection[thisnode]) == 1:
                ## make sure the pair are equivalent number
                if not self.equivalent( thisnode, node_connection[thisnode][0]):
                    print(f"Warning missing collateral sensor: {self.equivalent(thisnode)}")
                    print(f"Error short detected with: {node_connection[thisnode][0]}")

            else:
                ## Found short add it to the dict if it exists
                skip = False
                for time in self.short_dict:
                    if  set(self.short_dict[time]) == set(stuck_sensor_list):
                        skip = True
                if not skip:
                    while cur_time in self.short_dict:
                        cur_time = str(time.time())
                    self.short_dict[cur_time] = sorted(stuck_sensor_list)
                    print(f"New short found for {thisnode}: {stuck_sensor_list}")
                    new_stuck_sensor_list =[]
                    for sensor_idx in stuck_sensor_list:
                        doublon = min(self.equivalent(sensor_idx), sensor_idx)
                        if doublon in stuck_sensor_list and doublon not in new_stuck_sensor_list:
                            new_stuck_sensor_list.append(doublon)
                    print(f"\tshort summary: {new_stuck_sensor_list}")

    def equivalent(self, id1, id2=None):
        # compute equivalent to id1
        if id1 <= self.__corner_id[0]:
            corner = self.__corner_id[0]
            next_corner = self.__corner_id[1]
        elif id1 <= self.__corner_id[1]:
            corner = self.__corner_id[1]
            next_corner = self.__corner_id[2]
        elif id1 <= self.__corner_id[2]:
            corner = self.__corner_id[2]
            next_corner = self.__corner_id[3]
        elif id1 <= self.__corner_id[3]:
            corner = self.__corner_id[3]
            next_corner = self.__corner_id[0]
        else:
            corner = self.__corner_id[0]
            next_corner = self.__corner_id[1]

        distance = corner - id1
        if distance < 0:
            distance = distance + self.__sensor_count

        equivalent = next_corner + distance -1 + self.__first_sensor_offset
        if equivalent >= self.__sensor_count:
            equivalent = equivalent - self.__sensor_count

        

        if id2 == None:
            return equivalent
        elif id2 == equivalent:
            return True
        else:
            return False


