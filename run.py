import argparse

from filelock import Timeout

from scripts.utils import (
    load_config,
    get_process_lock,
    setup_logging,
    migrate_legacy_analysis_state,
)


def main():
    parser = argparse.ArgumentParser(description="Mindraft")
    parser.add_argument("--analyze", action="store_true",
                        help="执行全部 AI 分析（处理新笔记 + 生成 dashboard 数据），不启动服务")
    parser.add_argument("--dashboard", action="store_true",
                        help="只启动 dashboard 服务并打开浏览器，不做任何分析")
    parser.add_argument("--rebuild", action="store_true",
                        help="清空全部分析结果（ai_notes/、memory.json、dashboard 数据、process_log），从头重新分析")
    parser.add_argument("--dry-run", action="store_true",
                        help="调用 LLM 但不写入任何业务状态文件、不启动服务")
    args = parser.parse_args()

    if args.rebuild and args.dry_run:
        parser.error("--rebuild 会删除文件，不能与 --dry-run 同时使用")
    if args.rebuild and args.dashboard:
        parser.error("--rebuild 会做全部分析，不能与 --dashboard 同时使用")

    config = load_config()

    # rebuild 的清空必须先于 setup_logging：日志文件句柄一旦打开，
    # 删除 process_log 后新日志会写入已删除的 inode
    removed = []
    if args.rebuild:
        from scripts.utils import reset_analysis_state

        removed = reset_analysis_state(config)

    logger = setup_logging(config)

    logger.info(f"Mindraft 启动 | dry_run={args.dry_run}")

    # 旧布局迁移：{vault}/analysis/memory.json → {vault}/.mindraft/memory.json
    migrate_legacy_analysis_state(config)

    if args.rebuild:
        if removed:
            logger.info("--rebuild：已清空分析结果：")
            for path in removed:
                logger.info(f"  已删除 {path}")
        else:
            logger.info("--rebuild：没有需要清空的分析结果")

    if args.dashboard:
        from scripts.serve import start_server

        start_server(config, open_browser=True)
        return

    # 获取进程锁，防止并发执行（dry-run 模式下也获取锁，保证并发安全）
    lock = get_process_lock()
    try:
        with lock:
            from scripts.process_notes import process_new_notes
            from scripts.analyze import generate_dashboard_data

            if args.dry_run:
                logger.info("--dry-run 模式：调用 LLM，但不写入任何业务状态文件")
                process_new_notes(config, dry_run=True)
                generate_dashboard_data(config, dry_run=True)
                logger.info("Dry-run 完成")
                return

            process_new_notes(config, dry_run=False)
            generate_dashboard_data(config, dry_run=False)
    except Timeout:
        logger.error("另一个 Mindraft 实例正在运行，请等待其完成后再试")
        raise SystemExit(1)

    # --analyze：只做 AI 分析，不启动服务
    if args.analyze:
        return

    # 默认：完整流程，分析完成后启动 dashboard 服务并打开浏览器
    # 注意：服务在进程锁之外启动，避免服务运行期间长期占用 .mindraft.lock
    from scripts.serve import start_server

    start_server(config, open_browser=True)


if __name__ == "__main__":
    main()
