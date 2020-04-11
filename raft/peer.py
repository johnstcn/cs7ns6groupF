#!/usr/bin/env python
import logging
from typing import Tuple

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class Peer(object):
    def __init__(self, peer_id: int, host: str, port: int):
        LOG.debug("Peer init peer_id:%d host:%s port:%s", peer_id, host, port)
        self._peer_id = peer_id
        self._host = host
        self._port = port

    def hostport(self) -> Tuple[str, int]:
        return self._host, self._port

    def __str__(self):
        return "Peer(%d:%s:%d)" % (self._peer_id, self._host, self._port)

    def __repr__(self):
        return str(self)