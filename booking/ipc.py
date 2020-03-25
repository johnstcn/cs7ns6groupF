#!/usr/bin/env python3

import argparse
import asyncio
import logging
import socket
import socketserver
import threading

LOG = logging.getLogger(logging.basicConfig())
LOG.setLevel(logging.DEBUG)

ELECTION = b"vote"
HEALTHCHECK = b"ok?"
VICTORY = b"vctr"
OK = b"ok"
WHOISLEADER = b"ldr?"

ACK = b"ack"
NACK = b"nack"

CLIENT_TIMEOUT = 1


"""
Process represents one leader-elected process. It has an ID and knows about a number of peers.
In its initial state:
  - it is not leader
  - it does not know who the leader is
  - it is not in the process of electing a new leader
"""


class Process(object):
    def __init__(self, id, peers):
        self.id = id
        self.peers = peers
        self.election = False
        self.leader_id = None
        self.multicaster = Multicaster(peers[:id] + peers[id + 1 :])

    """
    am_leader returns True if a leader ID is known and the leader ID is my own ID.
    Otherwise, returns False.
    """

    def am_leader(self):
        if self.leader_id is None:
            return False
        return self.leader_id == self.id

    """
    handle_request_vote is the callback function invoked when someone requests a leader election.
    """

    def handle_request_vote(self, *args):
        if self.election:
            LOG.error("already doing an election!")
            return OK

        LOG.info("doing an election")
        thread = threading.Thread(target=self.perform_election)
        thread.daemon = True
        thread.start()
        return OK

    """
    handle_request_healthcheck is the callback function invoked when someone asks if we are alive.
    """

    def handle_request_healthcheck(self, *args):
        return OK

    """
    handle_request_victory is the callback function invoked when a leader is elected
    """

    def handle_request_victory(self, *args):
        self.leader_id = int(args[0])
        return OK

    """
    handle_request_leader is the callback function invoked when someone asks who the leader is
    """

    def handle_request_leader(self, *args):
        if self.leader_id is None:
            return None
        return b"%s:%d" % self.peers[self.leader_id]

    """
    perform_election is invoked when we want to perform leader election 
    """

    def perform_election(self):
        if self.election:
            return
        self.election = True
        # optimistically assume that we can be the leader initially
        can_be_leader = True
        try:
            # notify all peers with a higher id
            notify_peers = self.peers[self.id + 1 :]
            while True:
                if not notify_peers:
                    break
                # pass it on
                host, port = notify_peers[0]
                resp = send_message(ELECTION, host, port)
                if resp == OK:
                    LOG.info(
                        "{}:{} acknowledged our election request".format(host, port)
                    )
                    can_be_leader = False  # darnit
                else:
                    LOG.warn(
                        "{}:{} did not acknowledge our election request".format(
                            host, port
                        )
                    )
                notify_peers = notify_peers[1:]
        finally:
            if can_be_leader:
                self.assume_leadership()
            self.election = False

    """
    assume_leadership is invoked when we determine we may be the leader
    """

    def assume_leadership(self):
        for (hostid, (host, port)) in enumerate(self.peers):
            if hostid == self.id:
                continue
            resp = send_message(VICTORY + b" %d" % self.id, host, port)
            if resp == OK:
                LOG.info("{}:{} acknowledged our leadership".format(host, port))
            elif resp is None:
                LOG.warn(
                    "{}:{} could not acknowledge our leadership".format(host, port)
                )
            else:
                LOG.warn("{}:{} did not acknowledge our leadership".format(host, port))
        self.leader_id = self.id

    def run(self):
        callbacks = {
            ELECTION: self.handle_request_vote,
            HEALTHCHECK: self.handle_request_healthcheck,
            VICTORY: self.handle_request_victory,
            WHOISLEADER: self.handle_request_leader,
        }
        hostport = self.peers[self.id]
        with socketserver.TCPServer(hostport, Handler(callbacks)) as server:
            try:
                LOG.info("listening on {}:{}".format(*hostport))
                server.serve_forever()
            except KeyboardInterrupt as e:
                LOG.critical("user sent keyboard interrupt, shutting down")
            except Exception as e:
                LOG.error("got exception: " + str(e))


"""
Handler handles incoming messages and calls its relevant callback function.
"""


class Handler(socketserver.BaseRequestHandler):
    def __init__(self, callbacks):
        self.callbacks = callbacks

    def __call__(self, request, client_address, server):
        h = Handler(self.callbacks)
        socketserver.BaseRequestHandler.__init__(h, request, client_address, server)

    def handle(self):
        msg = self.request.recv(1024).strip()
        LOG.debug("got {} from {}:{}".format(msg, *self.client_address))
        if not msg:
            return

        verb = msg.split(b" ")[0]
        args = msg.split(b" ")[1:]
        if verb not in self.callbacks:
            LOG.error("no idea what to do with {} {}".format(verb, args))
            return
        cbfunc = self.callbacks[verb]
        resp = cbfunc(*args)
        if resp:
            self.request.sendall(resp)


class Multicaster(object):
    def __init__(self, peers):
        self.peers = peers

    def multisend(self, msg):
        tasks = []
        for peer in self.peers:
            tasks.append(self.send(msg, peer))

        with asyncio.get_event_loop() as loop:
            results = loop.run_until_complete(*tasks)
            return all(results)

    async def send(self, msg, peer):
        host, port = peer
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(CLIENT_TIMEOUT)
            try:
                s.connect((host, port))
                s.sendall(msg)
                LOG.debug("sent {} to {}:{}".format(msg, host, port))
                resp = s.recv(1024).strip()
                LOG.debug("got {} from {}:{}".format(resp, host, port))
                return resp == ACK
            except socket.timeout:
                LOG.error("timeout sending {} to {}:{}".format(msg, host, port))
                return False
            except ConnectionRefusedError:
                LOG.error("error connecting to {}:{}".format(host, port))
                return False


"""
parse_hostport transforms a string "host:port" to a tuple of (host:str, port:int)
Example:
    parse_hostport("localhost:12345") -> ("localhost", 12345)
"""


def parse_hostport(hostport_str):
    host, port_str = hostport_str.split(":")
    return host.strip(), int(port_str.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--peers", type=str, nargs="+", default=["localhost:9999"])
    args = parser.parse_args()

    socketserver.TCPServer.allow_reuse_address = True

    peers = list(map(parse_hostport, args.peers))

    p = Process(args.id, peers)
    p.run()


if __name__ == "__main__":
    main()
