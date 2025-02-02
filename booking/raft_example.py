#!/usr/bin/env python3
import argparse
import logging
import socketserver
import threading
import time
import random

from raft_node import Node
from raft_peer import Peer
from raft_states import NodePersistentState
from raft_state_machine import DummyStateMachine
from raft_rpc_client import RpcClient
from raft_messages import VoteMessage

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')


def parse_peer(peer_str):
    peer_id, peer_host, peer_port_str = peer_str.split(":")
    return int(peer_id), peer_host, int(peer_port_str)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node_id", type=int, default=0)
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--peers", type=str, nargs="+", default=[])
    parser.add_argument("--state", type=str, default="./state.json")
    parser.add_argument("--random_seed", type=int, default=0)
    args = parser.parse_args()

    random.seed(args.random_seed)

    socketserver.TCPServer.allow_reuse_address = True
    peers = []
    for i, peer_str in enumerate(args.peers):
        peer_id, host, port = parse_peer(peer_str)
        p = Peer(peer_id, host, port)
        peers.append(p)

    prev_state = NodePersistentState.load(args.state)
    state_machine = DummyStateMachine()
    node = Node(args.node_id, prev_state, peers, state_machine)
    node_thread = threading.Thread(target=node.start, args=[args.host, args.port])
    node_thread.daemon = True
    node_thread.start()

    testingRPCClient = False  # Add to test RPC Client. Continuing example
    if testingRPCClient:
        client = RpcClient()

    try:
        while True:
            if testingRPCClient:
                if args.node_id == 0:
                    t, s = client.send(peers[0], VoteMessage(term=0, candidate_id=0, last_log_idx=0, last_log_term=0))
                    print("Term", t, "Success?:", s)
            time.sleep(1)
    except KeyboardInterrupt:
        raise SystemExit
    finally:
        node.stop()


if __name__ == '__main__':
    main()
