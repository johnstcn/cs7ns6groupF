# -*- coding: utf-8 -*-
# @Time    : 2020/3/18 0018 23:35
# @Author  : Y.Zuo
# @Email   : zuoy@tcd.ie
# @File    : search.py
# @Software: PyCharm
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired


class SearchForm(FlaskForm):
    checkin_date = StringField(label=u'Check-in Date', validators=[DataRequired()])
    checkout_date = StringField(label=u'Check-out Date', validators=[DataRequired()])
    room_num = IntegerField(label=u'Rooms', validators=[DataRequired()])

    submit = SubmitField(label=u'Search')