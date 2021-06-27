import threading
import time
import os.path
from os import path
from filelock import Timeout, FileLock
from threading import Timer
import re
import ast
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta
import stat

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
    

