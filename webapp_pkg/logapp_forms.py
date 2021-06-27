from flask_wtf import FlaskForm, Form
from wtforms import validators, SelectField, TextAreaField

import os
import os.path
from os import path


class LOG(FlaskForm):

    filecontent = TextAreaField(label='select file',id='logfiletext',default='select log a file to be printed here',   render_kw={ 'class': 'form-control', 'readonly': True})
    logfile_selector = SelectField( 'Select Logs', choices=[]  , validate_choice=False)


    def read_log(self, file):
        self.filecontent.data = ""
        if path.exists(file):
            mylog = open(file, "r")
            self.filecontent.data = mylog.read()
        self.filecontent.label = file

