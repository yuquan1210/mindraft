import http.server
import socketserver
import logging
from pathlib import Path

logger = logging.getLogger("mindraft")


def start_server(config: dict):
    """
    启动 Dashboard 本地 HTTP 服务器。
    Phase 0 仅作为占位实现，Phase 2 补充完整前端静态文件服务。
    """
    dashboard_dir = Path(__file__).parent.parent / "dashboard"
    port = config.get("dashboard_port", 8080)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)

        def log_message(self, format, *args):
            logger.info("%s - %s" % (self.address_string(), format % args))

    logger.info(f"Dashboard 占位服务器启动: http://localhost:{port}")
    logger.info(f"服务目录: {dashboard_dir}")

    # Phase 0 不实际阻塞启动服务器，仅打印日志便于验收
    # Phase 2 替换为实际 socketserver.TCPServer
    with socketserver.TCPServer(("", port), Handler) as httpd:
        logger.info("按 Ctrl+C 停止服务器")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("服务器已停止")
