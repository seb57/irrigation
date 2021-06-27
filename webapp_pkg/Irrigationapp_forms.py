from flask_wtf import FlaskForm, Form
from wtforms import StringField, IntegerField , BooleanField, HiddenField,SubmitField,  validators, SelectField, TextAreaField,PasswordField

import os
import os.path
from os import path





class MYFORM(FlaskForm):
    debug = False

    def remove(self, name_list):
        for name in name_list:
            if self.debug:
                print("DEBUG: REMOVE FORM %s", name)
            delattr(MYFORM, name)
            if hasattr(MYFORM, 'add_row_{name}'.format(name=name)):
                delattr(MYFORM, 'add_row_{name}'.format(name=name))

    def cleaned_data(self):
        if self.debug:
            print("DEBUG cleaned_data:")
        mydict ={}
        for item in dir(MYFORM()):
            thiskey = item
            a = getattr(self, item)
            thistype = str(type(a))
            if hasattr(a, 'data'):
                thisvalue = getattr(a, 'data')
                if  "wtforms.fields" in thistype and not "HiddenField" in thistype and not "SubmitField" in thistype:
                    if self.debug:
                        print("DEBUG:  %s %s %s" %(thistype, thiskey, thisvalue))
                    mydict[thiskey] = thisvalue
        return (mydict)

    def remove_all_forms(self):
        mydict ={}
        for item in dir(MYFORM()):
            thiskey = item
            a = getattr(self, item)
            thistype = str(type(a))
            if  "wtforms.fields" in thistype :
                if self.debug:
                    print("DEBUG:  remove form %s %s" %(thistype, thiskey))
                delattr(MYFORM, thiskey)


    def create_elem(self, config):
        i = 0
        for pair in config.paramorder:
            uniqueid =pair['uniqueid']
            valueidx =pair['valueidx']
            if uniqueid == 'new_section_no_button':
                field_name = 'add_new_section_no_button_{uniqueid}'.format(uniqueid=valueidx)
                thisform =HiddenField(label=valueidx )
                setattr(MYFORM, field_name, thisform)
                continue
            if uniqueid == 'add_row':
                ## add empty field
                thisform =HiddenField(label='mt-5')
                field_name = 'add_row_{valueidx}'.format(valueidx=valueidx)
                setattr(MYFORM, field_name, thisform)
                continue
            if uniqueid == 'new_section_create_button':
                field_name = 'add_new_section_{uniqueid}'.format(uniqueid=valueidx)
                thisform =HiddenField(label=valueidx )
                setattr(MYFORM, field_name, thisform)

                field_name = 'incr_new_section_{uniqueid}'.format(uniqueid=valueidx)
                thisform =SubmitField( label='+' ,
                 render_kw={ 'class': 'btn btn-secondary', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'expand this section'})
                setattr(MYFORM, field_name, thisform)

                field_name = 'decr_new_section_{uniqueid}'.format(uniqueid=valueidx)
                thisform =SubmitField( label='-'  ,
                 render_kw={ 'class': 'btn btn-secondary', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':'reduce this section'})
                setattr(MYFORM, field_name, thisform)
                
                continue            

            field_name = '{uniqueid}_{valueidx}'.format(uniqueid=uniqueid,valueidx=valueidx)

            if self.debug:
                print("DEBUG configform: FIELD %s label %s value %s  (min %s ) (max %s)" %( field_name, config.param[uniqueid].label , config.param[uniqueid].value[valueidx] ,config.param[uniqueid].min_value , config.param[uniqueid].max_value))
            
            if config.param[uniqueid].is_integer():
                thisform =IntegerField( label=config.param[uniqueid].label  ,default=config.param[uniqueid].value[valueidx] ,
                 validators= [ validators.NumberRange(min=config.param[uniqueid].min_value, max=config.param[uniqueid].max_value) ],
                 render_kw={ 'class': 'form-control', 'type':'number', 'min':config.param[uniqueid].min_value, 'max':config.param[uniqueid].max_value ,'data-toggle':'tooltip' ,  'data-placement':'right', 'title':config.param[uniqueid].description})
                setattr(MYFORM, field_name, thisform)
            elif config.param[uniqueid].is_choices():
                thisform =SelectField( label=config.param[uniqueid].label  ,  choices=config.param[uniqueid].choices , coerce = int, default = config.param[uniqueid].value[0] ,
                 render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':config.param[uniqueid].description})
                setattr(MYFORM, field_name, thisform)
            elif config.param[uniqueid].is_boolean(): 
                thisform =BooleanField( label=config.param[uniqueid].label  ,default=config.param[uniqueid].value[valueidx] ,
                 render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':config.param[uniqueid].description})
                setattr(MYFORM, field_name, thisform)
            elif config.param[uniqueid].is_email(): 
                thisform =StringField( label=config.param[uniqueid].label  ,default=config.param[uniqueid].value[valueidx] ,
                 validators=[validators.DataRequired(),  validators.Length(min=6, max=35)] ,
                 render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':config.param[uniqueid].description})
                setattr(MYFORM, field_name, thisform)
            elif config.param[uniqueid].is_string(): 
                thisform =StringField( label=config.param[uniqueid].label  ,default=config.param[uniqueid].value[valueidx] ,
                 render_kw={ 'class': 'form-control', 'data-toggle':'tooltip' ,  'data-placement':'right', 'title':config.param[uniqueid].description})
                setattr(MYFORM, field_name, thisform)


