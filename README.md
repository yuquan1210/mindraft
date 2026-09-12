# Mindraft

Mindraft 是本地运行的个人笔记分析引擎。你在 Obsidian 或其他编辑器中写 Markdown，Mindraft 通过 LLM 将原始笔记按类别拆分、重写，持续积累记忆，并在本地 Dashboard 展示摘要、性格侧写与成长时间轴。

```text
raw_notes/*.md → 分类重写的 ai_notes/ → 增量记忆与历史归档 → 本地 Dashboard
```

当前已完成 Phase 1–3：笔记处理、Dashboard、两区记忆压缩和跨周快照。笔记关联、URL 抓取、短笔记批处理与用户形象仍是后续规划。

## 环境要求

- Python 3.10 或以上（代码使用 `match` 和 `X | Y` 类型语法）。
- 一个笔记目录；可直接使用已有的 Obsidian vault，无需将它放进代码仓库。
- 一个支持的 LLM provider 的 API key：DeepSeek、Kimi、OpenAI 或 Anthropic。
- 浏览器。Dashboard 使用静态 HTML/CSS/JS，无需 Node.js 或前端构建。

以下命令适用于 macOS / Linux 的 bash 或 zsh。请在 **mindraft 项目根目录**执行，程序默认从当前目录读取 `config.yml`。

## 首次安装

进入已下载或克隆的项目目录，然后创建并激活虚拟环境：

```bash
cd /path/to/mindraft
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install pytest
```

`/path/to/mindraft` 替换为实际路径。`pytest` 是测试依赖，目前未列入 `requirements.txt`，所以需要单独安装。

只有用到对应功能时才安装可选依赖：

```bash
# llm_provider: anthropic
python -m pip install anthropic

# token_estimation: tiktoken
python -m pip install tiktoken
```

每次打开新终端，都需要重新执行 `source .venv/bin/activate`。退出虚拟环境使用 `deactivate`。

## 配置笔记目录与模型

编辑 `config.yml` 中的以下配置，保留文件中的其余设置：

```yaml
notes_vault_path: ~/Developer/notes-vault
llm_provider: deepseek
llm_model: deepseek-v4-flash
llm_reasoning_effort: none

dashboard_port: 8765
```

`llm_model` 应填写所选 provider 账号可用的模型名称；上面展示的是仓库当前配置。`llm_reasoning_effort` 仅用于 DeepSeek。

笔记目录结构如下。请自行创建 `raw_notes/`，并在其中保存 Markdown 文件；其他路径由程序生成：

```text
notes-vault/
├── raw_notes/              # 原始 Markdown，Mindraft 永远只读
│   ├── 2026-09-12.md
│   └── project-review.md
├── ai_notes/               # AI 重写产物：{domain}/{subcategory}/*.md
└── .mindraft/
    └── memory.json         # 当前记忆、标签、处理记录与历史归档
```

当前只扫描 `raw_notes/` 直接包含的 `*.md`，不递归扫描子目录。文件按文件名排序处理；日期格式文件名便于保持时间顺序。

### 配置 API key

可以在当前终端直接导出对应环境变量，例如：

```bash
export DEEPSEEK_API_KEY='替换为你的真实 API key'
```

也可以使用项目提供的 `.env.example`。如果还没有 `.env`，复制后编辑：

```bash
cp .env.example .env
```

填好所选 provider 的 key 后，在运行程序的**同一终端**加载：

```bash
set -a
source .env
set +a
```

**程序不会自动加载 `.env`。** 虚拟环境激活也不会加载 API key；`set -a` 让文件中的变量导出给 Python 子进程。每次新开终端需要重新加载，除非你已通过 shell 配置导出这些变量。

