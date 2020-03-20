# -*- coding: utf-8 -*-
# @Time    : 2020/3/18 0018 16:03
# @Author  : Y.Zuo
# @Email   : zuoy@tcd.ie
# @File    : models.py
# @Software: PyCharm
from database import db


class Room(db.Model):
    __tablename__ = 'room'

    RoomID = db.Column(db.String(10), doc='RoomID', primary_key=True)
    # RoomPrice = db.Column(db.Float, doc='RoomPrice', nullable=False)
    RoomState = db.Column(db.String(10), doc='RoomState', default='unoccupied', nullable=False)


# class Customer(db.Model):
#     __tablename__ = 'customer'
#
#     CustomerID = db.Column(db.String(10), doc='CustomerID', primary_key=True)
#     CustomerName = db.Column(db.String(10), doc='CustomerName', nullable=False)
#     CustomerIDNumber = db.Column(db.String(10), doc='CustomerIDNumber', nullable=False)
#     CustomerPhone = db.Column(db.String(10), doc='CustomerPhone', nullable=False)
#     CustomerCreateDate = db.Column(db.Date, doc='CustomerCreateDate', nullable=False)


class InHistory(db.Model):
    __tablename__ = 'inHistory'

    InID = db.Column(db.String(10), primary_key=True)
    # CustomerId = db.Column(db.String(10), db.ForeignKey('customer.CustomerID'), doc='CustomerID', nullable=False)
    # CustomerInDate = db.Column(db.Date, doc='CustomerInDate', nullable=False)
    # CustomerOutDate = db.Column(db.Date, doc='CustomerOutDate', nullable=False)
    CustomerId = db.Column(db.String(10), doc='CustomerID', nullable=False)
    RoomID = db.Column(db.String(10), db.ForeignKey('room.RoomID'), doc='RoomID', nullable=False)


class OutHistory(db.Model):
    __tablename__ = 'outHistory'

    OutID = db.Column(db.String(10), primary_key=True)
    # CustomerId = db.Column(db.String(10), db.ForeignKey('customer.CustomerID'), doc='CustomerID', nullable=False)
    # CustomerInDate = db.Column(db.Date, doc='CustomerInDate', nullable=False)
    # CustomerOutDate = db.Column(db.Date, doc='CustomerOutDate', nullable=False)
    CustomerId = db.Column(db.String(10), doc='CustomerID', nullable=False)
    RoomID = db.Column(db.String(10), db.ForeignKey('room.RoomID'), doc='RoomID', nullable=False)
