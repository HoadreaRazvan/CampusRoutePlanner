"""Small local web server for the GUI (standard library only). Listens on 127.0.0.1 only."""
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from src.gui import api
from src.io import InputValidationError
from src.search.heuristics import DEFAULT_V_MAX

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY = 5 * 1024 * 1024


def make_handler(registry: api.Registry):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CampusRoutePlanner"

        def log_message(self, format, *args):  # keep the terminal quiet
            pass

        def do_GET(self):
            url = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/api/datasets":
                return self.respond(lambda: {"datasets": api.list_datasets(registry)})
            if url.path == "/api/graph":
                return self.respond(lambda: api.graph_payload(
                    registry, query.get("id", ""), float(query.get("vmax", DEFAULT_V_MAX))))
            return self.static(url.path)

        def do_POST(self):
            url = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self.send_json({"error": "request too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self.send_json({"error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)

            if url.path == "/api/solve":
                return self.respond(lambda: api.solve_payload(
                    registry, body.get("id", ""), body.get("start", ""), body.get("goal", ""),
                    body.get("required"), body.get("blocked") or [], float(body.get("vmax", DEFAULT_V_MAX))))
            if url.path == "/api/open":
                return self.respond(lambda: {"id": registry.add_folder(body.get("path", ""))})
            if url.path == "/api/upload":
                return self.respond(lambda: {"id": registry.add_upload(body.get("name", ""), body.get("files") or {})})
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def respond(self, produce):
            try:
                self.send_json(produce())
            except InputValidationError as err:
                self.send_json({"error": str(err), "code": err.code}, HTTPStatus.BAD_REQUEST)
            except (ValueError, TypeError) as err:
                self.send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)

        def static(self, path: str):
            relative = "index.html" if path in ("", "/") else path.lstrip("/")
            target = (STATIC_DIR / relative).resolve()
            if STATIC_DIR not in target.parents or not target.is_file():
                return self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            data = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", (mimetypes.guess_type(target.name)[0] or "application/octet-stream")
                             + ("; charset=utf-8" if target.suffix in (".html", ".css", ".js") else ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, payload, status: HTTPStatus = HTTPStatus.OK):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def create_server(port: int = 8765, registry: Optional[api.Registry] = None, tries: int = 20) -> ThreadingHTTPServer:
    """Binds to 127.0.0.1, trying the next ports if `port` is busy. Port 0 picks any free port."""
    registry = registry or api.Registry()
    handler = make_handler(registry)
    last_error: Optional[OSError] = None
    for candidate in ([0] if port == 0 else range(port, port + tries)):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), handler)
            server.registry = registry
            return server
        except OSError as err:
            last_error = err
    raise OSError(f"no free port between {port} and {port + tries - 1}") from last_error
