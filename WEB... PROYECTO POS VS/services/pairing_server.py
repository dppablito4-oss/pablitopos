from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import urllib.parse
from typing import Optional

# This module implements a tiny HTTP API that delegates to the running
# `App` instance. It intentionally has no external dependencies so it
# can run offline on the desktop and be reachable from the mobile app
# when both devices are on the same LAN (or via USB tethering).


class _Handler(BaseHTTPRequestHandler):
    # App instance will be injected when server starts
    APP_REF = None

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/guardian/mobile-lock":
            app = _Handler.APP_REF
            if not app or not getattr(app, "storage_guard", None):
                self._send_json(503, {"error": "Service unavailable"})
                return
            guard = app.storage_guard
            try:
                with open(guard.mobile_lock_path, "rb") as fh:
                    data = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as exc:
                self._send_json(404, {"error": f"mobile lock not found: {exc}"})
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/guardian/pair/confirm":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
            except Exception:
                self._send_json(400, {"error": "invalid json payload"})
                return

            pairing_id = payload.get("pairing_id")
            otp = payload.get("otp")
            app = _Handler.APP_REF
            if not app:
                self._send_json(503, {"error": "Service unavailable"})
                return

            try:
                # Reuse app verification logic; it raises StorageGuardianError
                unlock = app._verify_pairing_code(app.storage_guard, pairing_id, otp)
            except Exception as exc:
                self._send_json(400, {"success": False, "error": str(exc)})
                return

            # success
            # Notify the app UI (if it supports it) so an open QR dialog can
            # be auto-filled and submitted. The app will use `after` to ensure
            # safe Tk interaction.
            try:
                notify = getattr(app, "_notify_pairing_confirmed", None)
                if callable(notify):
                    try:
                        notify(pairing_id, otp)
                    except Exception:
                        pass
            except Exception:
                pass

            self._send_json(200, {"success": True, "fingerprint": getattr(app, "_storage_new_fingerprint", None)})
            return

        elif parsed.path == "/guardian/recover/confirm":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
            except Exception:
                self._send_json(400, {"error": "invalid json payload"})
                return

            challenge = payload.get("challenge")
            response = payload.get("response")
            app = _Handler.APP_REF
            if not app:
                self._send_json(503, {"error": "Service unavailable"})
                return

            # Verify response using app's logic
            try:
                if app.settings_service.verify_master_response(challenge, response):
                    # Success
                    # Notify UI to auto-complete
                    print(f"[SERVER] Codigo valido. Notificando a la App... (Challenge: {challenge})")
                    try:
                        notify = getattr(app, "_notify_recovery_confirmed", None)
                        if callable(notify):
                            notify(challenge, response)
                        else:
                            print("[SERVER] ERROR: _notify_recovery_confirmed no es callable o no existe")
                    except Exception as e:
                        print(f"[SERVER] EXCEPCION al notificar UI: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    self._send_json(200, {"success": True})
                else:
                    self._send_json(400, {"success": False, "error": "Invalid response code"})
            except Exception as exc:
                self._send_json(400, {"success": False, "error": str(exc)})
            return

        self._send_json(404, {"error": "Not found"})


class PairingServer:
    def __init__(self, app_instance, host: str = "127.0.0.1", port: int = 51820):
        self.app = app_instance
        self.host = host
        self.port = port
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        _Handler.APP_REF = self.app
        server = HTTPServer((self.host, self.port), _Handler)
        self._httpd = server

        def _run():
            try:
                server.serve_forever()
            except Exception:
                pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self._thread = t

    def stop(self):
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            self._httpd = None
        if self._thread:
            self._thread = None


__all__ = ["PairingServer"]
