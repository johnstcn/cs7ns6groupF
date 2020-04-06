#!/usr/bin/env python3

import argparse
import asyncio
import logging
import socket
import socketserver
import threading
from db_operation import *


LOG = logging.getLogger(logging.basicConfig())
LOG.setLevel(logging.DEBUG)

ELECTION = b"vote"
HEALTHCHECK = b"ok?"
VICTORY = b"vctr"
WHOISLEADER = b"ldr?"
TRANSACTION = b"action"

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

    def __init__(self, id, peers, qw=3, qr=1):
        self.id = id
        self.peers = peers
        self.election = False
        self.leader_id = None
        self.multicaster = Multicaster()
        self.qw = qw
        self.qr = qr

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

            responses = self.multicaster.multisend(ELECTION, notify_peers)
            if any(e is not None and e == ACK for e in responses):
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
        responses = self.multicaster.multisend(msg, other_peers)
        LOG.debug("assume_leadership: responses: %s", responses)
        num_acked = len(list(filter(lambda r: r is not None and r == ACK, responses)))
        num_required = self.qw - 1
        if num_acked < num_required:
            LOG.warning("insufficient peers acked (wanted %d, got %d): not asssuming leadership", num_required, num_acked)
        else:
            self.leader_id = self.id


    def handle_room_update_message(self, room):
        """
        handle_room_update_message handles the message from other peers. Should implement 2-phase protocol.
         - Check if leader; True --> Start 2 phase protocol
                            False --> do nothing.
        :param room: Message from other peers. Assumed to be room number for now.
        """
        LOG.info("Update on Room %d", int(room))
        # Insert Database update operation here.
        try:
            # db = get_db()
            check = update(int(room))  #Currently not working..
            # check = 1   #Placeholder
            if check == 1:
                successful = True
            if successful:
                LOG.info("Made successful update on room %d", int(room))
                return ACK
            else:
                LOG.info("Unsuccessful update on room %d", int(room))
                return NACK

        except Exception as e:
            LOG.error("got exception: " + str(e))

    def run(self):
        callbacks = {
            ELECTION: self.handle_request_vote,
            HEALTHCHECK: self.handle_request_healthcheck,
            VICTORY: self.handle_request_victory,
            WHOISLEADER: self.handle_request_leader,
            TRANSACTION: self.handle_room_update_message,
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
                return resp
            except socket.timeout:
                LOG.error("timeout sending {} to {}:{}".format(msg, host, port))
                return None
            except ConnectionRefusedError:
                LOG.error("error connecting to {}:{}".format(host, port))
                return None


def parse_hostport(hostport_str):
    """
    parse_hostport transforms a string "host:port" to a tuple of (host:str, port:int)
    Example:
        parse_hostport("localhost:12345") -> ("localhost", 12345)
    """

    host, port_str = hostport_str.split(":")
    return host.strip(), int(port_str.strip())


def main():
    desc = '''
module for inter-process communication and leader election.
Sample usage follows:
    # launch one instance binding to localhost:9990 (peers[0])
    $ booking/ipc.py --id 0 --peers localhost:9990 localhost:9991 &
    [1] 5313
    INFO:root:listening on localhost:9990
    # launch another process bindding to localhost:9991 (peers[1])
    $ booking/ipc.py --id 1 --peers localhost:9990 localhost:9991 &
    [2] 5476
    INFO:root:listening on localhost:9991
    # if we ask 0 who the leader is, it doesn't know
    $ echo 'ldr?' | nc localhost 9990
    DEBUG:root:got b'ldr?' from 127.0.0.1:48960
    # we can ask 0 to initiate an election
    $ echo 'vote' | nc localhost 9990
    DEBUG:root:got b'vote' from 127.0.0.1:48966
    INFO:root:doing an election
    ackDEBUG:asyncio:Using selector: EpollSelector
    # 0 asks 1 to vote
    DEBUG:root:sent b'vote' to localhost:9991
    DEBUG:root:got b'vote' from 127.0.0.1:47098
    # 1 initiates an election
    INFO:root:doing an election
    DEBUG:root:got b'ack' from localhost:9991
    DEBUG:asyncio:Using selector: EpollSelector
    # 1 has no higher peer so declares itself victor
    DEBUG:root:sent b'vctr 1' to localhost:9990
    DEBUG:root:got b'vctr 1' from 127.0.0.1:48970
    DEBUG:root:got b'ack' from localhost:9990
    # now 0 knows who the leader is
    $ echo 'ldr?' | nc localhost 9990
    DEBUG:root:got b'ldr?' from 127.0.0.1:48972
    localhost:9991
    '''
    parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--peers", type=str, nargs="+", default=["localhost:9999"])
    parser.add_argument("--quorum_write", type=int, default=3)
    parser.add_argument("--quorum_read", type=int, default=1)
    args = parser.parse_args()

    socketserver.TCPServer.allow_reuse_address = True

    peers = list(map(parse_hostport, args.peers))

    p = Process(args.id, peers, args.quorum_write, args.quorum_read)
    p.run()


if __name__ == "__main__":
    main()
