# -*- coding: utf-8 -*-
# @Time    : 2020/3/18 0018 17:21
# @Author  : Y.Zuo
# @Email   : zuoy@tcd.ie
# @File    : database.py
# @Software: PyCharm
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from ipc import *
import os


def ipc_test():
    id = int(os.environ['PEER_ID'])
    print(id)
    peers_value = os.environ['PEERS'].split(' ')
    print(peers_value)
    peers = list(map(parse_hostport, peers_value))
    print(peers)
    p = Process(id, peers)
    ipc_thread = threading.Thread(target=p.run)
    ipc_thread.start()
    return p


db = SQLAlchemy()
processor = ipc_test()


def create_app(config_name=None):
    app = Flask(__name__)
    if config_name is not None:
        app.config.from_object(config_name)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app



