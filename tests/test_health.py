import json

import pytest

import health
from health import build_health_payload, start_health_server


def test_health_payload_matches_contract():
    payload = build_health_payload()
    assert json.loads(payload) == {"status": "ok"}


def test_start_health_server_uses_http_server(monkeypatch):
    class DummyServer:
        def __init__(self, addr, handler):
            self.server_port = addr[1]
            self.handler = handler

        def serve_forever(self):
            pass

        def shutdown(self):
            pass

    captured = {}

    def fake_http_server(addr, handler):
        captured["handler"] = handler
        return DummyServer(addr, handler)

    monkeypatch.setattr(health, "HTTPServer", fake_http_server)
    server = start_health_server(port=1234)
    assert server.server_port == 1234
    assert "handler" in captured