| `llm_provider` | 环境变量 |
| --- | --- |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `kimi` | `KIMI_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |

只需配置实际使用的 provider。`.env` 已被 Git 忽略；不要把真实 key 写进受版本控制的 `config.yml`。

分析会将当前笔记及热层记忆发送给所选 LLM provider。本地运行指本地保存数据和提供 Dashboard，并不意味着模型推理离线。

## 日常运行

完成首次配置后，新开终端时按下面的顺序运行。如果 key 已由 shell 导出，可省略加载 `.env` 的三行：

```bash
cd /path/to/mindraft
source .venv/bin/activate
set -a
source .env
set +a
python run.py
```

默认流程为：处理新笔记 → 更新记忆与 Dashboard 数据 → 启动本地服务器并打开浏览器。默认地址为 [http://localhost:8765](http://localhost:8765)，端口可在 `config.yml` 修改。

服务器运行期间保持终端打开，按 **Ctrl+C** 停止。它只监听本机地址。新增笔记不会自动触发分析；写完后再次运行分析命令，刷新 Dashboard 即可。

### 常用命令

下面的命令均在已激活虚拟环境的项目根目录执行：

| 命令 | 行为 |
| --- | --- |
| `python run.py` | 处理新笔记、生成 Dashboard 数据、启动服务并打开浏览器 |
| `python run.py --analyze` | 处理新笔记并生成数据，完成后退出，不启动服务 |
| `python run.py --dashboard` | 仅启动服务展示已有数据，不调用 LLM；无需 API key |
| `python run.py --dry-run` | 调用 LLM，在内存中模拟处理和分析，不保存业务数据、不启动服务 |
| `python run.py --help` | 查看命令说明 |

可以保持一个 `--dashboard` 终端运行，在另一个已激活环境并加载 key 的终端执行 `--analyze`，完成后刷新页面。

`--dry-run` **仍会调用真实 API 并可能产生费用**，也会产生运行日志和使用进程锁；它不修改原笔记、AI 笔记、记忆状态或 Dashboard 数据。请检查终端是否出现 error/fallback，而不只看退出码。

`active_memory` 不变且数据文件有效时，普通分析会复用摘要与性格侧写；统计、标签和时间轴仍更新。缺文件或上次生成失败时会重新生成。

### 从头重建（会清空已有分析结果）

`--rebuild` 会删除 `ai_notes/`、记忆状态（包括历史归档）、Dashboard JSON 数据及处理日志，然后重新分析原始笔记并启动服务。`raw_notes/` 不受影响。需要保留历史时，应先备份整个笔记目录；普通更新应使用 `--analyze`。

```bash
python run.py --rebuild

# 重建后退出，不启动服务器
python run.py --rebuild --analyze
```

不能将 `--rebuild` 与 `--dry-run` 或 `--dashboard` 组合；`--dashboard` 也不能与 `--analyze` 或 `--dry-run` 组合。

## 运行测试

### 离线回归测试（不调用真实 API）

从新终端执行：

```bash
cd /path/to/mindraft
source .venv/bin/activate
python -m pip install pytest
python -m pytest tests/ --ignore=tests/test_llm_real.py
```

这些测试使用 mock LLM 和临时笔记目录，不需要 API key，也不会重建你的真实 vault。覆盖笔记拆分、记忆更新与压缩、失败恢复、周归档、Dashboard 缓存及本地 HTTP 路由。

### 全量测试（包含真实 API 测试）

```bash
cd /path/to/mindraft
source .venv/bin/activate
set -a
source .env
set +a
python -m pytest tests/
```

真实测试使用 `config.yml` 所选 provider 和模型：

- 当前进程没有对应 key，或 key 仍是 `${...}` 占位符时，真实 API 测试标记为 `skipped`。
- key 已加载时，会执行真实文本与 JSON 调用，可能产生费用。
- key 不正确、网络故障或模型不可用时，真实测试会失败；不会因错误 key 自动跳过。

### 单独验证 API 或某个模块

以下命令同样需要先执行 `source .venv/bin/activate`；真实 API 测试还需要加载 key。

```bash
# 仅运行真实 API 测试；-rs 显示跳过原因
python -m pytest tests/test_llm_real.py -v -rs

# 仅测试记忆压缩与归档，不调用真实 API
python -m pytest tests/test_memory.py -v

