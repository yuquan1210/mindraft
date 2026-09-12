"""Local Dashboard server, exposing only UI assets and generated notes."""
import http.server
import logging
import webbrowser
from pathlib import Path
from urllib.parse import unquote, urlsplit

logger = logging.getLogger("mindraft")


def make_handler(config, dashboard_dir):
    dashboard_dir = Path(dashboard_dir).resolve()
    ai_notes_dir = (Path(config["notes_vault_path"]).expanduser() / "ai_notes").resolve()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)

        def translate_path(self, path):
            relative = unquote(urlsplit(path).path).lstrip('/')
            root = ai_notes_dir if relative.startswith('ai_notes/') else dashboard_dir
            if root == ai_notes_dir:
                relative = relative[len('ai_notes/'):]
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                # send_head will treat a non-existent path as 404.
                return str(dashboard_dir / '.forbidden' / 'not-found')
            return str(target)

        def list_directory(self, path):
            self.send_error(404, "Directory listing is disabled")
            return None

        def log_message(self, format, *args):
            logger.info("%s - %s", self.address_string(), format % args)

    return Handler


def start_server(config: dict, open_browser: bool = False):
    dashboard_dir = Path(__file__).parent.parent / "dashboard"
    port = config.get("dashboard_port", 8765)
    handler = make_handler(config, dashboard_dir)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://localhost:{httpd.server_port}"
        logger.info("Dashboard 服务器启动: %s", url)
        if open_browser:
            webbrowser.open(url)
        logger.info("按 Ctrl+C 停止服务器")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("服务器已停止")
