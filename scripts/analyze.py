import logging
from pathlib import Path

logger = logging.getLogger("mindraft")


def generate_dashboard_data(config: dict, dry_run: bool = False):
    """
    生成 Dashboard 所需数据。
    Phase 0 仅作为占位实现，Phase 2 补充完整逻辑。
    """
    vault = Path(config["notes_vault_path"]).expanduser()
    logger.info(f"generate_dashboard_data 占位调用: dry_run={dry_run}, vault={vault}")
    # Phase 2 将从 memory.json 生成 stats.json、summaries.json 等
