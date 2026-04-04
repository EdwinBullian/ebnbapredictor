from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            from lib.tracker import get_history

            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            limit = 60
            if "limit" in params:
                try:
                    limit = int(params["limit"][0])
                except (ValueError, IndexError):
                    pass

            date = None
            if "date" in params:
                date = params["date"][0]

            history = get_history(limit=limit, date=date)
            self._send_json({"history": history, "count": len(history)})

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, format, *args):
        pass
