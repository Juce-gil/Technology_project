import hmac
import json
import select
import socket
import threading


class CommandServer:
    """Authenticated, framed TCP diagnostics/control server.

    Frames end in '#'. RESUME only queues a request; the behavior loop accepts
    it after all sensors are clear for the configured confirmation interval.
    """
    def __init__(self, manager, hal, config, token, host="0.0.0.0", port=8888):
        if not token: raise ValueError("a non-empty TCP token is required")
        self.manager = manager; self.hal = hal; self.config = config
        self.token = token; self.host = host; self.port = port
        self.server = None; self.clients = {}; self.authenticated = set()
        self.running = False; self.thread = None

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port)); self.server.listen(1); self.server.setblocking(False)
        self.running = True; self.thread = threading.Thread(target=self._loop, daemon=True); self.thread.start()
        return self

    def _loop(self):
        while self.running:
            sockets = [self.server] + list(self.clients)
            try: readable, _, exceptional = select.select(sockets, [], sockets, 0.2)
            except (OSError, ValueError): continue
            for sock in exceptional: self._drop(sock)
            for sock in readable:
                if sock is self.server: self._accept()
                else: self._receive(sock)

    def _accept(self):
        try:
            client, _ = self.server.accept(); client.setblocking(False)
            if self.clients: client.sendall(b"$4WD,ERR,busy#"); client.close(); return
            self.clients[client] = bytearray(); client.sendall(b"$4WD,OK,auth-required#")
        except OSError: pass

    def _receive(self, sock):
        try: data = sock.recv(1024)
        except OSError: self._drop(sock); return
        if not data: self._drop(sock); return
        buffer = self.clients[sock]; buffer.extend(data)
        if len(buffer) > self.config.remote.max_buffer: self._drop(sock); return
        while b"#" in buffer:
            raw, _, remaining = buffer.partition(b"#"); buffer[:] = remaining
            response = self.handle(sock, raw.decode("utf-8", "replace") + "#")
            try: sock.sendall(response.encode("utf-8"))
            except OSError: self._drop(sock); return

    def handle(self, client, raw):
        if not raw.startswith("$4WD,") or not raw.endswith("#"): return "$4WD,ERR,format#"
        fields = raw[5:-1].split(","); command = fields[0].upper(); args = fields[1:]
        if command == "AUTH":
            if len(args) == 1 and hmac.compare_digest(args[0], self.token):
                self.authenticated.add(client); return "$4WD,OK,authenticated#"
            return "$4WD,ERR,auth#"
        if client not in self.authenticated: return "$4WD,ERR,unauthorized#"
        try:
            if command == "STOP":
                self.manager.pause("tcp"); return "$4WD,OK,stopped#"
            if command == "RESUME":
                if self.manager.request_resume(): return "$4WD,OK,resume-requested#"
                return "$4WD,ERR,not-waiting-clear#"
            if command == "STATUS":
                body = self.manager.status()
                return "$4WD,OK,{}#".format(json.dumps(body, separators=(",", ":")))
            if command == "SPEED" and len(args) == 1:
                speed = max(0, min(self.config.motor.max_speed, int(args[0])))
                self.config.motor.base_speed = speed; return "$4WD,OK,speed={}#".format(speed)
            if command == "LED" and len(args) == 3:
                values = [max(0, min(255, int(value))) for value in args]
                self.hal.led_set(*values); return "$4WD,OK,led={},{},{}#".format(*values)
        except (TypeError, ValueError): return "$4WD,ERR,argument#"
        return "$4WD,ERR,command#"

    def _drop(self, sock):
        self.authenticated.discard(sock); self.clients.pop(sock, None)
        try: sock.close()
        except OSError: pass

    def close(self):
        self.running = False
        for sock in list(self.clients): self._drop(sock)
        if self.server is not None:
            try: self.server.close()
            except OSError: pass
        if self.thread is not None: self.thread.join(timeout=1.0)
