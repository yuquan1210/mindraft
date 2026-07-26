import argparse
import webbrowser
from pathlib import Path

from filelock import Timeout

from scripts.llm_factory import get_llm
from scripts.utils import load_config, get_process_lock, setup_logging


def main():
    parser = argparse.ArgumentParser(description="Mindraft")
    parser.add_argument("--notes-only", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config()
    logger = setup_logging(config)

    logger.info(f"Mindraft 启动 | dry_run={args.dry_run}")

    if args.serve:
        # Phase 0 仅启动基础占位服务器，后续 Phase 实现完整 Dashboard
        from scripts.serve import start_server

        start_server(config)
        return

    # 获取进程锁，防止并发执行（dry-run 模式下也获取锁，保证并发安全）
    lock = get_process_lock(config["notes_vault_path"])
    try:
        with lock:
            if args.dry_run:
                logger.info("--dry-run 模式：仅验证配置与基础设施，不写入业务状态文件")
                # Phase 0：验证 LLM 抽象层可初始化（不实际调用 API）
                try:
                    llm = get_llm(config)
                    logger.info(f"LLM provider 初始化成功: {type(llm).__name__}")
                except Exception as e:
                    logger.warning(f"LLM provider 初始化失败（可能未设置 API Key）: {e}")
                logger.info("Dry-run 完成")
                return

            if args.analyze:
                from scripts.analyze import generate_dashboard_data
                from scripts.serve import start_server

                generate_dashboard_data(config, dry_run=False)
                start_server(config)
                return

            if args.notes_only:
                from scripts.process_notes import process_new_notes

                process_new_notes(config, dry_run=False)
                return

            # 默认：完整执行
            from scripts.process_notes import process_new_notes
            from scripts.analyze import generate_dashboard_data
            from scripts.serve import start_server

            process_new_notes(config, dry_run=False)
            generate_dashboard_data(config, dry_run=False)
            start_server(config)
            webbrowser.open(f"http://localhost:{config['dashboard_port']}")
    except Timeout:
        logger.error("另一个 Mindraft 实例正在运行，请等待其完成后再试")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
