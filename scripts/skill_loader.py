# scripts/skill_loader.py
import yaml
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"


def build_system_prompt(operation: str, base_role: str, config: dict) -> str:
    """
    根据 operation 名称，自动查找所有适用且启用的 skill，
    拼装为完整的 system prompt
    """
    skill_toggles = config.get("skills", {})
    applicable_rules = []

    for skill_file in sorted(SKILLS_DIR.glob("*.yml")):
        skill = yaml.safe_load(skill_file.read_text())
        skill_name = skill.get("name")

        if not skill_toggles.get(skill_name, {}).get("enabled", True):
            continue

        if operation in skill.get("applies_to", []):
            rules_text = "\n".join(f"- {r}" for r in skill["rules"])
            applicable_rules.append(
                f"### {skill['description']}\n{rules_text}"
            )

    if not applicable_rules:
        return base_role

    rules_block = "\n\n".join(applicable_rules)
    return f"{base_role}\n\n## 执行规则\n\n{rules_block}"
