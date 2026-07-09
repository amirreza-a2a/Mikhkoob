import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class BlockerHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/block_rules':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.server.block_rules).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            msg = json.loads(body)
        except:
            self.send_response(400)
            self.end_headers()
            return

        if self.path == '/block_attempt':
            if self.server.on_block_attempt:
                self.server.on_block_attempt(msg.get("url", ""))
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class BlockerExtensionServer:
    def __init__(self, host='127.0.0.1', port=9876):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self.on_block_attempt = None
        # ساختار جدید: دیکشنری با کلیدهای scope ('always','focus','rest')
        self.block_rules = {
            "always": {"domains": [], "paths": {}},
            "focus":  {"domains": [], "paths": {}},
            "rest":   {"domains": [], "paths": {}}
        }

    def start(self):
        if self.running:
            return
        self.running = True
        self.server = HTTPServer((self.host, self.port), BlockerHTTPHandler)
        self.server.block_rules = self.block_rules
        self.server.on_block_attempt = self.on_block_attempt
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def update_block_rules(self, rules_by_scope):
        """
        دریافت قوانین جدید به صورت دیکشنری:
        {
            "always": {"domains": [...], "paths": {...}},
            "focus":  {"domains": [...], "paths": {...}},
            "rest":   {"domains": [...], "paths": {...}}
        }
        """
        self.block_rules = rules_by_scope
        if self.server:
            self.server.block_rules = rules_by_scope

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.running = False