# 运行单个用例
python -m pytest tests/test_memory.py::test_compression_failure_is_noop_and_retries -v
```

验证完整真实处理链路可使用 `python run.py --dry-run`；真实 API smoke 测试本身只验证模型接口，不代表实际笔记的生成质量。

## 数据与处理约定

- 一篇原笔记可拆分成 1–5 篇 AI 笔记，归入 `work`、`life`、`growth`、`wellbeing`、`identity` 五域。
- 每个 tag 在一篇原笔记内只计一次，累计至少 3 篇后成为活跃标签。
- 已处理文件按文件名记录，不会因为原文被编辑而自动重新处理。预筛选跳过的短笔记、空笔记也会记为已处理。
- 热层保留近期观察和较早观察的浓缩文本；压缩前完整热层进入 `history_archive`。token 阈值是软目标，并非硬上限。
- 周快照在跨周运行时生成，无需周末定时运行；时间轴显示截至归档时的累计笔记数。
- 核心 JSON 原子保存；普通笔记写入失败会回滚本次产物。但强制终止进程恰好发生在 Markdown 与记忆写入之间时，仍可能留下孤立 AI 笔记。

| 位置 | 用途 |
| --- | --- |
| `{notes_vault}/raw_notes/` | 用户维护的原始笔记 |
| `{notes_vault}/ai_notes/` | 自动生成的分类笔记 |
| `{notes_vault}/.mindraft/memory.json` | 记忆、历史归档与处理状态；建议随 vault 备份 |
| `dashboard/data/` | 自动生成的六份 Dashboard JSON 数据 |
| `logs/process_log.jsonl` | 本次及历史运行日志 |
| `.mindraft.lock` | 防止多个分析进程同时写入的文件锁 |

## 常见问题

| 现象 | 检查方法 |
| --- | --- |
| `ModuleNotFoundError` / 找不到 `pytest` | 先 `source .venv/bin/activate`，再执行依赖安装；使用 `python -m pip` 和 `python -m pytest` 确保使用同一环境 |
| `config.yml` 不存在 | 切换到 mindraft 项目根目录后运行 |
| API 返回 401，或真实测试被 skip | 检查 provider 与变量名是否匹配，并在当前终端执行 `set -a; source .env; set +a`；其他终端设置的 key 不会自动传入当前进程 |
| 没有新笔记被处理 | 检查 `notes_vault_path`、文件是否直接位于 `raw_notes/`、是否为 `.md`、是否过短或已经处理过 |
| Dashboard 尚无数据 | 先运行 `python run.py --analyze`，再运行 `python run.py --dashboard` |
| 摘要或性格侧写显示 fallback | 查看终端和 `logs/process_log.jsonl`，确认 API/模型可用后重跑 `--analyze` |
| 端口已被占用 | 停止已有服务，或修改 `config.yml` 的 `dashboard_port` |
| 另一个 Mindraft 实例正在运行 | 等待分析完成后重试；不要在进程运行时手动删除锁文件 |
| 记忆状态无法读取 | 检查文件或从备份恢复；程序不会用空记忆覆盖损坏文件 |

## 代码与设计文档

```text
run.py                   # CLI 与流程编排
config.yml               # vault 路径、LLM、记忆阈值、skill 开关、服务端口
scripts/process_notes.py # 逐篇处理、分类笔记写入、checkpoint
scripts/memory_state.py  # 记忆字段定义与兼容读取
scripts/memory.py        # 两区压缩、归档与周快照
scripts/analyze.py       # Dashboard 数据与 LLM 摘要生成
scripts/llm/             # 可替换的模型适配器
scripts/llm_calls.py     # 共用的校验与一次重试
scripts/schemas.py       # LLM 输出与状态校验契约
skills/                  # YAML 行为规则
scripts/serve.py         # 本地 Dashboard 与生成笔记服务
dashboard/               # 静态前端
tests/                   # pytest 回归与真实 API 测试
```

- [产品方案与阶段规划](doc/Mindraft.md)
- [实现日志与架构决策](doc/mindraft-log.md)
- [人机协作流程](doc/Mindraft-Vibe-Coding-Guide.md)
- [Agent 项目约束](AGENTS.md)
