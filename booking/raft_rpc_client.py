#!/usr/bin/env python
import logging
import socket
from typing import Tuple, Optional

from raft_peer import Peer

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class RpcClient(object):
    def send(self, peer: Peer, msg) -> Tuple[Optional[int], Optional[bool]]:
        LOG.debug("RpcClient send peer %s msg:%s", peer, msg)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect(peer.hostport())
                sock.sendall(bytes(msg))
                resp = sock.recv(1024)
                LOG.debug("RpcClient response from peer %s: %s", peer, resp)
                term_str, success_str = resp.strip().split(b' ')
                term = int(term_str)
                success = success_str == b'1'
                return term, success
            except Exception as e:
                LOG.warning("Got RpcClient Exception", e)
                raise
