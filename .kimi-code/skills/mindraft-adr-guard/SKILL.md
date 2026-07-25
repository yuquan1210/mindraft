---
name: mindraft-adr-guard
description: |
  **USE THIS SKILL** whenever the user is reviewing or implementing code in the Mindraft project and wants to ensure it complies with the project's Architecture Decision Records (ADRs). Trigger on phrases like "check ADR compliance", "does this follow the ADRs", "review this against Mindraft architecture", "mindraft guard", "validate ADR", or whenever the user modifies core files like `run.py`, `process_notes.py`, `memory.json` handling, LLM abstraction, `skill_loader.py`, or the renderer plugin system.
---

# Mindraft ADR Guard

审查 Mindraft 项目代码是否符合 `doc/Mindraft-Log.md` 中记录的架构决策（ADRs），并输出带引用和修复建议的详细报告。

## 何时使用

- 用户要求检查代码/改动是否遵守项目架构
- 实现完一个 Phase 后需要复核核心约束
- 修改了 `run.py`、`scripts/`、`skills/`、`dashboard/renderers/` 等核心模块
- 用户问 "这会不会违反 ADR"、"检查一下 ADR 合规性"

## 预期输入

- 当前工作目录应是 Mindraft 项目根目录（包含 `doc/Mindraft-Log.md` 和 `config.yml`）。
- 用户可以指定要审查的文件或目录；未指定时，默认审查核心产物：`config.yml`、`run.py` 和 `scripts/` 下的所有 `.py` 文件。

## 工作流程

1. **确认项目身份**
   - 检查当前目录是否存在 `doc/Mindraft-Log.md`（或 `doc/Mindraft.md`）。
   - 如果不存在，直接返回："当前目录看起来不是 Mindraft 项目，ADR Guard 只适用于 Mindraft 项目。"

2. **读取 ADR 事实来源**
   - 读取 `doc/Mindraft-Log.md` 的 "核心架构决策 (ADR)" 部分，提取每个 ADR 的编号、决策内容和影响。

3. **确定审查范围**
   - 如果用户在 prompt 中提供了具体文件/目录，按提供的范围审查。
   - 否则，审查 `config.yml`、`run.py` 和 `scripts/**/*.py`。

4. **逐项检查 ADR 合规性**
   - 对清单中的每一项，使用 `Read` / `Grep` 查找证据。
   - 记录 `PASS` / `FAIL` / `NOT_APPLICABLE` 状态，并引用具体文件和行号/片段。

5. **生成报告**
   - 使用下方报告模板输出。
   - 对于 `FAIL` 项，给出具体修复建议。

## ADR 合规检查清单

| ADR | 核心要求 | 检查方法 |
|-----|---------|----------|
| ADR-001 双 Repo | 代码仓库与笔记仓库分离；`config.yml` 通过 `notes_vault_path` 关联；代码中不硬编码笔记仓库路径；绝不写入 `raw_notes/` | 检查 `config.yml` 是否有 `notes_vault_path`；搜索 `raw_notes/` 写操作；搜索硬编码 vault 路径 |
| ADR-002 增量蒸馏记忆 | 每次 LLM 调用只传入 `active_memory` + 当前笔记，不堆积全文 | 检查 `process_notes.py` 中 LLM 调用是否包含 `active_memory` 参数/上下文，且不传入大量历史笔记原文 |
| ADR-003 记忆只增不减 | `memory_updates` 只允许 `APPEND_TO` 和 `SET_IF_NEW`；其余操作忽略 | 检查 `apply_memory_updates()` 是否只处理这两个 action；是否有 `DELETE`/`OVERWRITE` 分支执行了实际修改 |
| ADR-004 形象进化而非重建 | 默认使用 `evolve_avatar()`；Genesis 只在首次运行/重置/重大转变时触发 | 检查 `analyze.py` 中形象生成逻辑；`avatar_identity` 核心字段是否被轻易覆盖 |
| ADR-005 LLM 抽象层 | 业务代码只使用 `BaseLLM`；通过 `llm_factory.py` 切换模型；不直接导入 `openai`/`anthropic` 等具体实现 | 在 `scripts/` 中搜索 `import openai`、`from openai`、`import anthropic` 等；确认工厂模式使用 |
| ADR-006 Skill YAML 配置系统 | AI 行为规则通过 `skills/*.yml` 管理；`skill_loader.py` 按 operation 拼装；不硬编码 prompt | 检查 `skills/` 目录和 `skill_loader.py`；搜索业务代码中硬编码的长 prompt 字符串 |
| ADR-007 Renderer 插件体系 | `avatar_data.json` 数据契约稳定；渲染器可替换，继承 `BaseAvatarRenderer` | 检查 `dashboard/renderers/` 中渲染器是否继承 `BaseAvatarRenderer`；检查 `avatar_data.json` 字段是否被随意删除/重命名 |
| ADR-008 原子写入 + 进程锁 | `memory.json` 等核心文件使用 `safe_write_json()`；`run.py` 获取 `get_process_lock()` | 搜索 `memory.json` 写入点是否使用 `safe_write_json`；检查 `run.py` 是否获取锁 |
| ADR-009 LLM 输出 JSON Schema 校验 | 所有 LLM 结构化返回使用 `jsonschema` 校验；`chat_json()` 兜底解析 | 检查 `schemas.py` 和 `process_notes.py` 中是否有 `validate_llm_output` 调用 |
| ADR-010 笔记预筛选与批量处理 | `note_filter.py` 负责预筛选和分组；空文件/过短/无自然语言笔记跳过；短笔记合并 | 检查 `note_filter.py` 中 `should_skip_note` 和 `group_notes_for_processing` 实现 |
| ADR-011 逐篇 Checkpoint 断点恢复 | 每篇笔记处理完立即写入 `memory.json`；失败时跳过当前组继续 | 检查 `process_notes.py` 中是否在每篇笔记后调用 `safe_write_json` |
| ADR-012 前端配置导出 | `analyze.py` 导出 `dashboard/data/config.json`；不暴露 API key | 检查 `analyze.py` 中 `export_frontend_config`；确认导出的 JSON 不含 `api_keys` |
| ADR-013 跨周快照 | 检测到跨越自然周时独立生成快照；不依赖记忆压缩 | 检查 `maybe_generate_weekly_snapshot()` 是否被调用且逻辑不依赖压缩 |

## 输出格式

使用以下模板输出：

```markdown
# Mindraft ADR Guard 报告

## 审查范围
- 项目根目录：`<absolute-path>`
- 审查文件：`<file1>`, `<file2>`, ...

## 总体状态
- 通过：N 项
- 失败：N 项
- 不适用：N 项

## 详细检查

### ADR-00X: <标题>
- **状态**：PASS / FAIL / NOT_APPLICABLE
- **证据**：`<file>:<line>` 处的代码片段或说明
- **问题**（仅 FAIL）：具体描述
- **修复建议**（仅 FAIL）：具体步骤

...

## 汇总与建议
- 按优先级列出需要修复的问题
- 如果不确定某一项是否合规，明确说明"无法从现有代码中确认"，不要猜测
```

## 重要原则

- **禁止猜测**：如果无法从代码中找到直接证据，标记为 `NOT_APPLICABLE` 或 `无法确认`，不要为凑结论而编造。
- **引用具体位置**：每个 FAIL 必须给出文件路径和代码片段或行号范围。
- **建议要可行**：修复建议应具体到"把 X 改成 Y"，而不是泛泛而谈。
- **不修改文件**：只输出审查报告，不自动修复代码，除非用户明确要求。
