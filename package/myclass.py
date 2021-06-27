from datetime import datetime, timedelta
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from filelock import Timeout, FileLock, SoftFileLock
from threading import Timer
import configparser
import re
import collections
import os.path
from os import path
import stat

class MyError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Event(object):
    def __init__(self):
        self.callbacks = []

    def notify(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def register(self, callback):
        self.callbacks.append(callback)
        return callback

    @classmethod
    def watched_property(cls, event_name, key):
        actual_key = '_%s' % key

        def getter(obj):
            return getattr(obj, actual_key)

        def setter(obj, value):
            event = getattr(obj, event_name)
            setattr(obj, actual_key, value)
            event.notify(obj, key, value)

        return property(fget=getter, fset=setter)

class configpraram:
    def __init__(self, uniqueid=None, name=None, label='label' ,type='str', choices=None, choices_value=[None] , value=[None] ,min_value= None, max_value = None , default_value=None, group=None , description=None, allowfieldexpension=False, logger=None):
        self.uniqueid = uniqueid
        self.name = name
        self.label = label
        self.type = type
        self.value = value
        self.choices = choices
        self.choices_value =choices_value
        self.min_value = min_value
        self.max_value = max_value
        self.default_value = default_value
        self.group = group
        self.description = description
        self.allowfieldexpension = allowfieldexpension
        self.__logger=logger
        if self.type == 'int':
            if self.min_value == None:
                self.min_value = 0
            if self.max_value == None:
                self.max_value = 0
            if self.value == None:
                self.max_value = 0
        else:
            self.min_value = None
            self.max_value = None

    def  myprint(self,string):
        if self.__logger == None:
            print (string)
        else:
            self.__logger.info(string)

    def printdetails(self):
        for pair in vars(self).items():
            self.myprint(pair)

    def is_choices(self):
        if re.search(r'choice', self.type, re.IGNORECASE) is not None:
            return True
        return False
    def is_integer(self):
        if re.search(r'int', self.type, re.IGNORECASE) is not None:
            return True
        return False
    def is_boolean(self):
        if re.search(r'bool', self.type, re.IGNORECASE) is not None:
            return True
        return False
    def is_string(self):
        if re.search(r'str', self.type, re.IGNORECASE) is not None:
            return True
        return False
    def is_email(self):
        if re.search(r'email', self.type, re.IGNORECASE) is not None:
            return True
        return False


class myobject(FileSystemEventHandler):
    file_changed = Event.watched_property('changed', 'file_changed')

    last_modified = datetime.now()
    __name = "unset"
    message= ""

    observer =Observer()
    debug = False
    __on_modified_timer = None

    def __init__(self, file=None, allowfieldexpension=False, debug=False, ReadConfig=True, callback=None, logger=None):
        if callback != None:
            self.callback = callback
        self.file = file
        self.file_full_name = file
        self.__logger = logger

    #  if not path.exists(file):
    #      raise MyError("ERROR mysensor: file does not exists " + str(file))
        self.allowfieldexpension = allowfieldexpension
        self.config = configparser.ConfigParser()
        self.param = collections.OrderedDict()
        self.paramorder = []
        self.changed = Event()
        self.debug = debug
        __folder , self.__name = os.path.split(self.file)
        ##check that folder exists
        if  path.exists(file):
            self.read_config()
            self.__filestat = os.stat ( self.file )
        else:
            self.myprint("Warning myobject: status file does not exists: %s" % file)

        self.__lock_file = SoftFileLock(f'{__folder}/{self.__name}.lock')
        self.set_file_observer()

    def  myprint(self,string):
        if self.__logger == None:
            print (string)
        else:
            self.__logger.info(string)

    def set_file_observer(self):
        if self.debug:
             self.myprint("DEBUG: set_file_observer")
        __folder , self.__name = os.path.split(self.file)
        if not path.exists(__folder):
            self.myprint("Warning myobject: status file folder does not exists, so can't do any observation: %s" % __folder)
            raise MyError("ERROR mysensor: min requirement not met. need at least folder for status file " + str(self.file))
        self.observer.schedule(self, path= __folder, recursive=False)
        if (not self.observer.is_alive()):
            self.observer.start()

    def __del__(self):
         self.myprint("DELETE INSTANCE OF MYOBJECT %s" %self.__name)

    def callback(self, *args):
        if self.debug:
            self.myprint("INFO myobject: file changed %s" % self.file)

    def read_config(self,file=None):
            if self.debug:
                 self.myprint("READING CONFIG FILE")
            if file != None:
                self.file = file
            if self.file == None:
                self.myprint("Warning read_config: file not set")
                return 0
            self.config = configparser.ConfigParser()

            self.config.read( self.file )
            self.message=""
            #make sure param is empty
            self.param = collections.OrderedDict()
            self.parameteridkeys = []
            for parameterid in self.config.sections():
                if not 'type' in self.config[parameterid] and not 'value' in self.config[parameterid]:
                    self.myprint("Warning read_config: variable missing 'type' or 'value' field: %s" % parameterid)
                    continue
                self.parameteridkeys.append(parameterid)
                newitem  =configpraram(
                    uniqueid = self.uniquifyID(parameterid),
                    name = parameterid,
                    type  = self.get_parameterid_type(parameterid),
                    label = self.config.get( parameterid , 'label', fallback=parameterid.replace("_", " ") ),
                    value = self.get_parameterid_value(parameterid) ,
                    choices = self.get_parameterid_choices(parameterid) ,
                    choices_value = self.get_parameterid_choices_value(parameterid) ,
                    min_value=self.get_parameterid_minvalue(parameterid) ,
                    max_value=self.get_parameterid_maxvalue(parameterid) ,
                    default_value=self.get_parameterid_defaultvalue(parameterid) ,
                    group = self.get_parameterid_group(parameterid),
                    allowfieldexpension = self.transform_to_boolean(self.config.get( parameterid , 'allowfieldexpension', fallback='True')),
                    description = self.config.get( parameterid , 'description', fallback='None'),
                    logger = self.__logger
                )

            #    print (f'DEBUG {self.uniquifyID(parameterid)} , {newitem.allowfieldexpension}')
                self.param['{id}'.format(id=newitem.uniqueid)] = newitem
            self.create_order_dic()

    def prettyprint(self):
        for item_name in self.item_name_list():
            self.myprint("\nparam[%s] =" % item_name)
            self.param[item_name].printdetails()

    def is_integer(self,parameterid):
        if re.search(r'int', self.config[parameterid]['type'], re.IGNORECASE) is not None:
            return True
        return False
    def is_boolean(self,parameterid):
        if re.search(r'bool', self.config[parameterid]['type'], re.IGNORECASE) is not None:
            return True
        return False
    def is_string(self,parameterid):
        if re.search(r'str', self.config[parameterid]['type'], re.IGNORECASE) is not None:
            return True
        return False
    def is_email(self,parameterid):
        if re.search(r'email', self.config[parameterid]['type'], re.IGNORECASE) is not None:
            return True
        return False
    def is_choices(self,parameterid):
        if re.search(r'choice', self.config[parameterid]['type'], re.IGNORECASE) is not None:
            return True
        return False

    def get_parameterid_type(self,parameterid):
        if self.is_boolean(parameterid):
            return 'bool'
        elif self.is_integer(parameterid):
            return 'int'
        elif self.is_email(parameterid):
            return 'email'
        elif self.is_string(parameterid):
            return 'str'
        elif self.is_choices(parameterid):
            return 'choices'
        else:
            return 'str'

    def parameterid_exists(self,parameterid):
        if not self.config.has_section(parameterid):
            self.myprint("INFO: %s does not exists in config file %s" % (parameterid, self.file))
            return False
        if not 'type' in self.config[parameterid]:
            self.myprint("INFO: %s does has no 'type' definition in config file")
            return False
        if not 'value' in self.config[parameterid]:
            self.myprint("INFO: %s does has no 'value' definition in config file")
            return False
        return True

    def get_all_paramerterid(self):
        key_list = []
        for section in  self.config.sections():
            if self.parameterid_exists(section):
                key_list.append(section)
        return (key_list)

    def set_parameterid_value(self,parameterid, value):
        self.get_parameterid_value(parameterid)
        for item_name in self.item_name_list():
            if self.param[item_name].name == parameterid:
            #    print ( f'item_name: {item_name}  {self.param[item_name].name}  =? {parameterid} {self.param[item_name].value}')
                self.param[item_name].value = [value]


    def get_parameterid_value(self,parameterid):
        ## if config file has list already, just split it after cleaning all space for non string typ
        if (self.config.get( parameterid , 'value', fallback=None)) == None:
            print (f'PARAM {parameterid} DOES NOT EXIST')
            return None
        if re.search(r'\[', self.config[parameterid]['value'], re.IGNORECASE) is not None:
            if not self.is_string(parameterid):
                value_list = re.sub(r'\s+', '', self.config[parameterid]['value'])
            value_list = value_list.strip('][').split(',')


            for i in range(len(value_list)):
                if self.is_boolean(parameterid):
                    value_list[i] = self.transform_to_boolean(value_list[i])
                elif self.is_integer(parameterid) or self.is_choices(parameterid):
                    try :
                        value_list[i] = int(value_list[i])
                    except:
                        value_list[i] = 0
                else:
                    value_list[i] = str(value_list[i])
                    value_list[i]= value_list[i].replace('"', '')
                    value_list[i]= value_list[i].replace('\'', '')
            if self.debug:
                 self.myprint("DEBUG get_parameterid_value: value_list= %s" %value_list)
            return (value_list)
        else:
        ## if config file is not a list , convert it
            value = self.config.get( parameterid , 'value', fallback=self.get_parameterid_defaultvalue(parameterid))
            ## if default value is not set, set it to False or Min
            if re.search(r'bool', self.config[parameterid]['type'], re.IGNORECASE) is not None:
                value = self.config.get( parameterid , 'value', fallback=False)
                value = self.transform_to_boolean(value)
            elif re.search(r'int', self.config[parameterid]['type'], re.IGNORECASE) is not None or  re.search(r'choice', self.config[parameterid]['type'], re.IGNORECASE) is not None :
                try :
                    value = int(self.config.get( parameterid , 'value', fallback=0))
                except:
                    value = 0

        if not 'list' in str(type(value)) :
                    value = [value]

        if self.debug:
             self.myprint("DEBUG get_parameterid_value: value_list= %s" %value)
        return (value)

    def transform_to_boolean(self, value):
        res = (value in ["true" , "1" , 1 , "True", "TRUE", 'yes', 'YES' ,'Yes', 'y' , 'Y'])
        return res

    def get_parameterid_minvalue(self,parameterid):
        if not self.is_integer(parameterid):
            return None
        try :
            value = int(self.config.get( parameterid , 'min_value', fallback=0))
        except:
            value = 0
        return (value)

    def get_parameterid_choices(self,parameterid, with_indexes=True):
        if not self.is_choices(parameterid):
            return None
        try :
            value = []
            i = 0
            string = self.config.get( parameterid , 'choices', fallback=0)
            string = re.sub(r'\s*,\s*', ',', string)

            #string to list
            for item in list(string.split(",")):
                if with_indexes:
                    value.append ((i , item))
                    i = i +1
                else:
                    value.append(item)

        except:
            value = [(0, None)]
        return (value)

    def get_parameterid_choices_value(self,parameterid):
        if not self.is_choices(parameterid):
            return []
        value = []
        #string to list
        string = self.config.get( parameterid , 'choices_value', fallback="0")
      #  string = re.sub(r'\s*,\s*', ',', string)

        for item_value in list(string.split(",")):
            try :
                value.append(int(item_value))
            except:
                value.append(0)
        return (value)

    def get_parameterid_maxvalue(self,parameterid):
        if not self.is_integer(parameterid):
            return None
        try :
            value = int(self.config.get( parameterid , 'max_value', fallback=0))
        except:
            value = 0
        return (value)

    def get_parameterid_defaultvalue(self,parameterid):
        value = self.config.get( parameterid , 'defaultvalue', fallback=None)
        if self.is_boolean(parameterid):
            value = (value in ["true" , "1" , 1 , "True", "TRUE"])
        elif self.is_integer(parameterid):
            try :
                value = int(value)
            except:
                value = 0

        return (value)
    def get_parameterid_group(self,parameterid):
        value = self.config.get( parameterid , 'group', fallback="")
        return value

    def uniquifyID(self,paramaterid):
        idx = 0
        ## remove _<number> it it has it at the end
        paramaterid = re.sub(r'_\d+$', '', paramaterid)
        uniqueid = '{name}_{idx}'.format(name=paramaterid,idx=idx)
        while uniqueid in self.item_name_list(): #self.uniqueidorder:
            idx = idx + 1
            uniqueid = '{name}_{idx}'.format(name=paramaterid,idx=idx)
        return uniqueid

    def get_number_of_item(self):
        len(self.param)

    def item_name_list(self):
        return(list(self.param.keys()))


    def get_all_group(self):
        all_group =[]
        for item in self.param:
            if not item.group in all_group:
                all_group.append(item.group)
        return (all_group)



    def expand_item_name_value_field(self, item_name,):
        ### DUPLICATE BASED ON PARAMID ALL WE NEED IS TO ADD NEW ELEMENT TO THE VALUE ITEM
        self.param[item_name].value.append(self.param[item_name].default_value)

    def expand_item_value_in_group(self, group, append=False):
        if self.debug:
             self.myprint("DEBUG expand_item_value_in_group: add item to group %s :" % group)
        for item_name in self.item_name_list():
            if self.debug:
                 self.myprint("DEBUG expand_item_value_in_group: %s" %item_name)
            if self.param[item_name].group == group and self.param[item_name].allowfieldexpension:
                self.expand_item_name_value_field(item_name)
        self.create_order_dic()

    def remove_last_item_value_in_group(self, group):
        if self.debug :
             self.myprint("DEBUG remove_last_item_value_in_group: '%s'" % group)
        removed_idx = []
        for item_name in self.item_name_list():
            idx = len (self.param[item_name].value) -1
            if self.debug:
                 self.myprint("DEBUG remove_last_item_value_in_group item: %s (%s)" % (item_name, idx))
            if self.param[item_name].group == group and len (self.param[item_name].value) > 1:
                del  self.param[item_name].value[-1]
                removed_idx.append('{name}_{idx}'.format(name=item_name, idx=idx ))
        self.create_order_dic()
        return removed_idx
    def __process_these_items(self, itemlist):
        if self.debug:
             self.myprint("DEBUG __process_these_items:")
        idx = 0
        max_idx =  1
        ### if all item in that list have allowfieldexpension set as false, then do not add the button to expend
        at_least_one_item_allow_expension = False
        for item in itemlist:
            at_least_one_item_allow_expension = at_least_one_item_allow_expension or item.allowfieldexpension

        if self.allowfieldexpension and at_least_one_item_allow_expension:
#            print("NEW SECTION WITH BUTTON")
            self.paramorder.append(  {'uniqueid' : 'new_section_create_button' , 'valueidx' :itemlist[0].group })
        else:
 #           print ("NEW SECTION NO BUTTON")
            self.paramorder.append(  {'uniqueid' : 'new_section_no_button' , 'valueidx' :itemlist[0].group })
        while idx < max_idx:
            for item in itemlist:
                max_idx = max(max_idx, len(item.value))
                if idx < len(item.value):
                    if self.debug:
                         self.myprint("DEBUG __process_these_items: item uniqueid %s group %s value[idx] %s value %s" % ( item.uniqueid , item.group , item.value[idx], item.value))
                    self.paramorder.append(  {'uniqueid' : item.uniqueid , 'valueidx' :idx })
            self.paramorder.append(  {'uniqueid' : 'add_row' , 'valueidx' :'{a}_{b}'.format(a=item.uniqueid,b=idx) })
            idx = idx + 1


    def create_order_dic(self):
        self.paramorder = []

        same_group_item = []
        prev_group =None
        for item in self.param.values():
            if prev_group == None:
                same_group_item.append(item)
                prev_group = item.group
            elif prev_group == item.group:
                same_group_item.append(item)
            else:
                self.__process_these_items(same_group_item)
                prev_group = item.group
                same_group_item = []
                same_group_item.append(item)
        if len(same_group_item) >0:
                self.__process_these_items(itemlist = same_group_item)
        if self.debug:
            self.myprint("DEBUG create_order_dic: paramorder=%s" % self.paramorder)


    def update_value(self, adict):
        if self.debug:
             self.myprint("DEBUG update_value: adict=" % adict)

        for key, value in adict.items():
            paramaterid = re.sub(r'_\d+$', '', key)
            if not paramaterid in self.param :
                if 'add_row' in paramaterid or 'create_button' in paramaterid or 'new_section' in paramaterid:
                    continue
                self.myprint("Warning update_value: this item is not in param dict %s" % paramaterid)
                continue

            valueidx = re.sub(paramaterid+'_', '', key)
            valueidx = int(valueidx)
            if self.param[paramaterid].is_integer() or self.param[paramaterid].is_choices():
                value = int(value)
            elif self.param[paramaterid].is_boolean():
                value = self.transform_to_boolean(value)
            else:
                value= value.replace('"', '')
                value= value.replace("'", "")
            self.param[paramaterid].value[valueidx]=value
            if self.debug:
                self.myprint("DEBUG update_value: param[%s].value= %s" % (paramaterid ,self.param[paramaterid].value))
        self.saveconfig()
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.__name):
            ## ISSUE: SAME CLASS USED BY 3 APP ON SAME FILE. ON_MODIFIED TRIGGERED TWICE..
            ## EASY FIX WHEN SAME PROCESS MODIFY THE FILE AND GET THE EVENT
            ## ISSUE WITH EXTERNAL: FIRST TRIGGER IS OPENING EMPTY FILE, WATCHING FOR LOCK WOULD BE OK BUT STILL PREVENT MANUAL FILE UPDATE
            ## SOLUTION: ON MODIFIED , WAIT UNTIL FILE IS NOT TOUCHED FOR 1 SEC.

            now = datetime.now()
            if (now - self.last_modified < timedelta(seconds=4)):
                return

            file_time_stamp_sec = os.stat ( self.file ) [stat.ST_MTIME ]
            ctime_sec = int(time.time())
            #print (f'{ctime_sec}  ? {file_time_stamp_sec}')

            ## was the file changed less than 2 sec ago? YES==> check again in 3sec.
            if ctime_sec - file_time_stamp_sec < 2:
                if  self.__on_modified_timer != None:
                    self.__on_modified_timer.cancel()
                self.__on_modified_timer = Timer( 3 , self.on_modified, args = { event: event})
                self.__on_modified_timer.start()
                return

            #print (f"CHANGED FOUND:{self.__name}")
            self.last_modified = datetime.now()
            self.read_config()
            self.callback(self, self.__name)
            self.file_changed =True


    def saveconfig(self):
        if self.debug:
            self.myprint("DEBUG saveconfig")
        for item_name in self.item_name_list():
            configkey = item_name
            if  not self.config.has_section(configkey):
                configkey = re.sub(r'_\d+$', '', configkey)
                if  not self.config.has_section(configkey):
                    self.myprint('WARNING NO SECTION FOUND FOR %s (_<0-9>)' % (configkey))
                    continue
            self.config.set(configkey , 'value', str( self.param[item_name].value).replace("'","") )

        if self.debug:
            self.myprint("DEBUG saveconfig")
            for parameterid in self.config.sections():
                self.myprint("DEBUG saveconfig:  parameterid %s => %s" % (parameterid , self.config.items(parameterid)))

        self.__filestat = os.stat ( self.file )
        self.last_modified = datetime.now()
        try:
            with self.__lock_file.acquire(timeout=1):
                with open(self.file, 'w') as file:
                    self.config.write(file)
                    self.last_modified = datetime.now()

        except Timeout:
            self.myprint(f'LOCK file exists another app is using this file')
            self.message ="Another application currently holds the lock, try saving file later"






