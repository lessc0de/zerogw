import zmq
import time
import json
from .simple import (Base, CheckingWebsock, TimeoutError,
    CHAT_FW, CHAT_SOCK, START_TIMEOUT,
    )

CONFIG="./test/tworoutes.yaml"

class TwoRoutes(Base):
    timeout = 1
    config = CONFIG

    def do_init(self):
        self.zmq = zmq.Context(1)
        super().do_init()
        self.chatfw = self.zmq.socket(zmq.PULL)
        self.chatfw.connect(CHAT_FW)
        self.chatout = self.zmq.socket(zmq.PUB)
        self.chatout.connect(CHAT_SOCK)
        self.chatout.connect(CHAT_SOCK + '1')
        time.sleep(START_TIMEOUT)  # sorry, need for zmq sockets

    def backend_send(self, *args):
        self.assertEqual(([], [self.chatout], []),
            zmq.select([], [self.chatout], [], timeout=self.timeout))
        self.chatout.send_multipart([
            a if isinstance(a, bytes) else a.encode('utf-8')
            for a in args])

    def backend_recv(self, backend=None):
        if backend is None:
            sock = self.chatfw
        else:
            raise NotImplementedError(backend)
        if (([sock], [], []) !=
            zmq.select([sock], [], [], timeout=self.timeout)):
            raise TimeoutError()
        val =  sock.recv_multipart()
        if val[1] == b'heartbeat':
            return self.backend_recv(backend=backend)
        return val

    def testDuplicate(self):
        ws = self.websock()
        ws.connect()
        ws.subscribe('chat')
        self.backend_send('publish', 'chat', 'message: hello_world')
        ws.client_got('message: hello_world')
        self.backend_send('publish', 'chat', 'message: another_hello')
        ws.client_got('message: another_hello')
        ws.close()