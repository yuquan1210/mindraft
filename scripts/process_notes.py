import logging
from pathlib import Path

logger = logging.getLogger("mindraft")


def process_new_notes(config: dict, dry_run: bool = False):
    """
    处理 raw_notes 中的新笔记。
    Phase 0 仅作为占位实现，Phase 1 补充完整逻辑。
    """
    vault = Path(config["notes_vault_path"]).expanduser()
    raw_notes_dir = vault / "raw_notes"

    if not raw_notes_dir.exists():
        logger.warning(f"raw_notes 目录不存在: {raw_notes_dir}")
        return

    logger.info(f"process_new_notes 占位调用: dry_run={dry_run}, vault={vault}")
    # Phase 1 将扫描 raw_notes → LLM 处理 → 写入 ai_notes
