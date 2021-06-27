## GENERIC CLASS
from flask import render_template, request, flash
from datetime import datetime
import logging.handlers
from package.myclass import myobject
import os, shutil
from os import listdir
from os.path import isfile, join

##APP SPECIFIC FORM AND USER CLASS
from webapp_pkg.wifiapp_forms import WIFI_STATUS_FORM , ACCESS_PT_FORM , WIFI_FORM
from webapp_pkg.Irrigationapp_forms import  MYFORM


### NEEDED FOR APP INTEGRATION AT WEBAPP
from flask import Blueprint
LeakSensorApp_api = Blueprint('LeakSensorApp_api', __name__)

INSTALL_FOLDER = '/home/pi/bin'


#LOG_FOLDER= os.path.abspath('config_and_log') + "/"
LOG_FOLDER = '/home/pi/config_and_log/'
APP_CONFIG_FILE = LOG_FOLDER + "LeakSensorApp.ini"

if not os.path.isdir(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)

if not os.path.isfile(APP_CONFIG_FILE):
    shutil.copyfile(f"{INSTALL_FOLDER}/Leaksensorapp.ini", APP_CONFIG_FILE)


LeakSensorAppConfig = myobject(file=APP_CONFIG_FILE, debug=False ,allowfieldexpension=False)
#def LeakSensorAppConfig_check():
#    if LeakSensorAppConfig.message != "":
#        socketio.emit('txt_element_id_update', {'elementid': 'message_id_field' , 'txt': LeakSensorAppConfig.message, 'addClass': 'alert-warning'}, namespace='/test') 
    
@LeakSensorApp_api.route("/LeakSensorAppConfig", methods =['GET', 'POST'])
def LeakSensorAppConfig_def():
    thispagedebug = False
    form= MYFORM()
    form.remove_all_forms()
    form= MYFORM()
    if request.method =='POST':
        form.create_elem( config=LeakSensorAppConfig)
        form= MYFORM()
        if "save" in request.form:
            form= MYFORM(request.form)
            if form.validate_on_submit():
                LeakSensorAppConfig.update_value(form.cleaned_data())
                if 'Another' in LeakSensorAppConfig.message :
                    LeakSensorAppConfig.message = ""
                    flash(f'Try Saving Data Again', 'warning')    
                else:
                    flash(f'Data Saved', 'success')    
            else:
                flash(f'Fix the issue', 'danger')
        elif "reset" in request.form:
            LeakSensorAppConfig.read_config()
            form.remove_all_forms()
            form.create_elem( config=LeakSensorAppConfig)
            form= MYFORM(None)
        else:
            ## look for key with partial substring
            for key in request.form.keys():
                if "incr_new_section_" in key:
                    section  = key.replace("incr_new_section_", "")
                    LeakSensorAppConfig.expand_item_value_in_group(section)
                    form.create_elem( config=LeakSensorAppConfig)
                    form= MYFORM()
                    break
                elif "decr_new_section_" in key:
                    section  = key.replace("decr_new_section_", "")
                    form.remove(LeakSensorAppConfig.remove_last_item_value_in_group(section))
                    form= MYFORM()
                    break

    else:
        form.create_elem( config=LeakSensorAppConfig)
        form= MYFORM()
    return render_template("LeakSensorAppConfig.html",pagename='LeakSensorAppConfig' , form=form , debug=thispagedebug )
