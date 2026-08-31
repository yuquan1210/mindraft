# scripts/skill_loader.py
import yaml
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"

VOCABULARY_PLACEHOLDER = "{subcategory_vocabulary}"
_VOCABULARY_FALLBACK = "（未配置词表，自行归纳 subcategory）"


def build_system_prompt(operation: str, base_role: str, config: dict) -> str:
    """
    根据 operation 名称，自动查找所有适用且启用的 skill，
    拼装为完整的 system prompt；同时注入 config 中的推荐 subcategory 词表。
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

    prompt = base_role
    if applicable_rules:
        rules_block = "\n\n".join(applicable_rules)
        prompt = f"{prompt}\n\n## 执行规则\n\n{rules_block}"

    if VOCABULARY_PLACEHOLDER in prompt:
        prompt = prompt.replace(
            VOCABULARY_PLACEHOLDER, _render_vocabulary(config)
        )

    return prompt


def _render_vocabulary(config: dict) -> str:
    """将 config.subcategory_vocabulary 渲染为 prompt 中的词表文本。"""
    vocabulary = config.get("subcategory_vocabulary") or {}
    if not vocabulary:
        return _VOCABULARY_FALLBACK
    lines = []
    for domain in sorted(vocabulary):
        words = vocabulary[domain] or []
        lines.append(f"- {domain}: {', '.join(words)}")
    return "\n".join(lines)
