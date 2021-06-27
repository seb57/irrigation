from filelock import Timeout, FileLock
from threading import Timer
import os.path
import configparser
from datetime import datetime


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


