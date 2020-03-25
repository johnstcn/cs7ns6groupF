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
WHOISLEADER = b"ldr?"

ACK = b"ack"
NACK = b"nack"

CLIENT_TIMEOUT = 1


class Process(object):
    """
    Process represents one leader-elected process. It has an ID and knows about a number of peers.
    In its initial state:
    - it is not leader
    - it does not know who the leader is
    - it is not in the process of electing a new leader
    """

    def __init__(self, id, peers):
        self.id = id
        self.peers = peers
        self.election = False
        self.leader_id = None
        self.multicaster = Multicaster()

    def am_leader(self):
        """
        am_leader returns True if a leader ID is known and the leader ID is my own ID.
        Otherwise, returns False.
        """
        if self.leader_id is None:
            return False
        return self.leader_id == self.id

    def handle_request_vote(self, *args):
        """
        handle_request_vote is the callback function invoked when someone requests a leader election.
        """
        if self.election:
            LOG.error("already doing an election!")
            return NACK

        LOG.info("doing an election")
        thread = threading.Thread(target=self.perform_election)
        thread.daemon = True
        thread.start()
        return ACK

    def handle_request_healthcheck(self, *args):
        """
        handle_request_healthcheck is the callback function invoked when someone asks if we are alive.
        """
        return ACK

    def handle_request_victory(self, *args):
        """
        handle_request_victory is the callback function invoked when a leader is elected
        """
        victor = int(args[0])
        if victor < self.id:
            return NACK  # do not acknowledge leadership of filthy peasants

        self.leader_id = victor
        return ACK

    def handle_request_leader(self, *args):
        """
        handle_request_leader is the callback function invoked when someone asks who the leader is
        """
        if self.leader_id is None:
            return None
        return ("%s:%d" % self.peers[self.leader_id]).encode("utf-8")

    def perform_election(self):
        """
        perform_election is invoked when we want to perform leader election 
        """
        if self.election:
            return
        self.election = True
        # optimistically assume that we can be the leader initially
        can_be_leader = True
        try:
            # notify all peers with a higher id
            notify_peers = self.peers[self.id + 1 :]
            if not notify_peers:
                # it's up to us to take the mantle
                return

            acked = self.multicaster.multisend(ELECTION, notify_peers)
            if acked:
                can_be_leader = False
        finally:
            if can_be_leader:
                self.assume_leadership()
            self.election = False

    def assume_leadership(self):
        """
        assume_leadership is invoked when we determine we may be the leader
        """

        msg = VICTORY + b" %d" % self.id
        other_peers = self.peers[: self.id] + self.peers[self.id + 1 :]
        acked = self.multicaster.multisend(msg, other_peers)
        if not acked:
            LOG.warn("not all peers acknowledged, not asssuming leadership")
        else:
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


class Handler(socketserver.BaseRequestHandler):
    """
    Handler handles incoming messages and calls its relevant callback function.
    """

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
    """
    Multicaster handles sending messages to multiple peers simultaneously.
    """

    def multisend(self, msg, peers):
        """
        multisend sends msg to all peers simultaneously
        """
        tasks = []
        for peer in peers:
            tasks.append(self.asend(msg, peer))

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(asyncio.gather(*tasks))
            if isinstance(results, list):
                return results
            else:
                return [results]
        finally:
            loop.stop()

    async def asend(self, msg, peer):
        """
        asend is an async wrapper for send.
        """
        return self.send(msg, peer)

    def send(self, msg, peer):
        """
        send sends msg to peer
        """
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


def parse_hostport(hostport_str):
    """
    parse_hostport transforms a string "host:port" to a tuple of (host:str, port:int)
    Example:
        parse_hostport("localhost:12345") -> ("localhost", 12345)
    """

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
