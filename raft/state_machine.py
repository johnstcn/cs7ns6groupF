#!/usr/bin/env python

import logging

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class StateMachine(object):
    def apply(self, new_state):
        """
        Apply the new state to the state machine
        :param new_state:
        :return:
        """
        pass


class DummyStateMachine(StateMachine):
    def __init__(self):
        self._states = []

    def apply(self, new_state):
        self._states.append(new_state)
        LOG.debug("DummyStateMachine apply new_state:%s", new_state)
