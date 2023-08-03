# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class KeyForm(FlaskForm):
    key = StringField('API Key', validators=[DataRequired()])
    submit = SubmitField('Submit')
