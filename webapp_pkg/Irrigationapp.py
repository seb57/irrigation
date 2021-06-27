## GENERIC CLASS
from flask import render_template, request, flash, current_app
from datetime import datetime
import logging.handlers
from package.myclass import mysensor, myobject
import os, shutil
from os import listdir
from os.path import isfile, join

##APP SPECIFIC FORM AND USER CLASS
from webapp_pkg.wifiapp_forms import WIFI_STATUS_FORM , ACCESS_PT_FORM , WIFI_FORM
from webapp_pkg.Irrigationapp_forms import  MYFORM
from webapp_pkg.logapp_forms import LOG


### NEEDED FOR APP INTEGRATION AT WEBAPP
from flask import Blueprint
irrigation_api = Blueprint('irrigation_api', __name__)
from threading import Timer

import configparser


#LOG_FOLDER= os.path.abspath('config_and_log') + "/"
LOG_FOLDER = '/home/pi/config_and_log/'
INSTALL_FOLDER = '/home/pi/bin'


WEBSERVER_LOG_FILE = LOG_FOLDER + "webaspp.log"
SCHEDULER_STATUS_FILE =  LOG_FOLDER+ 'scheduler.st'
SCHEDULER_LOG_FILE =  f"{LOG_FOLDER }scheduler_week{datetime.today().isocalendar()[1]}.log"
TANKS_STATUS_FILE =  LOG_FOLDER+ 'tank.st'

APP_CONFIG_FILE =  LOG_FOLDER+ 'IrrigationController.ini'
if not os.path.isdir(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)

if not os.path.isfile(APP_CONFIG_FILE):
    shutil.copyfile(f"{INSTALL_FOLDER}/default_init/Irrigationapp.ini", APP_CONFIG_FILE)

my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(WEBSERVER_LOG_FILE, maxBytes=10 *1024*1024, backupCount=1)
my_logger.addHandler(handler)
logging.getLogger().addHandler(logging.StreamHandler())


msg_queue = []


##check how many timer we have
timer_list = []
appconfig = configparser.ConfigParser()
appconfig.read( APP_CONFIG_FILE ) 
for idx in range(1, 10, 1):
    if appconfig.has_section(f"timer{idx}_mode_select"):
        timer_list.append(f'timer{idx}')
    else:
        break

print(f"debug {timer_list}")
scheduler =mysensor(file = SCHEDULER_STATUS_FILE,field_list=timer_list ,logger=my_logger)
@scheduler.changed.register
def scheduler_changed(obj, key, value):
    # print('Key %s changed to %s' % (key, value))
    # print (scheduler.field_status['sensor_name'])
    if  not "on" in scheduler.field_status['status'] :
        for name in timer_list:
            scheduler.field_status[name] ="?"

    msg_queue.append({'cmd':'status_icon_update', 'elementid': scheduler.field_status['sensor_name'] , 'value':  scheduler.field_status['status']})
    for name in timer_list:
        msg_queue.append({ 'cmd':'progress_bar_update1', 'elementid': f'#{name}_progress_bar', 'value':  f"{scheduler.field_status[name]}" })



main_tank =mysensor(file =TANKS_STATUS_FILE, field_list=['level'] ,logger=my_logger)
@main_tank.changed.register
def main_tank_changed(obj, key, value):
    # print('Key %s changed to %s' % (key, value))
    # print (main_tank.field_status['sensor_name'])
#    msg_queue.append({'cmd':'txt_element_id_update', 'elementid': '{name}_message'.format(name=main_tank.field_status['sensor_name']) , 'txt':  main_tank.field_status['message']})
    msg_queue.append({'cmd':'txt_element_id_update', 'elementid': 'message_id_field' , 'txt': main_tank.field_status['message'], 'addClass': 'alert-warning' })

    msg_queue.append({'cmd':'status_icon_update', 'elementid': main_tank.field_status['sensor_name'] , 'value':  main_tank.field_status['status'].lower()})
    msg_queue.append({'cmd':'progress_bar_update', 'elementid': '#{name}_progress_bar'.format(name=main_tank.name) , 'value':  '{value}%'.format(value=main_tank.field_status['level'])})



