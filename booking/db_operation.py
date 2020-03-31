# -*- coding: utf-8 -*-
# @Time    : 2020/3/31 0031 22:33
# @Author  : Y.Zuo
# @Email   : zuoy@tcd.ie
# @File    : db_operation.py
# @Software: PyCharm
from models import *


def insert(room_id, room_state):
    result = Room(Room(RoomID=room_id, RoomState=room_state))
    db.session.add(result)
    db.session.commit()


def update(room_id):
    result = Room.query.filter(Room.RoomID == room_id).first()
    if result.RoomState == 'occupied':
        return 0
    else:
        result.RoomState = 'occupied'
        db.session.commit()
        return 1
