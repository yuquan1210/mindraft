import argparse
from pathlib import Path

from filelock import Timeout

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
        from scripts.serve import start_server

        start_server(config, open_browser=False)
        return

    # 获取进程锁，防止并发执行（dry-run 模式下也获取锁，保证并发安全）
    lock = get_process_lock(config["notes_vault_path"])
    try:
        with lock:
            if args.dry_run:
                from scripts.process_notes import process_new_notes
                from scripts.analyze import generate_dashboard_data

                logger.info("--dry-run 模式：调用 LLM，但不写入任何业务状态文件")
                if args.analyze:
                    generate_dashboard_data(config, dry_run=True)
                    logger.info("Analyze dry-run 完成")
                else:
                    process_new_notes(config, dry_run=True)
                    logger.info("Dry-run 完成")
                return

            if args.analyze:
                from scripts.analyze import generate_dashboard_data
                from scripts.serve import start_server

                generate_dashboard_data(config, dry_run=False)
                start_server(config, open_browser=True)
                return

            if args.notes_only:
                from scripts.process_notes import process_new_notes

                process_new_notes(config, dry_run=False)
                return

            # 默认：只处理新笔记
            from scripts.process_notes import process_new_notes

            process_new_notes(config, dry_run=False)
    except Timeout:
        logger.error("另一个 Mindraft 实例正在运行，请等待其完成后再试")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
