#!/usr/bin/env python

import logging

from states import BookingData

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class StateMachine(object):
    def apply(self, data: BookingData):
        """
        Apply new data to the state machine
        :param data: new BookingData
        :return:
        """
        pass


class DummyStateMachine(StateMachine):
    def __init__(self):
        self._states = []

    def apply(self, data: BookingData):
        self._states.append(data)
        LOG.debug("DummyStateMachine apply new_state:%s", data)
