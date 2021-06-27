from flask import Flask,  render_template ,current_app
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
import configparser
from webapp_pkg.webapp_socketio import WEBAPPSOCKETIO


import os, sys, traceback, shutil

try:
    dateTimeObj = datetime.now()
    print( dateTimeObj.strftime('%D  %H:%M:%S') + ": Program Started")

    
    LOG_FOLDER = '/home/pi/config_and_log/'
    INSTALL_FOLDER = '/home/pi/bin'
    WEBAPP_CONFIG_FILE = LOG_FOLDER + 'webapp.ini'
    webappconfig = configparser.ConfigParser()
    if not os.path.isfile(WEBAPP_CONFIG_FILE):
        shutil.copyfile(f"{INSTALL_FOLDER}/default_init/webapp.ini", WEBAPP_CONFIG_FILE)
    
    webappconfig.read( WEBAPP_CONFIG_FILE ) 

    
    template_dir = os.path.abspath('webapp_pkg/templates')
    app = Flask(__name__, template_folder = template_dir)
    app_context = app.app_context()
    
    ###NOTE STILL NEED TO UPDATE base.html to change nav bar

    if webappconfig['wifiapp'].getboolean('enabled', False):
        print(f"INFO: import WifiApp")
        from webapp_pkg.wifiapp import wifi_api
        app.register_blueprint(wifi_api)
    if webappconfig['logviewerapp_api'].getboolean('enabled', False):
        print(f"INFO: import LogViewApp")
        from webapp_pkg.LogViewerapp import logviewerapp_api
        app.register_blueprint(logviewerapp_api)
    if webappconfig['irrigation_api'].getboolean('enabled', False):
        print(f"INFO: import IrrigationApp")
        from webapp_pkg.Irrigationapp import irrigation_api
        app.register_blueprint(irrigation_api)
    if webappconfig['leakSensorApp_api'].getboolean('enabled', False):
        print(f"INFO: import LeakApp")
        from webapp_pkg.Leaksensorapp import LeakSensorApp_api
        app.register_blueprint(LeakSensorApp_api)

    app.config['SECRET_KEY']= "my_little_secret!"
    csrf = CSRFProtect(app)

    #####################################################################################################################################################
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
    ######################################################################################################################################################
    socketio = WEBAPPSOCKETIO(app, async_mode=None)

    dateTimeObj = datetime.now()
    socketio.run(app, debug=False, host="0.0.0.0", port=80)


except KeyboardInterrupt:
    print("User KeyboardInterrupt")


except:
    print("Exception in user code:")
    print("-"*60)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for item in traceback.format_exc().splitlines():
        print(item)
    print("-"*60)
    
finally:
    dateTimeObj = datetime.now()
    print(dateTimeObj.strftime('%D  %H:%M:%S') +": Program Exit")
    sys.exit(-1)
