# -*- coding: utf-8 -*-
# @Time    : 2020/3/18 0018 17:21
# @Author  : Y.Zuo
# @Email   : zuoy@tcd.ie
# @File    : database.py
# @Software: PyCharm
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name=None):
    app = Flask(__name__)
    if config_name is not None:
        app.config.from_object(config_name)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app
