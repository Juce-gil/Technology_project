#!/usr/bin/env python3
import argparse
import atexit
import collections
import hmac
import html
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from base64 import b64decode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CarProcess:
    def __init__(self):
        self.process = None
        self.logs = collections.deque(maxlen=300)
        self.lock = threading.RLock()
        self.control_token = secrets.token_urlsafe(24)

    @staticmethod
    def command(line_source, motor_backend, arduino_port="/dev/ttyACM0"):
        if line_source not in ("ir", "camera"):
            raise ValueError("无效循迹模式")
        if motor_backend not in ("gpio", "arduino"):
            raise ValueError("无效电机后端")
        command = [sys.executable, "-u", os.path.join(PROJECT_ROOT, "main.py"),
                   "--line-source", line_source, "--motor-backend", motor_backend,
                   "--tcp", "--tcp-host", "127.0.0.1"]
        if motor_backend == "arduino":
            command.extend(("--arduino-port", arduino_port))
        return command

    def legacy_running(self):
        result = subprocess.run(
            ["pgrep", "-f", "^./bluetooth_control$"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False)
        return result.returncode == 0

    def stop_legacy(self):
        result = subprocess.run(
            ["pkill", "-TERM", "-f", "^./bluetooth_control$"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False)
        if result.returncode not in (0, 1):
            raise RuntimeError("停止原厂控制程序失败")
        self._log("已停止原厂 bluetooth_control")

    def start(self, line_source, motor_backend, arduino_port, confirmed):
        if not confirmed:
            raise RuntimeError("请先确认轮子已架空且周围安全")
        with self.lock:
            if self.running():
                raise RuntimeError("SmartCarV2 已经在运行")
            if self.legacy_running():
                raise RuntimeError("原厂 bluetooth_control 仍在运行，请先停止")
            command = self.command(line_source, motor_backend, arduino_port)
            command.extend(("--tcp-token", self.control_token))
            env = os.environ.copy()
            env["PYTHONPATH"] = PROJECT_ROOT
            self.process = subprocess.Popen(
                command, cwd=PROJECT_ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, bufsize=1, start_new_session=True)
            self._log("启动：{}".format(" ".join(command[:-2]) + " --tcp-token <内部令牌>"))
            threading.Thread(target=self._read_output, daemon=True).start()

    def running(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        with self.lock:
            if not self.running():
                self.process = None
                return
            process = self.process
            self._log("正在安全停止 SmartCarV2")
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGINT)
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired: os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            finally:
                self.process = None
                self._log("SmartCarV2 已停止")

    def control(self, command):
        if not self.running():
            raise RuntimeError("SmartCarV2 未运行")
        try:
            with socket.create_connection(("127.0.0.1", 8888), timeout=1.0) as sock:
                self._recv_frame(sock)
                sock.sendall(("$4WD,AUTH,{}#".format(self.control_token)).encode("utf-8"))
                auth = self._recv_frame(sock)
                if ",OK,authenticated#" not in auth: raise RuntimeError("内部认证失败")
                sock.sendall(("$4WD,{}#".format(command)).encode("utf-8"))
                return self._recv_frame(sock)
        except OSError as exc:
            raise RuntimeError("控制端口尚未就绪：{}".format(exc))

    def snapshot(self):
        result = {"running": self.running(), "legacy_running": self.legacy_running(),
                  "logs": list(self.logs)[-80:]}
        if result["running"]:
            try:
                response = self.control("STATUS")
                prefix = "$4WD,OK,"
                if response.startswith(prefix) and response.endswith("#"):
                    result["car"] = json.loads(response[len(prefix):-1])
            except (RuntimeError, ValueError) as exc:
                result["status_error"] = str(exc)
        return result

    def _read_output(self):
        process = self.process
        if process is None or process.stdout is None: return
        for line in process.stdout:
            self._log(line.rstrip())
        code = process.poll()
        self._log("控制进程退出，返回码 {}".format(code))

    def _log(self, message):
        stamp = time.strftime("%H:%M:%S")
        with self.lock: self.logs.append("{}  {}".format(stamp, message))

    @staticmethod
    def _recv_frame(sock):
        data = bytearray()
        while b"#" not in data:
            block = sock.recv(1024)
            if not block: break
            data.extend(block)
            if len(data) > 8192: raise RuntimeError("控制响应过长")
        return data.decode("utf-8", "replace")


PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SmartCarV2 控制面板</title>
<style>
body{font-family:system-ui,"Microsoft YaHei",sans-serif;margin:0;background:#f3f6f8;color:#17212b}
main{max-width:920px;margin:24px auto;padding:0 16px}.card{background:white;border-radius:12px;padding:20px;margin:14px 0;box-shadow:0 2px 10px #0001}
h1{font-size:25px}h2{font-size:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
label{display:block;margin:8px 0}select,input[type=text]{width:100%;box-sizing:border-box;padding:9px;border:1px solid #bbc6ce;border-radius:7px}
button{padding:10px 16px;border:0;border-radius:7px;background:#24689b;color:white;font-weight:600;margin:5px 5px 5px 0;cursor:pointer}
button.stop{background:#a33232}button.warn{background:#9a6700}.status{font-weight:700}.ok{color:#237447}.bad{color:#a33232}
pre{background:#101820;color:#d9e4ec;padding:14px;border-radius:8px;min-height:180px;max-height:390px;overflow:auto;white-space:pre-wrap}
.note{color:#52606b;font-size:14px}.message{color:#a33232;font-weight:600}
</style></head><body><main>
<h1>SmartCarV2 控制面板</h1>
<div class="card"><h2>运行状态</h2><div id="status">正在读取...</div></div>
<div class="card"><h2>启动设置</h2>
<form method="post" action="/action">
<input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="action" value="start">
<div class="grid"><label>循迹方式<select name="line_source"><option value="ir">四路红外</option><option value="camera">摄像头</option></select></label>
<label>电机后端<select name="motor_backend"><option value="gpio">树莓派 GPIO</option><option value="arduino">Arduino 串口</option></select></label>
<label>Arduino 端口<input name="arduino_port" value="/dev/ttyACM0"></label></div>
<label><input type="checkbox" name="confirmed" value="yes"> 我确认轮子已架空，周围无人和障碍，可随时断电</label>
<button type="submit">启动循迹</button></form>
<form method="post" action="/action" style="display:inline"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="action" value="stop"><button class="stop">安全停止</button></form>
<form method="post" action="/action" style="display:inline"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="action" value="pause"><button class="warn">暂停</button></form>
<form method="post" action="/action" style="display:inline"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="action" value="resume"><button>请求恢复</button></form>
<form method="post" action="/action" style="display:inline"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="action" value="legacy-stop"><button class="warn">停止原厂控制程序</button></form>
<p class="note">请求恢复不能绕过障碍、稳定清除时间或 FAULT。摄像头当前尚未完成硬件恢复，优先使用四路红外模式。</p>{message}</div>
<div class="card"><h2>运行日志</h2><pre id="logs">暂无日志</pre></div>
</main><script>
async function refresh(){try{const r=await fetch('/api/status');const d=await r.json();
const state=d.car&&d.car.state?d.car.state:'不可用';document.getElementById('status').innerHTML=
'SmartCarV2：<span class="'+(d.running?'ok':'bad')+'">'+(d.running?'运行中':'已停止')+'</span>　'+
'原厂程序：<span class="'+(d.legacy_running?'bad':'ok')+'">'+(d.legacy_running?'运行中':'已停止')+'</span>　状态：'+state+
(d.status_error?'　'+d.status_error:'');document.getElementById('logs').textContent=(d.logs||[]).join('\n')||'暂无日志';}
catch(e){document.getElementById('status').textContent='状态读取失败：'+e}}refresh();setInterval(refresh,1000);
</script></body></html>"""


class PanelHandler(BaseHTTPRequestHandler):
    server_version = "SmartCarPanel/1.0"

    def authenticated(self):
        value = self.headers.get("Authorization", "")
        try:
            scheme, encoded = value.split(" ", 1)
            user_pass = b64decode(encoded).decode("utf-8")
            user, password = user_pass.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return scheme.lower() == "basic" and user == "smartcar" and hmac.compare_digest(password, self.server.panel_token)

    def require_auth(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="SmartCarV2"')
        self.end_headers()

    def do_GET(self):
        if not self.authenticated(): return self.require_auth()
        if self.path == "/api/status":
            return self.send_json(self.server.car.snapshot())
        if self.path != "/": return self.send_error(404)
        self.send_page("")

    def do_POST(self):
        if not self.authenticated(): return self.require_auth()
        if self.path != "/action": return self.send_error(404)
        length = min(int(self.headers.get("Content-Length", "0")), 4096)
        form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        if not hmac.compare_digest(form.get("csrf", [""])[0], self.server.csrf):
            return self.send_error(403, "请求校验失败")
        action = form.get("action", [""])[0]
        try:
            if action == "start":
                self.server.car.start(form.get("line_source", ["ir"])[0],
                                      form.get("motor_backend", ["gpio"])[0],
                                      form.get("arduino_port", ["/dev/ttyACM0"])[0],
                                      form.get("confirmed", [""])[0] == "yes")
            elif action == "stop": self.server.car.stop()
            elif action == "pause": self.server.car.control("STOP")
            elif action == "resume": self.server.car.control("RESUME")
            elif action == "legacy-stop": self.server.car.stop_legacy()
            else: raise RuntimeError("未知操作")
            message = "操作已提交"
        except (RuntimeError, ValueError) as exc:
            message = str(exc)
        self.send_page(message)

    def send_page(self, message):
        message_html = '<p class="message">{}</p>'.format(html.escape(message)) if message else ""
        body = PAGE.replace("{csrf}", html.escape(self.server.csrf)).replace(
            "{message}", message_html).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def send_json(self, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def log_message(self, format_, *args):
        return


def parse_args():
    parser = argparse.ArgumentParser(description="SmartCarV2 中文网页控制面板")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--token", default=os.environ.get("SMARTCAR_PANEL_TOKEN"))
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.token: raise SystemExit("请通过 --token 或 SMARTCAR_PANEL_TOKEN 设置面板密码")
    car = CarProcess(); atexit.register(car.stop)
    server = ThreadingHTTPServer((args.host, args.port), PanelHandler)
    server.car = car; server.panel_token = args.token; server.csrf = secrets.token_urlsafe(24)
    print("控制面板：http://{}:{}  用户名：smartcar".format(args.host, args.port))
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close(); car.stop()
    return 0


if __name__ == "__main__": raise SystemExit(main())
