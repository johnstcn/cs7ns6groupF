# -*- coding: utf-8 -*-
# @Time    : 2020/3/18 0018 22:18
# @Author  : Y.Zuo
# @Email   : zuoy@tcd.ie
# @File    : login.py
# @Software: PyCharm
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    username = StringField(label=u'Account', validators=[DataRequired()])
    # password = PasswordField(label=u'Password', validators=[DataRequired()])
    submit = SubmitField(label=u'Submit')