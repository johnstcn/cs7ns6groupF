#!/usr/bin/env python3

import argparse
import logging
import socket
import socketserver
import threading

LOG = logging.getLogger(logging.basicConfig())
LOG.setLevel(logging.DEBUG)

ELECTION    = b"vote"
HEALTHCHECK = b"ruok"
ALIVE       = b"imok"
VICTORY     = b"vctr"
OK          = b"ok"

CLIENT_TIMEOUT = 1

def send_message(msg, host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(CLIENT_TIMEOUT)
        try:
            s.connect((host, port))
            s.sendall(msg)
            LOG.info("sent {} to {}:{}".format(msg, host, port))
            resp = s.recv(1024)
            return resp
        except socket.timeout:
            LOG.info("timeout sending {} to {}:{}".format(msg, host, port))
            return None
    

class Process(object):
    def __init__(self, id, peers):
        self.id = id
        self.peers = peers
        self.election = False
        self.leader_id = None


    def am_leader(self):
        if self.leader_id is None:
            return False
        return self.leader_id == self.id


    def handle_request_vote(self, *args):
        if self.election:
            LOG.error("already doing an election!")
            return OK

        self.election = True
        LOG.info("doing an election")
        thread = threading.Thread(target=self.do_election)
        thread.daemon = True
        thread.start()
        return OK


    def handle_request_healthcheck(self, *args):
        return ALIVE


    def handle_request_victory(self, *args):
        self.leader_id = int(args[0])
        return OK


    def do_election(self):
        try:
            # notify all peers with a higher id
            notify_peers = self.peers[self.id+1:]
            if not notify_peers:
                # we are the leader! declare victory!
                for (hostid, (host, port)) in enumerate(self.peers):
                    if hostid == self.id:
                        continue
                    resp = send_message(VICTORY + b' %d' % self.id, host, port)
                    if resp == OK:
                        LOG.info("{}:{} acknowledged our leadership".format(host, port))
            
            # pass it on
            for host, port in notify_peers:
                resp = send_message(ELECTION, host, port)
                if resp == OK:
                    LOG.info("{}:{} acknowledged our election request".format(host, port))
        finally:
            self.election = False


    def run(self):
        callbacks = {
            ELECTION: self.handle_request_vote,
            HEALTHCHECK: self.handle_request_healthcheck,
            VICTORY: self.handle_request_victory,
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
    def __init__(self, callbacks):
        self.callbacks = callbacks
    
    def __call__(self, request, client_address, server):
        h = Handler(self.callbacks)
        socketserver.BaseRequestHandler.__init__(h, request, client_address, server)

    def handle(self):
        msg = self.request.recv(1024).strip()
        LOG.info("got {} from {}:{}".format(msg, *self.client_address))
        if not msg:
            return
        
        verb = msg.split(b' ')[0]
        args = msg.split(b' ')[1:]
        cbfunc = self.callbacks[verb]
        resp = cbfunc(*args)
        self.request.sendall(resp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--peers", type=str, nargs="+", default=["localhost:9999"])
    args = parser.parse_args()

    socketserver.TCPServer.allow_reuse_address = True

    hostport = lambda s : (s.split(":")[0], int(s.split(":")[1]))

    peers = list(map(hostport, args.peers))

    p = Process(args.id, peers)
    p.run()
