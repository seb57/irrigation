import os
from os import listdir
from os.path import isfile, join
from subprocess import Popen, PIPE
from shutil import copyfile
import time, re

debug = False

def get_wifi_ssid():
    return os.popen("iwconfig wlan0 | grep 'ESSID' | awk '{print $4}' | awk -F\\\" '{print $2}'").read()
    
def get_IP_address():
    return  os.popen("ifconfig wlan0 | grep 'inet ' | awk '{print $2}'").read()

def get_wifimode():  
    return os.popen("iwconfig wlan0 | grep Mode | awk '{print $1}' | sed s/'Mode:'//g").read()


def scan_network():
        current_ssid = get_wifi_ssid()
        current_ssid = re.sub(r'\n', '', current_ssid)
        current_ssid = re.sub(r'\s+', '', current_ssid)
        mystring = ''
        trialcount = 5
        while  mystring == '' and trialcount > 1:
            mystring = os.popen("iwlist wlan0 scan | grep  ESSID").read()
            if mystring == '':
                time.sleep(1)
                trialcount = trialcount -1
        # ESSID:"NetA"
        i = 0
        ssidlist=[]
        idx = 0
        for item in mystring.split('\n')[:-1]:
            name = re.sub(r'\s*ESSID:', '', item)
            name = re.sub(r'"', '', name)
            ssidlist.append(( i ,name))
            # print(f'"{current_ssid}" "{name}"')
            if current_ssid == name:
                idx = i
            i = i + 1
            #print(f'{ssidlist} idx ={idx}')
        return(ssidlist , idx)

def update_wifi( wifi, password):
    res = os.popen(f"raspi-config nonint do_wifi_ssid_passphrase {wifi} {password}").read()
    print(f'update_wifi:res = {res}')

def get_hostname():
    f=open('/etc/hostname', 'r')
    hostname=f.read()
    f.close()
    return hostname

def set_hostname( name):
    if name==None or name=="":
        name='unset'
    try:
        f = open('/etc/hostname', "w")
        f.write(name)
        f.close()
    except:
        print(f'ERROR:set_hostname cannot write to file')
        return 'feature not supported'

def get_hostapd_data( varname):
    try:
        FILE = '/etc/hostapd/hostapd.conf'
        f = open(FILE, "r")
        value ='not_found'
        for line in f.readlines():
            if f'{varname}' in line:
                value = line.replace(f'{varname}=',"")
                break
        f.close()
        return value
    except:
        print(f'INFO :get_hostapd_data cannot read {FILE}, defeaturing hostapd')
        return 'feature not supported'

def set_hostapd_data(  varname ,varvalue):
    try:
        FILE = '/etc/hostapd/hostapd.conf'
        FILE_SAVE = '/etc/hostapd/hostapd.conf.save'
        copyfile(FILE,FILE_SAVE)
        f1 = open(FILE_SAVE, "r")
        f2 = open(FILE, 'w')

        for line in f1.readlines():
            if f'{varname}' in line and '#' not in line:
                f2.writelines(f'#{line}') 
                f2.writelines(f'{varname}={varvalue}')
            else:
                f2.writelines(line) 
        f1.close()
        f2.close()
    except:
        print(f'ERROR:set_hostapd_data cannot read/write {FILE}')