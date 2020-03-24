#!/usr/bin/env python3

import argparse
import logging
import socketserver

LOG = logging.getLogger(logging.basicConfig())
LOG.setLevel(logging.DEBUG)

ELECTION    = b"vote"
HEALTHCHECK = b"ruok"
ALIVE       = b"imok"
VICTORY     = b"woot"
OK          = b"ok"

class Process(object):
    def __init__(self, id, peers):
        self.id = id
        self.peers = peers
        self.election = False

    @property
    def get_id(self):
        return self.id

    @property
    def get_peers(self):
        return list(self.peers)

    @property
    def is_election(self):
        return self.election

    def do_election(self):
        if self.is_election:
            LOG.error("already doing an election!")
            return

        self.election = True
        LOG.info("doing an election")
        return OK

    def do_healthcheck(self):
        return ALIVE

    def run(self):
        callbacks = {
            ELECTION: self.do_election,
            HEALTHCHECK: self.do_healthcheck,
        }
        hostport = self.peers[self.id]
        with socketserver.TCPServer(hostport, Handler(callbacks)) as server:
            try:
                LOG.info("listening on %s:%d" % hostport)
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
            LOG.info("got %s from %s:%d" % (msg, self.client_address[0], self.client_address[1]))
            resp = self.callbacks[msg]()
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