class mysensor(FileSystemEventHandler):
    status_changed = Event.watched_property('changed', 'status_changed')
    status = 'unset'
    frequency = 10
    name =None
    debug =False
    field_list =  []
    __mandatory_field = ['sensor_name', 'frequency', 'status', 'message']
    field_status= {'sensor_name' : 'None' ,'frequency'  : 1 , 'status' : 'None', 'message' : '' }#, 'level' : None ,'msg': None}
    field_changes= {'sensor_name' : False ,'frequency'  : False , 'status' : False , 'message' : False}#, 'level' : False , 'msg': False}

    __timer = None


    def __init__(self, file, callback=None, debug= False, field_list=None,  logger=None):
        self.debug =debug
      #  if not path.exists(file):
      #      raise MyError("ERROR mysensor: file does not exists " + str(file))
        if callback != None:
            self.callback = callback
        self.__logger = logger
        self.changed = Event()
        if field_list != None:
            self.field_list = field_list
            for field in field_list:
                self.field_status[field] = None
                self.field_changes[field] =False


        self.sensor_status = myobject(file = file ,allowfieldexpension=False, debug=debug ,callback=self.__somthingchanged, logger=self.__logger)
        self.__statusfile = file
        self.__somthingchanged()

    def  myprint(self,string):
        if self.__logger == None:
            print (string)
        else:
            self.__logger.info(string)

    def callback(self, *args ):
        if self.debug:
            self.myprint("INFO mysensor "+ str(self.__statusfile) + " instance changed " + str(args))
        self.status_changed =True

    def __somthingchanged(self, *args):
        if self.status == 'offline':
            self.myprint("INFO mysensor "+ str(self.__statusfile) + " is online")
        self.__read_status()
        self.callback(self , self.name)
        if self.__timer != None:
            self.__timer.cancel()
        # do a bit smaller sampling than sensor state to not hace online/offline status blinking..
        sampling = self.frequency +2
        self.__timer=Timer(sampling , self.__setoffline , [self ,  self.__statusfile , "timeout"])
        self.__timer.start()


    def __setoffline(self, *args ):
        self.myprint("INFO mysensor "+ str(self.__statusfile) + " is offline")
        self.status = 'offline'
        self.field_status['status'] =self.status
        self.field_changes['status'] =self.status_changed
        self.status_changed = True

    def __read_status(self):
        ### READ STATUS FILE AND CHECK IF ANYTHING EXISTS OF NOT
        self.sensor_status.read_config()
        if self.is_missing_field():
            self.myprint("Error mysensor: status file has missing data")
            self.msg = "sensor log is corrupted"
            return False


        somethingchange =False
        for name in self.__mandatory_field:
            if self.field_status[name] != self.sensor_status.get_parameterid_value(name)[0]:
                self.field_status[name] = self.sensor_status.get_parameterid_value(name)[0]
                self.field_changes[name] = True
        self.field_status['msg'] =  self.sensor_status.message
        if self.field_status['msg'] == "" or self.field_status['msg'] == None:
            somethingchange =True

        for name  in self.field_list:
            if self.field_status[name] != self.sensor_status.get_parameterid_value(name)[0]:
                self.field_status[name] = self.sensor_status.get_parameterid_value(name)[0]
                self.field_changes[name] = True

        self.name = self.sensor_status.get_parameterid_value('sensor_name')[0]
        self.label = self.sensor_status.get_parameterid_value('sensor_name')[0]
        self.frequency = self.sensor_status.get_parameterid_value('frequency')[0]


        self.status_changed = somethingchange
        self.field_status['status'] = self.field_status['status'].lower()
        self.status =  self.field_status['status']


    def is_missing_field(self):
        if len(self.sensor_status.param) == 0:
            self.myprint("Error Sensor: file contains no field")
            return True

        Error = False
        for name in self.__mandatory_field:
            if not name in self.sensor_status.parameteridkeys:
                self.myprint("Error sensor: mandatory field '%s' is missing" % (name))
                Error = True
        for name in self.field_list:
            if not name in self.sensor_status.parameteridkeys:
                self.myprint("Error sensor:  user defined field '%s' is missing" % (name))
                Error = True
        return(Error)
