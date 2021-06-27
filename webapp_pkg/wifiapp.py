## GENERIC CLASS
from flask import render_template, request, flash
from datetime import datetime


##APP SPECIFIC FORM AND USER CLASS
from webapp_pkg.wifiapp_forms import WIFI_STATUS_FORM , ACCESS_PT_FORM , WIFI_FORM
import webapp_pkg.wifitool as wifitool


### NEEDED FOR APP INTEGRATION AT WEBAPP
from flask import Blueprint
wifi_api = Blueprint('wifi_api', __name__)

######################################################################################################################################################
# WIFI CONFIG
######################################################################################################################################################
(ssid_list , ssid_idx)  = wifitool.scan_network()



@wifi_api.route("/Wifi", methods =['GET', 'POST'])
def Wifi():
    global ssid_list, ssid_idx
    thispagedebug =False
    msg = ""
    wifistatus_form = WIFI_STATUS_FORM()
    wifistatus_form.ssid.default      = wifitool.get_wifi_ssid()
    wifistatus_form.ipaddress.default = wifitool.get_IP_address()
    wifistatus_form.wifimode.default = wifitool.get_wifimode()
    wifistatus_form.localhost.default= wifitool.get_hostname() +".local"

    access_point_form =ACCESS_PT_FORM(request.form)
    wifi_form = WIFI_FORM(request.form)
    wifi_form.wifi_list_field.choices = ssid_list

    if request.method =='GET':
        wifi_form.hostname_field.default= wifitool.get_hostname() 
        wifi_form.wifi_list_field.default = ssid_idx

    if request.method =='POST':
        wifi_form.hostname_field.default  = request.form.get('hostname_field')
        wifi_form.wifi_list_field.default = request.form.get('wifi_list_field')

        
        if wifi_form.validate() and access_point_form.validate():
        #    print(f'request.form = {request.form}')
            if "scan_field" in request.form :
                #msg_queue.append({'cmd':'txt_element_id_update', 'elementid': 'message_id_field' , 'txt': "scanning... please wait", 'addClass': 'alert-warning' })
                (ssid_list , ssid_idx)  = wifitool.scan_network()
                #flash(f'new wifi list is now updated available wifi', 'sucess')
                wifi_form.wifi_list_field.choices = ssid_list
                wifi_form.wifi_list_field.default = ssid_idx
            else:
                if "hostname_field" in request.form:
                    if request.form.get('hostname_field') != wifitool.get_hostname():
                        wifitool.set_hostname(request.form.get('hostname_field'))
                        msg = msg + f'Reboot to activate new hostname\n'
                if "wifi_list_field" in request.form and "wifi_pwd_field" in request.form:
                    if request.form.get('wifi_list_field') != str(ssid_idx) or not 'type password here'  in request.form.get('wifi_pwd_field'):
                        msg = msg + f'connecting to new network.... please wait'
                        wifitool.update_wifi(ssid_list[int(request.form.get('wifi_list_field'))][1],request.form.get('wifi_pwd_field'))

                if msg:
                    flash(f'{msg}', 'warning')    



    wifistatus_form.process()
    access_point_form.process()
    wifi_form.process()
    return render_template("wifi.html",pagename='wifi' , wifi_form=wifi_form,  access_point_form=access_point_form, wifistatus_form=wifistatus_form ,
     time=datetime.now().strftime("%d %b %y %H:%M:%S") ,debug=thispagedebug )