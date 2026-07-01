import json
import os
import hashlib
import base64
import secrets
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests

CONFIG_DIR = os.path.expanduser("~/.config/spotfetch")
TOKEN_FILE = os.path.join(CONFIG_DIR, "tokens.json")

DEFAULT_CLIENT_ID = "d9739ff737b348928da15234f91cf697"

SCOPES = "playlist-read-private playlist-read-collaborative user-library-read"
REDIRECT_PORT = 3000
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/"


class SpotifyAuthError(Exception):
    pass


class _AuthHandler(BaseHTTPRequestHandler):
    auth_code = None
    code_verifier = None
    auth_event = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if 'code' in params:
            self._handle_callback(params)
        elif 'error' in params:
            self._handle_callback(params)
        elif parsed.path == '/':
            self._serve_login_page()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_login_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f"""<!DOCTYPE html>
<html>
<head><title>SpotFetch - Spotify Login</title></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; margin-top: 80px; background: #191414; color: white;">
    <div style="max-width: 400px; margin: 0 auto; padding: 40px;">
        <h1 style="font-size: 2em; margin-bottom: 8px;">SpotFetch</h1>
        <p style="color: #b3b3b3; margin-bottom: 32px;">Connect your Spotify account to download playlists</p>
        <a href=\"{self._get_auth_url()}\"
           style="display: inline-block; padding: 14px 32px; background: #1DB954; color: white;
                  text-decoration: none; border-radius: 24px; font-weight: bold; font-size: 16px;">
            Log in with Spotify
        </a>
    </div>
</body>
</html>"""
        self.wfile.write(html.encode())

    def _get_auth_url(self):
        verifier = secrets.token_urlsafe(64)
        _AuthHandler.code_verifier = verifier
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b'=').decode()

        params = {
            'response_type': 'code',
            'client_id': self.server.client_id,
            'scope': SCOPES,
            'redirect_uri': REDIRECT_URI,
            'code_challenge_method': 'S256',
            'code_challenge': challenge,
        }
        return f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"

    def _handle_callback(self, params):
        code = params.get('code', [None])[0]
        error = params.get('error', [None])[0]

        if error:
            self._serve_error_page(f"Authorization denied: {error}")
            if _AuthHandler.auth_event:
                _AuthHandler.auth_event.set()
            return

        if code:
            _AuthHandler.auth_code = code
            if _AuthHandler.auth_event:
                _AuthHandler.auth_event.set()
            self._serve_success_page()
        else:
            self._serve_error_page("No authorization code received")

    def _serve_success_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """<!DOCTYPE html>
<html>
<head><title>Authenticated</title></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; margin-top: 100px; background: #191414; color: white;">
    <div style="max-width: 400px; margin: 0 auto; padding: 40px;">
        <div style="font-size: 48px; margin-bottom: 16px; color: #1DB954;">&#10003;</div>
        <h1 style="font-size: 1.5em;">Authenticated!</h1>
        <p style="color: #b3b3b3;">You can close this window and return to SpotFetch.</p>
    </div>
</body>
</html>"""
        self.wfile.write(html.encode())

    def _serve_error_page(self, message):
        self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f"""<!DOCTYPE html>
<html>
<head><title>Authentication Failed</title></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; margin-top: 100px; background: #191414; color: white;">
    <div style="max-width: 400px; margin: 0 auto; padding: 40px;">
        <div style="font-size: 48px; margin-bottom: 16px; color: #E74C3C;">&#10007;</div>
        <h1 style="font-size: 1.5em;">Authentication Failed</h1>
        <p style="color: #b3b3b3;">{message}</p>
    </div>
</body>
</html>"""
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass


class _AuthServer(HTTPServer):
    def __init__(self, client_id, port=REDIRECT_PORT):
        self.client_id = client_id
        super().__init__(('127.0.0.1', port), _AuthHandler)


class SpotifyAuth:
    def __init__(self, client_id=None):
        self.client_id = client_id or os.environ.get("SPOTIFY_CLIENT_ID") or DEFAULT_CLIENT_ID
        self._token_info = None
        self._load_tokens()

    def _load_tokens(self):
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE) as f:
                    self._token_info = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._token_info = None

    def _save_tokens(self, token_info):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_info, f)
        self._token_info = token_info

    def clear_tokens(self):
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        self._token_info = None

    def is_authenticated(self):
        return self._token_info is not None and 'refresh_token' in self._token_info

    def get_access_token(self):
        if not self.client_id:
            return None
        if self._token_info and 'refresh_token' in self._token_info:
            return self._refresh_access_token()
        return None

    def _refresh_access_token(self):
        resp = requests.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self._token_info['refresh_token'],
                'client_id': self.client_id,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30,
        )
        if resp.ok:
            data = resp.json()
            self._token_info['access_token'] = data['access_token']
            if 'refresh_token' in data:
                self._token_info['refresh_token'] = data['refresh_token']
            self._save_tokens(self._token_info)
            return data['access_token']
        self._token_info = None
        return None

    def authenticate(self):
        if not self.client_id:
            raise SpotifyAuthError(
                "Spotify Client ID not configured. "
                "Set it via environment variable SPOTIFY_CLIENT_ID "
                "or in SpotFetch settings."
            )

        os.makedirs(CONFIG_DIR, exist_ok=True)

        _AuthHandler.auth_code = None
        _AuthHandler.code_verifier = None
        auth_event = threading.Event()
        _AuthHandler.auth_event = auth_event

        try:
            server = _AuthServer(self.client_id)
        except OSError as e:
            raise SpotifyAuthError(
                f"Could not start authentication server on port {REDIRECT_PORT}: {e}\n"
                f"Make sure port {REDIRECT_PORT} is available."
            )

        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        webbrowser.open(f'http://127.0.0.1:{REDIRECT_PORT}/')
        print(f"\nOpening browser for Spotify login...")
        print(f"If the browser doesn't open, visit: http://127.0.0.1:{REDIRECT_PORT}/\n")

        auth_event.wait(timeout=120)

        server.shutdown()
        thread.join(timeout=2)

        if _AuthHandler.auth_code is None:
            raise SpotifyAuthError(
                "Authentication timed out or was denied. Please try again."
            )

        resp = requests.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'authorization_code',
                'code': _AuthHandler.auth_code,
                'redirect_uri': REDIRECT_URI,
                'client_id': self.client_id,
                'code_verifier': _AuthHandler.code_verifier,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30,
        )

        if not resp.ok:
            raise SpotifyAuthError(f"Failed to exchange code for token: {resp.text}")

        token_info = resp.json()
        self._save_tokens(token_info)
        print("Successfully authenticated with Spotify!")
        return token_info['access_token']
