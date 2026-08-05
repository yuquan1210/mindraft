# scripts/serve.py
import http.server
import socketserver
import logging
import webbrowser
from pathlib import Path

logger = logging.getLogger("mindraft")


def start_server(config: dict, open_browser: bool = False):
    """
    启动 Dashboard 本地 HTTP 服务器。

    Args:
        config: 加载后的 config.yml 配置。
        open_browser: 为 True 时自动打开系统默认浏览器。
    """
    dashboard_dir = Path(__file__).parent.parent / "dashboard"
    port = config.get("dashboard_port", 8080)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)

        def log_message(self, format, *args):
            logger.info("%s - %s" % (self.address_string(), format % args))

    logger.info(f"Dashboard 服务器启动: http://localhost:{port}")
    logger.info(f"服务目录: {dashboard_dir}")

    if open_browser:
        url = f"http://localhost:{port}"
        logger.info(f"正在打开浏览器: {url}")
        webbrowser.open(url)

    with socketserver.TCPServer(("", port), Handler) as httpd:
        logger.info("按 Ctrl+C 停止服务器")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("服务器已停止")
