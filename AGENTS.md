# Mindraft — AGENTS.md

> 本文件是 AI Agent 的项目入口，每次会话自动读取。细节文档按需查阅：
> - `doc/Mindraft.md`（产品方案与阶段设计）
> - `doc/mindraft-log.md`（实现日志 + ADR-001~014，架构决策的唯一权威来源）
> - `doc/Mindraft-Vibe-Coding-Guide.md`（人机协作流程）

## 项目定位

Mindraft 是本地运行的个人笔记分析引擎。用户用 Obsidian 在 `notes-vault/raw_notes/` 写 Markdown，运行 `python run.py` 后由 LLM 处理笔记、蒸馏记忆，并通过本地 Dashboard 展示分析结果。双 Repo：`mindraft`（代码）与 `notes-vault`（笔记）通过 `config.yml → notes_vault_path` 关联。

核心原则（不可违反）：
- **原始笔记不可侵犯**：`raw_notes/` 永远只读。
- **记忆只增不减**：`memory_updates` 只允许 `APPEND_TO`、`SET_IF_NEW`；历史信号只归档或压缩，不删除。
- LLM、Skill、Renderer 全部可替换（抽象层 + 配置切换）。

## 当前状态

- **Phase 1（笔记处理核心）✅ 完成；Phase 2（Dashboard MVP）✅ 完成**。下一步 Phase 3（记忆压缩、跨周快照等，见 `doc/mindraft-log.md` 与 `doc/Mindraft.md` §9）。
- Phase 1 延后项：短笔记批量合并（`note_filter.py` 中 `group_notes_for_processing` 目前是逐篇占位）、`summary_style.yml`、笔记关联、URL 抓取、像素画形象。
- 注意：`config.yml` 中 `summary_style` / `analysis_style` / `memory_compression` 三个 skill 开关对应的 yml 文件尚不存在，`skills/` 下实际只有 `note_style.yml`、`tagging.yml`、`json_output.yml`。

## 目录结构

```
mindraft/
├── config.yml            # 主配置（LLM provider、skill 开关、记忆阈值等）
├── run.py                # 入口：默认完整流程（笔记 + dashboard 数据 + 起服务）；--analyze / --dashboard / --rebuild / --dry-run
├── scripts/
│   ├── llm/              # base.py + kimi/openai/anthropic/deepseek
│   ├── llm_factory.py    # 按 config.llm_provider 返回 BaseLLM 实例
│   ├── skill_loader.py   # 按 operation 拼装 system prompt（skills/*.yml）
│   ├── process_notes.py  # 笔记处理主流程（逐篇 checkpoint）
│   ├── note_filter.py    # 预筛选与分组
│   ├── analyze.py        # 生成 dashboard/data/*.json
│   ├── serve.py          # 本地静态服务
│   ├── schemas.py        # LLM 输出 JSON Schema
│   ├── prompts.py        # 所有 Role Prompt
│   └── utils.py          # safe_write_json、token 估算、配置加载等
├── skills/               # *.yml Skill 配置
├── dashboard/            # 静态前端（index.html / app.js / style.css / data/）
├── logs/                 # process_log.jsonl（运行日志，gitignore）
└── tests/                # pytest
```

关键路径（代码生成，勿手改）：记忆状态在 `{notes_vault}/.mindraft/memory.json`（隐藏目录，ADR-014）；日志在 `mindraft/logs/process_log.jsonl`；进程锁在 `mindraft/.mindraft.lock`；AI 重写笔记写入 `{notes_vault}/ai_notes/`。

## 常用命令

```bash
pip install -r requirements.txt   # 安装依赖（可选：anthropic、tiktoken）
python run.py                     # 完整流程：处理新笔记 → 生成 dashboard 数据 → 启动服务并打开浏览器
python run.py --analyze           # 只做 AI 分析（处理新笔记 + 生成 dashboard 数据），不启动服务；memory 未变化时跳过生成
python run.py --dashboard         # 只启动 dashboard 服务并打开浏览器，不做任何分析
python run.py --rebuild           # 清空全部分析结果（ai_notes/、memory.json、dashboard 数据、process_log）后走完整流程
python run.py --dry-run           # 干跑：调 LLM 但不写文件、不启动服务
python -m pytest tests/           # 测试（test_llm_real.py 需要真实 API key）
```

## 硬约束

- **不修改** `raw_notes/` 任何文件。
- `memory.json` 等核心状态文件必须通过 `utils.safe_write_json()` 原子写入；`run.py` 启动时获取 filelock 进程锁。
- LLM 返回必须通过 `jsonschema` 校验；失败时自动重试一次（`_call_with_retry()`），仍失败则记录日志并跳过当前组，不中断整体流程。
- Role Prompt 必须定义在 `prompts.py`，业务代码不硬编码 system prompt。
- 所有 LLM 调用只通过 `BaseLLM` 接口（`llm_factory.get_llm()`），不直接实例化具体模型类。
- 每次实现变更后，同步更新 `doc/mindraft-log.md`。

## 工作方式

- 实现新功能前：读本文件 → 按阶段精读 `doc/Mindraft.md` §9 对应 Phase 的目标与验收标准 → 需要决策依据时查 `doc/mindraft-log.md` 的 ADR。
- 数据结构与代码细节以 `scripts/` 实际代码为准（`schemas.py`、`process_notes.py` 是唯一事实源），不要凭文档中的示例代码实现。
- 验证改动：`python run.py --dry-run` + `python -m pytest tests/`。
