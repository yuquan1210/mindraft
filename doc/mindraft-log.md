# Mindraft — 实现日志

> 供 AI Agent 恢复上下文使用。每次实现中断前更新此文档，每次继续实现时先读取此文档。
> 产品文档：[# Mindraft.md](# Mindraft.md) · 技术参考：[Mindraft-Technical.md](Mindraft-Technical.md)

---

## 项目状态

**当前阶段**：Phase 1 ✅ 已完成 → Phase 2 ⬜ 未开始
**实现方式**：Vibe-coding — AI 实现，人工审查 + 指挥
**最后更新**：2026-07-26

---

## 核心架构决策 (ADR)

### ADR-001：双 Repo 架构

| 项 | 内容 |
|----|------|
| **决策** | 笔记仓库（notes-vault）与产品代码（mindraft）分离为两个 Repo |
| **理由** | 原始笔记与产品代码关注点完全不同；Obsidian 管理笔记，Git 双向同步；两者可独立版本控制 |
| **影响** | 运行时通过 `config.yml → notes_vault_path` 关联两个 Repo |
| **状态** | ✅ 已确认 |

---

### ADR-002：增量蒸馏记忆

| 项 | 内容 |
|----|------|
| **决策** | LLM 每次调用只接收 `active_memory`（~600 tokens）+ 当前笔记，不堆积原始笔记全文 |
| **理由** | 保证 token 消耗恒定，笔记量从 10 篇增长到 10,000 篇，LLM 调用成本不变 |
| **影响** | 历史笔记的信息通过 memory 蒸馏保留，不以原文形式出现 |
| **状态** | ✅ 已确认 |

---

### ADR-003：记忆只增不减

| 项 | 内容 |
|----|------|
| **决策** | `memory_updates` 只允许 `APPEND_TO` 和 `SET_IF_NEW` 两种操作，LLM 返回 DELETE / OVERWRITE 时直接忽略 |
| **理由** | 历史信号永远有价值；矛盾信号本身也是观察数据（标记为"存在矛盾信号"而非删除）；防止 AI 幻觉误删数据 |
| **影响** | `apply_memory_updates()` 中的 `case _: pass` 是安全阀，不可删除 |
| **状态** | ✅ 已确认 |

---

### ADR-004：形象进化而非重建

| 项 | 内容 |
|----|------|
| **决策** | avatar 以 `evolve_avatar()`（增量更新）为主，genesis 模式（从头生成）仅在首次运行或明确重置时触发 |
| **理由** | 连续性是用户认同感的来源；每次重建会丢失积累的个性细节，破坏"形象成长"的核心体验 |
| **影响** | `avatar_data.json` 的 `avatar_identity.core_traits` 和 `visual_anchors` 作为稳定锚点不轻易变动 |
| **状态** | ✅ 已确认 |

---

### ADR-005：LLM 抽象层

| 项 | 内容 |
|----|------|
| **决策** | 通过 `BaseLLM` 抽象类 + `llm_factory.py` 实现多 LLM 支持，切换模型只需改 `config.yml` 一行 |
| **理由** | 不绑定特定模型；降低迁移成本；支持按需选用最优/最省的模型 |
| **影响** | 所有业务代码只依赖 `BaseLLM`，不直接引用 Kimi / OpenAI 等具体实现 |
| **状态** | ✅ 已确认 |

---

### ADR-006：Skill YAML 配置系统

| 项 | 内容 |
|----|------|
| **决策** | AI 行为规则通过 `.yml` 文件管理，`skill_loader.py` 按 operation 自动拼装 system prompt |
| **理由** | 不改代码即可调整 AI 行为；支持按 operation 精细控制规则组合；方便用户自定义 |
| **影响** | 每次添加新 operation 类型，只需在相应 skill YAML 的 `applies_to` 中声明 |
| **状态** | ✅ 已确认 |

---

### ADR-007：Renderer 插件体系

| 项 | 内容 |
|----|------|
| **决策** | `avatar_data.json` 数据契约固定不变；渲染器（TextCard / PixelArt / Game）可替换，不影响数据层 |
| **理由** | Phase 1 用 TextCardRenderer 快速验证，Phase 2 无缝升级 PixelArtRenderer，不需要改数据结构 |
| **影响** | `avatar_data.json` 的字段结构在 Phase 0 就要最终确定，后续阶段只扩展、不重构 |
| **状态** | ✅ 已确认 |

---

### ADR-008：原子写入 + 进程锁

| 项 | 内容 |
|----|------|
| **决策** | `memory.json` 等核心状态文件使用 write-to-temp + rename 原子写入；通过 `filelock` 库实现进程级文件锁 |
| **理由** | 防止写入中途崩溃导致文件损坏；防止并发执行两个 `run.py` 实例导致数据丢失 |
| **影响** | 所有 JSON 文件写入统一通过 `safe_write_json()` 执行；`run.py` 启动时获取锁，锁获取失败则退出 |
| **状态** | ✅ 已确认 |

---

### ADR-009：LLM 输出 JSON Schema 校验

| 项 | 内容 |
|----|------|
| **决策** | 使用 `jsonschema` 库校验所有 LLM 返回的 JSON 结构，校验失败时记录日志并跳过该笔记 |
| **理由** | LLM 可能漏字段、多字段、字段类型不对；没有校验会导致下游逻辑崩溃或数据损坏 |
| **影响** | `schemas.py` 集中定义所有 schema；`chat_json()` 使用原生 JSON 模式 + 兜底解析 |
| **状态** | ✅ 已确认 |

---

### ADR-010：笔记预筛选与批量处理

| 项 | 内容 |
|----|------|
| **决策** | 在调用 LLM 前，由代码预筛选笔记：跳过空文件、低于阈值的短内容、仅含代码无自然语言的笔记；短笔记合并为一批一次 LLM 调用 |
| **理由** | 节省 LLM API 调用次数和 token 消耗；避免对无意义内容浪费处理资源；首次运行大量笔记时显著减少耗时 |
| **影响** | `note_filter.py` 负责预筛选和分组；config.yml 新增 `note_filter` 配置段；被跳过的笔记仍标记为已处理 |
| **状态** | ✅ 已确认 |

---

### ADR-011：逐篇 Checkpoint 断点恢复

| 项 | 内容 |
|----|------|
| **决策** | 每处理完一篇笔记后立即将 `processed_notes` 和 `active_memory` 持久化到 `memory.json`；处理失败时跳过当前组继续下一组 |
| **理由** | 如果一批笔记处理到中途 LLM API 报错，已完成的部分不会丢失；下次运行会从断点继续 |
| **影响** | `memory.json` 的写入频率从"全部处理完一次性写入"变为"每篇写一次"；使用 `safe_write_json()` 保证原子性 |
| **状态** | ✅ 已确认 |

---

### ADR-012：前端配置导出

| 项 | 内容 |
|----|------|
| **决策** | `analyze.py` 在生成 dashboard 数据时，同时将前端需要的配置子集导出为 `dashboard/data/config.json` |
| **理由** | Dashboard 是纯静态 HTML/JS，无法直接读取 Python 的 YAML 配置；前端需要知道当前使用哪个 renderer |
| **影响** | `app.js` 通过 `fetch("data/config.json")` 加载配置；不暴露 API key 等敏感信息 |
| **状态** | ✅ 已确认 |

---

### ADR-013：跨周快照（替代周末快照）

| 项 | 内容 |
|----|------|
| **决策** | 周快照生成由"如果是周末"改为"检测到跨越自然周时自动生成"，独立于记忆压缩 |
| **理由** | 用户不一定在周末运行脚本；Road Map 在早期阶段（未触发压缩时）也需要数据支撑 |
| **影响** | `maybe_generate_weekly_snapshot()` 比较 `last_updated` 与当前日期的 ISO 周数，跨周则生成 |
| **状态** | ✅ 已确认 |

---

## 实现阶段状态

| 阶段 | 状态 | 完成日期 | 核心产物 |
|------|------|---------|---------|
| Phase 0：基础骨架 | ✅ 已完成 | 2026-07-25 | `.gitignore`、`.env.example`、`requirements.txt`、`config.yml`、LLM 抽象层、`run.py` 骨架、基础设施（`utils.py`、`schemas.py`、`prompts.py`） |
| Phase 1：笔记处理核心 | ✅ 已完成 | 2026-07-26 | `process_notes.py`、`note_filter.py`、skill 系统、`memory.json` |
| Phase 2：Dashboard MVP | ⬜ 未开始 | — | `analyze.py`、Dashboard HTML/JS、`serve.py` |
| Phase 3：记忆系统完善 | ⬜ 未开始 | — | 记忆压缩、MBTI 描述、Road Map |
| Phase 4：用户形象 TextCard | ⬜ 未开始 | — | `avatar_data.json`、TextCardRenderer |
| Phase 5：笔记关联与链接增强 | ⬜ 未开始 | — | `relationships.json`、URL 摘要、关系图 |
| Phase 6：像素画形象 | ⬜ 未开始 | — | Replicate API、PixelArtRenderer |

---

## Grilling 记录（持续更新）

> 每次 grilling 会议后追加记录，包括关键决策、待确认想法、延后项。

### 2026-07-26 Phase 1 规划 grilling

**决策结论**

| 决策项 | 结论 |
|---|---|
| 范围边界 | 以 `Mindraft.md` §9 为准；Phase 1 只实现核心笔记处理链路，不提前实现压缩、tag 升级、summary_style、relationships 等 |
| `memory.json` 结构 | 硬编码五域：`work`, `life`, `growth`, `wellbeing`, `identity`，不允许 LLM 新增自定义域 |
| `memory_updates` path | 点号路径，如 `work.ongoing_projects` |
| 非法 action | 静默忽略 + `logger.warning` |
| `ai_notes/` 目录映射 | `ai_notes/{category}/{filename}` |
| 文件名生成 | LLM 生成英文 `title`，系统 slugify，例如 `productive-friday.md` |
| 重复文件名 | 追加数字，例如 `productive-friday-2.md` |
| 覆盖策略 | Phase 1 不覆盖；frontmatter 保留 `source` 字段用于后续映射 |
| Batching | Phase 1 不做，作为未来优化项 |
| 失败语义 | 失败跳过，不标记为已处理，下次重试 |
| 视为失败的情况 | API 异常、JSON 解析失败、schema 校验失败、写入异常、非法 `category` |
| Tags | 进入 `memory.json.tag_candidates`，只累计 `count`，`status: pending`，不升级；格式强制英文小写连字符 |
| `--dry-run` | 调用 LLM，但不写入文件 |
| 测试 | fixture-based mock 测试 + 人工验收 |
| 文档更新 | Phase 1 完成后更新 `Mindraft-AI-Reference.md` 和 `Mindraft-Log.md` |

**延后/待确认想法**

- Batching 短笔记作为未来优化项
- `summary_style.yml` 延后到 Phase 2/3
- `related_notes` 从 Phase 1 schema 移除，延后到 Phase 5
- Tag 升级机制（count ≥ 3 → active）延后到 Phase 3
- Dashboard 可视化可简化（静态列表/卡片替代 Chart.js 柱状图和 CSS Grid 热力图）
- Phase 6 像素画形象作为最后增强项
- URL 抓取、追问交互、关系网络图可视化延后到 Phase 5+ 优化

### 2026-08-03 Phase 2 规划 grilling

**决策结论**

| 决策项 | 结论 |
|---|---|
| 范围边界 | 最小静态 Dashboard MVP：最近笔记列表 + active_memory 五域摘要 + tag_candidates + 每日一句 + 暗色主题 + 本地服务器。不做 Chart.js 字数图、CSS Grid 热力图、形象、记忆压缩、跨周快照。 |
| 数据文件 | 全部写入 `mindraft/dashboard/data/`：`summaries.json`、`stats.json`、`recent_notes.json`、`config.json` |
| 每日一句 + 五域摘要 | 合并为一次 LLM 调用，prompt 硬编码在 `scripts/prompts.py`，返回 JSON 经 schema 校验 |
| 每日一句风格 | 带情绪/叙事色彩，像安静观察者，150 字以内，中文 |
| 五域摘要 | 每域一句自然语言，顺序固定 work/life/growth/wellbeing/identity |
| 最近笔记列表 | 最多 10 篇，按 `memory.json.processed_notes` 顺序，最后处理在前；`processed_at` 取 `ai_notes/` 文件 mtime |
| `stats.json` | 总笔记数 + 五域 category 计数 |
| 主题/响应式 | 只做 dark 主题，桌面优先 |
| `run.py` 默认行为 | 只处理新笔记；`--analyze` 生成数据 + 启动服务器 + 打开浏览器；`--serve` 只启动服务器；`--dry-run` 不写入 |
| `--analyze --dry-run` | 调用 LLM 但不写入文件、不启动服务器、不打开浏览器 |
| LLM 失败 | `summaries.json` fallback，`daily_insight` 显示固定文案，五域摘要为空，Dashboard 仍可启动 |
| 测试 | 全人工验收，不写前端自动化测试 |
| ADR-013 跨周快照 | 延后到 Phase 3，与 Road Map Timeline 一起实现 |
| 文档更新 | 同步更新 `Mindraft.md` §9/§10、`Mindraft-AI-Reference.md` §7 |

---

## 关键约定

### 目录结构约定

```
notes-vault/
├── raw_notes/          ← 原始笔记（Obsidian 写入，绝对不修改）
├── ai_notes/           ← AI 处理结果（按类别存放）
│   ├── work/
│   └── life/
└── analysis/           ← 分析产物（JSON 文件）
    ├── memory.json
    ├── avatar_data.json
    └── relationships.json

mindraft/
├── config.yml          ← 主配置文件
├── run.py              ← CLI 入口
├── scripts/            ← Python 处理脚本
│   ├── llm/            ← LLM 抽象层
│   ├── process_notes.py
│   ├── note_filter.py  ← 笔记预筛选与批量分组
│   ├── analyze.py
│   ├── serve.py
│   ├── schemas.py      ← LLM 返回 JSON Schema
│   ├── prompts.py      ← Base Role 定义
│   └── utils.py        ← 原子写入、进程锁、token 估算、日志
├── skills/             ← AI Skill YAML 配置
└── dashboard/          ← 前端静态文件
```

### 命名约定

| 类别 | 可选值 |
|------|--------|
| LLM 提供者 | `kimi` \| `openai` \| `anthropic` \| `deepseek` |
| 渲染器类型 | `text_card` \| `pixel_art` \| `animated_sprite` \| `game` |
| 变化量级 | `micro` \| `macro` \| `transformation` |
| Memory 操作 | `APPEND_TO` \| `SET_IF_NEW`（仅这两种，其余忽略） |
| Token 估算 | `char_ratio`（默认）\| `tiktoken` |
| 笔记处理 | `skip`（预筛选跳过）\| `single`（独立处理）\| `batch`（合并处理） |

### 关键文件路径（运行时）

| 文件 | 路径 |
|------|------|
| 主配置 | `mindraft/config.yml` |
| 记忆状态 | `{notes_vault}/analysis/memory.json` |
| 形象数据 | `{notes_vault}/analysis/avatar_data.json` |
| 关联图谱 | `{notes_vault}/analysis/relationships.json` |
| AI 处理日志 | `{notes_vault}/analysis/process_log.jsonl` |
| 进程锁 | `{notes_vault}/analysis/.mindraft.lock` |
| 前端配置 | `mindraft/dashboard/data/config.json` |

---

## 待解决问题

> 每阶段结束后在此记录待确认问题，确认后标记解决。

（目前无待解决问题）

---

## 实现汇总历史

> 每阶段完成后，AI Agent 在此追加汇总，包括：完成内容、主要决策、遇到的问题、下一阶段建议。

（尚未开始实现）

---

### Phase 0 实现汇总（2026-07-25）

**完成内容**
1. 创建项目基础文件：`.gitignore`、`.env.example`、`requirements.txt`
2. 创建 `config.yml`：配置 notes-vault 路径、LLM provider、API keys、skill 开关、日志与 token 估算等
3. 搭建 LLM 抽象层：`scripts/llm/base.py`（抽象基类 + JSON 兜底解析）、`scripts/llm/kimi.py`、`scripts/llm/openai.py`、`scripts/llm/anthropic.py`、`scripts/llm_factory.py`
4. 创建基础设施 `scripts/utils.py`：配置加载（含 `${ENV}` 占位符解析）、`token_estimate()`、`safe_write_json()` 原子写入、`get_process_lock()` 进程锁、`setup_logging()` 日志初始化
5. 创建 `scripts/schemas.py`：`PROCESS_NOTE_SCHEMA`、`BATCH_PROCESS_SCHEMA`、`validate_llm_output()`
6. 创建 `scripts/prompts.py`：统一 Base Role 定义
7. 创建 `run.py` CLI 入口：支持 `--dry-run`、`--notes-only`、`--analyze`、`--serve` 参数，dry-run 不写入业务状态文件
8. 创建占位模块 `scripts/process_notes.py`、`scripts/analyze.py`、`scripts/serve.py`，确保 run.py 各模式可导入不崩溃
9. 修正 `scripts/llm/kimi.py` 的 base URL 为官方最新地址 `https://api.kimi.com/coding/v1`（同步更新 `doc/Mindraft-Technical.md` 示例）
10. 将验证脚本移入 `tests/` 目录：`tests/test_llm_mock.py`（mock 测试）、`tests/test_llm_real.py`（真实 API 测试）

**验证结果**
- `pip install -r requirements.txt` 成功
- `python run.py --dry-run` 成功执行，控制台与日志文件均有输出，未写入 `memory.json` 等业务状态文件
- 并发测试：第二个 `run.py` 实例被进程锁拒绝，退出码 1
- LLM 抽象层通过 mock 测试：文本对话、JSON 模式、markdown 代码块兜底解析均正常
- 真实 Kimi API 调用测试通过：文本对话与 JSON 模式均返回正常响应

**主要决策**
- `_resolve_env_placeholders()` 对未设置的环境变量保留原样，不强制所有 provider 的 key 必须同时存在，降低多 provider 配置门槛
- `llm_factory.py` 中 Anthropic provider 采用延迟导入，避免未安装 `anthropic` 包时模块级崩溃
- `setup_logging()` 在重复调用时清除旧 handler，防止日志重复输出
- Kimi base URL 确定为 `https://api.kimi.com/coding/v1`（已同步更新代码与 `doc/Mindraft-Technical.md`）

**待确认问题**
1. ✅ `notes_vault_path` 已确认：`~/Developer/GitHub/notes-vault` 正确
2. ✅ 验证脚本已移入 `tests/` 目录
3. ✅ 真实 Kimi API 调用测试通过，Phase 0 可进入人工审查

---

### Phase 1 实现汇总（2026-07-26）

**完成内容**
1. 创建 `skills/` 目录与 Skill 配置：`skills/note_style.yml`、`skills/tagging.yml`。
2. 创建 `scripts/skill_loader.py`：按 operation 与启用开关自动拼装 system prompt。
3. 重写 `scripts/prompts.py` 中 `NOTE_PROCESSOR_ROLE`：明确五域 `active_memory` 结构、合法 `memory_updates` 路径与操作、输出 JSON 格式。
4. 更新 `scripts/schemas.py`：`PROCESS_NOTE_SCHEMA` 增加 `title`、category 改为五域（`work|life|growth|wellbeing|identity`）、`memory_updates.action` 收紧为 enum、`tags` 增加英文小写连字符 pattern；移除 `related_notes`（Phase 5 使用）。
5. 调整 `config.yml`：`note_filter.batch_short_notes` 设为 `false`，明确 Phase 1 不做 batching。
6. 创建 `scripts/note_filter.py`：跳过空文件、过短内容、无自然语言笔记；`group_notes_for_processing` Phase 1 逐篇返回。
7. 扩展 `scripts/utils.py`：新增 `get_nested()` / `set_nested()` / `exists_nested()` 支持点号路径字典访问。
8. 重写 `scripts/process_notes.py`：
   - `create_initial_memory()`：五域硬编码结构。
   - `process_new_notes()`：扫描 → 过滤 → 逐篇 LLM 处理 → schema 校验 → 写入 `ai_notes/` → 应用 `memory_updates` → 更新 `tag_candidates` → 逐篇 checkpoint 持久化 `memory.json`。
   - `apply_memory_updates()`：仅 `APPEND_TO` / `SET_IF_NEW`，非法操作静默忽略并 warning。
   - `write_ai_note()`：按 `ai_notes/{category}/{slug}.md` 写入，重复文件名追加 `-2`、`-3`，不覆盖，frontmatter 含 `source`。
   - `update_tag_candidates()`：累计 `count`，`status` 固定 `pending`。
9. 更新 `run.py`：`--dry-run` 调用 `process_new_notes(dry_run=True)`；`--notes-only` 调用完整处理流程。
10. 创建 `tests/test_process_notes.py`：fixture mock 测试覆盖正常处理、dry-run 不写入、跳过笔记、失败重试四种场景。

**验证结果**
- `python tests/test_process_notes.py` 通过：ai_notes 输出、memory.json 更新、tag_candidates 累计、失败不标记均正常。
- `python tests/test_llm_mock.py` 通过，未破坏既有 LLM 抽象层测试。
- 使用真实 Kimi API 在临时 vault（2 篇笔记）上执行 dry-run，成功调用 LLM 并返回正确 category，未写入文件。
- 在真实 `notes-vault`（22 篇笔记）上执行 `python run.py --dry-run` 可达第 2 篇笔记处理，因 21 次 API 调用总耗时超过 300 秒前台超时；改为小批量验证后确认 pipeline 可用。

**主要决策**
- `active_memory` 采用硬编码五域：`work`、`life`、`growth`、`wellbeing`、`identity`；不允许 LLM 新增自定义域。
- `memory_updates` 使用点号路径，非法 action 静默忽略并记录 warning。
- `ai_notes/` 文件名由 LLM 生成英文 title 经 slugify 得到，重复时追加数字，Phase 1 不覆盖已存在文件。
- Phase 1 不做 batching、不做记忆压缩、不做 tag 升级、不处理 `related_notes`。
- 失败语义：单篇失败跳过，不标记为已处理，下次运行自动重试。

**遇到的问题**
- 真实 vault 22 篇笔记 dry-run 前台超时：API 调用顺序执行，总耗时超过 300 秒。计划在 Phase 2 考虑加入 rate/timeout 控制或允许用户分批处理，不作为 Phase 1 阻塞项。

**下一阶段建议**
- Phase 2：Dashboard MVP，优先做最小静态页面（笔记列表 + memory 摘要 + 每日一句），可视化图表可延后。

**待确认问题**
1. ✅ 五域 `active_memory` 结构已确认
2. ✅ `memory_updates` 路径与 action 语义已确认
3. ✅ `ai_notes/` 目录映射、文件名生成、覆盖策略已确认
4. ✅ 失败语义已确认
5. ✅ Tags Phase 1 只累计不升级已确认
6. ✅ `--dry-run` 调用 LLM 但不写入已确认

---

### Phase 2 实现汇总（2026-08-05）

**完成内容**
1. 扩展 `scripts/prompts.py`：新增 `DASHBOARD_SUMMARY_ROLE`，定义每日一句 + 五域摘要的生成任务，中文叙事风格。
2. 扩展 `scripts/schemas.py`：新增 `DASHBOARD_SUMMARY_SCHEMA`，校验 LLM 返回的 6 个字段。
3. 重写 `scripts/analyze.py`：
   - 读取 `memory.json`；不存在时回退到空结构。
   - 扫描 `ai_notes/` 生成 `recent_notes.json`（最多 10 篇，`processed_at` 取文件 mtime）。
   - 统计五域 category 文件数量生成 `stats.json`。
   - 调用一次 LLM 生成 `summaries.json`（每日一句 + 五域摘要 + `tag_candidates`）。
   - LLM 失败时 fallback，Dashboard 仍可启动。
   - dry-run 时调用 LLM 但不写入任何文件。
4. 创建 Dashboard 前端：
   - `dashboard/index.html`：暗色主题骨架，空状态提示。
   - `dashboard/style.css`：暗色主题、桌面优先、响应式卡片布局。
   - `dashboard/app.js`：异步加载 `data/config.json`、`summaries.json`、`stats.json`、`recent_notes.json` 并渲染。
5. 更新 `scripts/serve.py`：支持 `open_browser` 参数，启动 `http.server` 服务 `dashboard/` 目录。
6. 更新 `run.py` 命令语义：
   - 默认只处理新笔记。
   - `--analyze` 生成数据 + 启动服务器 + 自动打开浏览器。
   - `--serve` 只启动服务器，不生成数据。
   - `--dry-run` 不写入；`--analyze --dry-run` 不启动服务器/浏览器。
7. 更新文档：
   - `doc/Mindraft.md` §9 Phase 2 描述、§10 `run.py` 命令表。
   - `doc/Mindraft-AI-Reference.md` §7 Phase 2 状态。
   - `doc/Mindraft-Log.md` Phase 2 grilling 记录 + 本实现汇总。
8. 更新 `.gitignore`：排除 `dashboard/data/` 生成数据文件。

**验证结果**
- `python3 -m py_compile` 通过 `scripts/analyze.py`、`scripts/serve.py`、`run.py`。
- `python3 tests/test_process_notes.py` 与 `python3 tests/test_llm_mock.py` 通过，未破坏 Phase 1 功能。
- 使用 mock LLM 验证 `analyze.py` 端到端：正确生成 `summaries.json`、`stats.json`、`recent_notes.json`、`config.json`。
- 验证 `generate_dashboard_data(dry_run=True)`：调用 LLM 但不写入 `dashboard/data/`。
- `serve.py` smoke test：在临时端口上成功返回 `index.html` 且包含关键结构。
- 在临时测试 vault 上执行完整流程：`python run.py` 处理笔记 → `python run.py --analyze` 生成数据并自动打开浏览器，Dashboard 正确展示页眉、最后更新时间、每日一句、五域摘要卡片、tag 候选列表、最近 10 篇笔记列表。
- 空状态测试：`rm -rf dashboard/data` 后执行 `python run.py --serve`，页面显示「还没有生成 dashboard 数据」。
- LLM 失败 fallback 测试：临时改错 API key 后执行 `--analyze`，Dashboard 仍能启动并显示 fallback 提示。

**主要决策**
- Phase 2 采用最小静态 MVP：不做 Chart.js / 热力图，不做形象/压缩/跨周快照。
- 每日一句 + 五域摘要合并为一次 LLM 调用，prompt 硬编码在 `scripts/prompts.py`。
- 前端数据写入 `mindraft/dashboard/data/`，由 `.gitignore` 排除。
- `run.py` 默认只处理笔记，`--analyze` 负责生成数据并启动服务。
- LLM 失败时 Dashboard 仍可启动，显示 fallback 提示。
- `processed_at` 使用 `ai_notes/` 文件 mtime，避免回改 Phase 1 `memory.json` schema。

**遇到的问题**
- 无。

**下一阶段建议**
- Phase 3：记忆压缩机制、`analysis_style.yml` skill、MBTI 描述、Road Map Timeline、Chart.js 字数图/活跃日历、跨周快照 ADR-013。

**待确认问题**
1. ✅ Phase 2 范围边界已确认
2. ✅ 每日一句风格与五域摘要结构已确认
3. ✅ `run.py` 新命令语义已确认
4. ✅ 数据文件路径与 schema 已确认
5. ✅ ADR-013 跨周快照延后到 Phase 3 已确认

