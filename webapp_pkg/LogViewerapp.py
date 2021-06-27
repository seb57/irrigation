## GENERIC CLASS
from flask import render_template, request, flash
import os
from os import listdir
from os.path import isfile, join

##APP SPECIFIC FORM AND USER CLASS
from webapp_pkg.wifiapp_forms import WIFI_STATUS_FORM , ACCESS_PT_FORM , WIFI_FORM
from webapp_pkg.logapp_forms import LOG


### NEEDED FOR APP INTEGRATION AT WEBAPP
from flask import Blueprint
logviewerapp_api = Blueprint('logviewerapp_api', __name__)



#LOG_FOLDER= os.path.abspath('config_and_log') + "/"
LOG_FOLDER = '/home/pi/config_and_log/'

@logviewerapp_api.route("/LogViewer", methods =['GET', 'POST'])
def LogViewer():
    thispagedebug =False
    choice_list = []
    for filename in sorted(listdir(LOG_FOLDER)):
        if 'lock' in filename:
            continue
        full_name = LOG_FOLDER + "/" + filename
        if isfile(full_name):
            choice_list.append( ( full_name , filename))


    form = LOG()
    form.logfile_selector.choices = choice_list

    if request.method =='POST':
        if form.validate_on_submit():
            form.read_log(request.form.get('logfile_selector'))
    return render_template("LogViewer.html",pagename='LogViewer' ,form=form ,debug=thispagedebug )
    


