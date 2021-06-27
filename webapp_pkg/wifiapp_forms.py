from flask_wtf import FlaskForm, Form
from wtforms import StringField,   validators, SelectField, SubmitField

import webapp_pkg.wifitool as wifitool


class WIFI_STATUS_FORM(FlaskForm):


    ssid =StringField( label='SSID :'  ,default=wifitool.get_wifi_ssid(),
                    validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                    render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'WIFI SSID connected to', 'readonly':True})
    ipaddress =StringField( label='IP address :'  ,default=wifitool.get_IP_address(),
                    validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                    render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'local IP Address', 'readonly':True})
    wifimode =StringField( label='Wifi Mode :'  ,default=wifitool.get_wifimode(),
                    validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                    render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'Managed: device connected to existing Wifi vs Hospot: device is hosting Wifi', 'readonly':True})
    localhost =StringField( label='LocalHost :'  ,default=wifitool.get_hostname(),
                    validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                    render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'device name', 'readonly':True})


class ACCESS_PT_FORM(FlaskForm):
    readonly = False
    if wifitool.get_hostapd_data('ssid') == 'feature not supported':
        readonly = True

    ssid =StringField( label='SSID :'  ,default=wifitool.get_hostapd_data('ssid'),
                validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'SSID name when in hotspot mode', 'readonly':readonly})
   
    pwd =StringField( label='WPA-PSK PASSWORD :'  ,default=wifitool.get_hostapd_data('wpa_passphrase'),
                validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'host spot passphrase (WPA-PSK', 'readonly':readonly})




class WIFI_FORM(FlaskForm):

    hostname_field =StringField( label='hostname'  ,
                 validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                 render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'name you would like this deviced to be called'})

    scan_field =SubmitField( label='scan wifi'   ,
                 render_kw={ 'class': 'form-control btn btn-primary', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'refresh available wifi list' })


    wifi_list_field =SelectField( label='available wifi'  ,  choices=[] , coerce = int ,
                 render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'select ssid from the list' })

    wifi_pwd_field =StringField( label='password'  ,default= "type password here",
                 validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                 render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'only suppor wpa-psk'})

    
    