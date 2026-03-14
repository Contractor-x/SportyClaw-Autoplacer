import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8000"))


def build_health_payload() -> bytes:
    return json.dumps({"status": "ok"}).encode("utf-8")


class _HealthRequestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self._send_response()

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404, "Not Found")
            return
        self._send_response()

    def _send_response(self):
        payload = build_health_payload()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # Suppress default logging to keep logs clean.
        logger.debug(format, *args)


def start_health_server(port: int | None = None, bind: bool = True):
    actual_port = port or HEALTH_PORT
    if not bind:
        class _HealthServerStub:
            server_port = actual_port

            def shutdown(self):
                pass

            def serve_forever(self):
                pass

        return _HealthServerStub()

    server = HTTPServer(("0.0.0.0", actual_port), _HealthRequestHandler)
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
        name="health-server",
    )
    thread.start()
    logger.info("Health endpoint running on port %s", server.server_port)
    return server
