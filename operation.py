#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/4/13 0013 15:06
# @Author  : Y.Zuo
# @Email   : zuoy@tcd.ie
# @File    : operation.py
# @Software: PyCharm
import logging
import sqlite3
import time


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def connect(db):
    """
    :param db: str, e.g. 'test.db'
    """
    try:
        conn = sqlite3.connect(db)
        logger.debug('Connecting to database')

        return conn

    except Exception as e:
        logger.warning("Fail to connect database")
        logger.warning(e)
        return None


def create_table(conn, table_name):
    """
    :param conn: database connection
    :param table_name: name
    """
    try:
        c = conn.cursor()
        # Create table
        c.execute('''CREATE TABLE {} (
                        ID INTEGER PRIMARY KEY autoincrement, 
                        RoomID INTEGER NOT NULL,  
                        RoomState CHAR(12) NOT NULL, 
                        BookTime DOUBLE)
                        '''.format(table_name))

        conn.commit()
        logger.debug('Create table in database')

    except Exception as e:
        logger.warning("Fail to create table in database")
        logger.warning(e)


def select(conn, table_name):
    try:
        c = conn.cursor()
        c.execute('''SELECT * FROM {} WHERE RoomState='unoccupied'
                        '''.format(table_name))

        logger.debug('Search in database')
        return c.fetchall()

    except Exception as e:
        logger.warning("Fail to search in database")
        logger.warning(e)
        return None


def insert(conn, table_name, room_id, room_state='unoccupied'):
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO {} (RoomID, RoomState) VALUES ({}, '{}')
                        '''.format(table_name, room_id, room_state))

        conn.commit()
        logger.debug("Insert to table(%s)", table_name)

    except Exception as e:
        logger.warning("Fail to insert to table(%s)", table_name)
        logger.warning(e)


def update(conn, table_name, room_id):
    try:
        c = conn.cursor()
        c.execute('''SELECT * FROM {} WHERE RoomID={}
                        '''.format(table_name, room_id))
        room = c.fetchall()[0]
        if room[2] == 'occupied':
            logger.info("Room is booked")
            return 0
        else:
            t = time.time()
            c.execute('''UPDATE {} SET RoomState='occupied', BookTime={} WHERE RoomID={}
                            '''.format(table_name, t, room_id))
            conn.commit()
            logger.info("Update RoomID(%s) to occupied", room_id)
            return 1

    except Exception as e:
        logger.warning("Fail to update table(%s)", table_name)
        logger.warning(e)


if __name__ == '__main__':
    conn = connect('test.db')
    table_name = 'room'
    # create_table(conn, table_name)
    # lis = ['101', '102', '103', '104', '105', '106', '201', '202', '203', '204', '205', '206']
    # for i in lis:
    #     insert(conn, 'room', int(i))
    # result = select(conn, 'room')
    update(conn, table_name, 101)
    conn.close()