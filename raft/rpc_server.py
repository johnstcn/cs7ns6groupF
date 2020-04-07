#!/usr/bin/env python
import logging
import socketserver
import threading
from typing import Dict, Callable, Tuple, Optional

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class RpcServer(object):
    def __init__(self, host: str, port: int, handlers: Dict[bytes, Callable]):
        LOG.debug("RpcServer init host:%s port%d", host, port)
        self._host = host
        self._port = port
        self._handlers = handlers
        self._server = None

    def start(self):
        LOG.debug("RpcServer start")
        if self._server is not None:
            raise RuntimeError('RpcServer already running on %s:%d' % (self._host, self._port))

        factory = RpcServer._Dispatcher.factory(self._handlers)
        self._server = socketserver.TCPServer((self._host, self._port), factory)
        thread = threading.Thread(target=self._server.serve_forever)
        thread.daemon = True
        thread.start()

    def stop(self):
        LOG.debug("RpcServer stop")
        if self._server is None:
            return

        self._server.server_close()
        self._server = None

    def hostport(self) -> Tuple[Optional[str], Optional[int]]:
        if self._server is None:
            return None, None

        return self._server.server_address

    class _Dispatcher(socketserver.BaseRequestHandler):
        """
        Dispatcher is a BaseRequestHandler that knows how to dispatch stuff to its handlers.
        Meant to be an inner class of RpcServer.
        """

        def __init__(self, request, client_address, server, handlers):
            self._handlers = handlers
            super().__init__(request, client_address, server)

        def handle(self):
            data: bytes = self.request.recv(1024).strip()
            # protocol looks like this:
            # VERB arg1 arg2 arg3... argn
            verb, rest = data.split(b' ', maxsplit=1)
            resp = self._handlers[verb](rest.strip())
            self.request.sendall(resp)

        @classmethod
        def factory(cls, handlers):
            """
            This is what socketserver.TCPServer gets passed in its constructor.
            :param handlers: a dict of verb -> handler function
            :return: a function that returns an instance of a Dispatcher when called.
            """

            def _create_handler(request, client_address, server):
                cls(request, client_address, server, handlers)

            return _create_handler
