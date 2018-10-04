import usocket as socket
import json
import time
import urandom
import select

boot_time = time.time()

class BlipBusMessage(object):
    def __init__(self, name, addr=None, port=None, raw=None, bus=None):
        self.raw = raw
        self.bus = bus
        self.addr = addr
        self.port = port
        self.fields = {"event": name}
        if raw is not None:
            self.fields.update(raw)
                
    def serialise(self):
        return json.dumps(self.fields)

    def reply(self, msg):
        self.bus.send(msg, addr=self.addr, port=self.port)

    def __repr__(self):
        return "<BlipBusMessage %s>" % self.fields

def handle_ping(msg):
    response = BlipBusMessage("blipbus.pong")
    response.fields['uptime'] = time.time() - boot_time
    msg.reply(response)

class BlipBus(object):
    def __init__(self, name, port=3333):
        self._name = name
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._port = port
        self._sock.bind(("", port))
        self._poller = select.poll()
        self._poller.register(self._sock, select.POLLIN)

        self.handlers = {}

        self.on("blipbus.ping", handle_ping)

    def on(self, spec, fn):
        self.handlers[spec] = fn

    def handle(self):
        while True:
            res = self._poller.poll(0)
            if not res:
                break

            payload, (addr, port) = self._sock.recvfrom(1500)
            #print(addr, port)
            evt = json.loads(payload)
            #print(evt)

            for spec, fn in self.handlers.items():
                if evt['event'] == spec or spec == "*":
                    msg = BlipBusMessage(evt['event'], raw=evt, bus=self, addr=addr, port=port)
                    fn(msg)

    def send(self, msg, addr="255.255.255.255", port=None):
        msg.fields['src'] = self._name
        raw = msg.serialise()
        if port is None:
            port = self._port
        numbytes = self._sock.sendto(raw, (addr, port))
        #print("sent %d bytes '%s' to %s:%d" % (numbytes, raw, addr, port))