IrrigationControllerAppConfig = myobject(file =APP_CONFIG_FILE , debug=False ,allowfieldexpension=True ,logger=my_logger)
@IrrigationControllerAppConfig.changed.register
def IrrigationControllerAppConfig_changed(obj, key, value):
    msg_queue.append({'cmd':'txt_element_id_update', 'elementid': 'message_id_field' , 'txt': "config file changed externally please reload", 'addClass': 'alert-warning' })
#    msg_queue.append({'cmd':'reload'})

    
######################################################################################################################################################
# WEB PAGE
######################################################################################################################################################
timer_dict = {}

def reset(parameter_id):
    if parameter_id not in timer_dict:
        return
    IrrigationControllerAppConfig.read_config()
    IrrigationControllerAppConfig.set_parameterid_value(parameter_id,  IrrigationControllerAppConfig.get_parameterid_defaultvalue(parameter_id))
    IrrigationControllerAppConfig.saveconfig()
    msg_queue.append({'cmd':'reload'})
    print (f"Timer reset {parameter_id}")
    timer_dict[parameter_id].cancel()
    del timer_dict[parameter_id]

@irrigation_api.route("/", methods =['GET', 'POST'])
@irrigation_api.route("/IrrigationControllerAppConfig", methods =['GET', 'POST'])
def IrrigationControllerAppConfig_def():
    thispagedebug =False
    form= MYFORM()
    form.remove_all_forms()
    form= MYFORM()

    log = LOG()
    log.read_log(file=SCHEDULER_LOG_FILE)
#    print(request)
#    print (request.form)
    if request.method =='POST':
        form.create_elem( config=IrrigationControllerAppConfig)
        form= MYFORM()
        if "save" in request.form or "submit" in request.form:
            form= MYFORM(request.form)
            if form.validate_on_submit():
                IrrigationControllerAppConfig.update_value(form.cleaned_data())
                if 'Another' in IrrigationControllerAppConfig.message :
                    IrrigationControllerAppConfig.message = ""
                    flash(f'Try Saving Data Again', 'warning')
                else:
                    flash(f'Data Saved', 'success')
                    for timer in timer_list:
                        parameter_id = f'{timer}_mode_select'
                        time_value = IrrigationControllerAppConfig.get_parameterid_choices_value(parameter_id)[IrrigationControllerAppConfig.get_parameterid_value(parameter_id)[0]]
                        if (time_value != 0):
                            if  parameter_id not in timer_dict:
                                print(f"launch timer {parameter_id} for {time_value} ")
                                timer_dict[parameter_id] = Timer(time_value , reset, (parameter_id,) )
                                timer_dict[parameter_id].setName(parameter_id)
                                timer_dict[parameter_id].start()
                        else: 
                            if  parameter_id in timer_dict and timer_dict[parameter_id].isAlive():
                                print(f"kill timer {parameter_id}")
                                timer_dict[parameter_id].cancel()
                                del timer_dict[parameter_id]   



                    form.create_elem( config=IrrigationControllerAppConfig)
                    form= MYFORM()
            else:
                flash(f'Fix the issue', 'danger')
        elif "reset" in request.form:
            for timer in timer_list:
                reset(f"{timer}_mode_select")
            IrrigationControllerAppConfig.read_config()
            form.remove_all_forms()
            form.create_elem( config=IrrigationControllerAppConfig)
            form= MYFORM(None)
        else:
            ## look for key with partial substring
            for key in request.form.keys():
                if "incr_new_section_" in key:
                    section  = key.replace("incr_new_section_", "")
                    IrrigationControllerAppConfig.expand_item_value_in_group(section)
                    form.create_elem( config=IrrigationControllerAppConfig)
                    form= MYFORM()
                    break
                elif "decr_new_section_" in key:
                    section  = key.replace("decr_new_section_", "")
                    form.remove(IrrigationControllerAppConfig.remove_last_item_value_in_group(section))
                    form= MYFORM()
                    break
    else:
        form.create_elem( config=IrrigationControllerAppConfig)
        form= MYFORM()
    return render_template("IrrigationControllerAppConfig.html",pagename='IrrigationControllerAppConfig' ,log =log, tank=main_tank, scheduler=scheduler , form=form ,
     time=datetime.now().strftime("%d %b %y %H:%M:%S") , debug=thispagedebug )





