---
name: mindraft-test-runner
description: |
  **USE THIS SKILL** whenever the user wants to verify the Mindraft project runs correctly. Trigger on phrases like "test mindraft", "run dry-run", "验证 Mindraft", "跑一下验收", "check if run.py works", "运行测试", or whenever the user finishes implementing a Phase and wants to run the acceptance commands from `doc/Mindraft.md`.
---

# Mindraft Test Runner

运行 Mindraft 项目的标准验证命令，解析输出与日志，并给出通过/失败报告。

## 何时使用

- 完成一个 Phase 后需要按 `doc/Mindraft.md` 中的验收标准验证
- 用户说 "跑一下 dry-run"、"测试一下"、"验证项目能启动"
- 修改了 `run.py`、配置或核心脚本后想确认没破坏基础流程

## 预期输入

- 当前工作目录应是 Mindraft 项目根目录（包含 `run.py` 和 `config.yml`）。
- 用户可指定运行哪些命令；未指定时，默认运行 `python run.py --dry-run` 和 `python run.py --notes-only`（如果 `raw_notes/` 存在且有有效笔记）。

## 工作流程

1. **确认项目身份**
   - 检查当前目录是否存在 `run.py` 和 `config.yml`。
   - 如果不存在，直接返回："当前目录看起来不是 Mindraft 项目，请切换到项目根目录。"

2. **检查环境**
   - 运行 `python --version` 或 `python3 --version` 确认 Python 3.11+。
   - 检查 `config.yml` 中 `notes_vault_path` 是否存在且可解析。
   - 检查 `requirements.txt` 或 `pyproject.toml` 是否存在；如果存在，提示/尝试安装依赖（不自动安装，除非用户明确要求）。

3. **执行默认命令**
   - 始终运行：`python run.py --dry-run`（如果 `python` 不可用，尝试 `python3 run.py --dry-run`）
   - 可选（默认启用）：`python run.py --notes-only`（同上，自动回退到 `python3`）
   - 用户可要求追加：`--analyze`, `--serve`, 或完整 `python run.py`。

4. **解析日志与输出**
   - 如果命令失败，记录错误信息、traceback 和退出码。
   - 如果命令成功，检查 `analysis/process_log.jsonl`（如存在）是否有 ERROR 或 WARNING 级别日志。

5. **生成报告**
   - 按下方模板输出，明确给出"通过"/"失败"结论和下一步建议。

## 输出格式

```markdown
# Mindraft Test Runner 报告

## 环境检查
- Python 版本：`<version>`
- 项目根目录：`<absolute-path>`
- notes_vault_path：`<path>` / `未配置` / `路径不存在`

## 执行命令

### 1. `python[3] run.py --dry-run`
- **退出码**：0 / 非 0
- **状态**：PASS / FAIL
- **关键输出摘要**：...
- **错误**（如有）：...

### 2. `python[3] run.py --notes-only`
- ...

## 日志检查（analysis/process_log.jsonl）
- ERROR 数量：N
- WARNING 数量：N
- 关键日志摘录：...

## 总体结论
- **结果**：PASS / FAIL
- **下一步**：...
```

## 重要原则

- **不自动修复代码**：只运行和报告，除非用户明确说"请修复"。
- **依赖管理**：如果缺少依赖，报告具体缺失的包（如 `openai`、`pyyaml`、`jsonschema`、`filelock`），让用户决定是否安装。
- **安全**：不读取 `.env` 或真实 API key；只检查占位符是否存在。
- **失败时明确**：给出可执行的下一步，例如 "安装缺失依赖：pip install -r requirements.txt"。
