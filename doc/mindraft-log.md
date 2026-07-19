# Mindraft — 实现日志

> 供 AI Agent 恢复上下文使用。每次实现中断前更新此文档，每次继续实现时先读取此文档。
> 产品文档：[# Mindraft.md](# Mindraft.md) · 技术参考：[Mindraft-Technical.md](Mindraft-Technical.md)

---

## 项目状态

**当前阶段**：Phase 0（未开始）
**实现方式**：Vibe-coding — AI 实现，人工审查 + 指挥
**最后更新**：2026-06-19

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
| **影响** | 所有业务代码只依赖 `BaseLLM`，不直接引用 DeepSeek / OpenAI 等具体实现 |
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
| Phase 0：基础骨架 | ⬜ 未开始 | — | `config.yml`、LLM 抽象层、`run.py` 骨架、基础设施（`utils.py`、`schemas.py`、`prompts.py`） |
| Phase 1：笔记处理核心 | ⬜ 未开始 | — | `process_notes.py`、`note_filter.py`、skill 系统、`memory.json` |
| Phase 2：Dashboard MVP | ⬜ 未开始 | — | `analyze.py`、Dashboard HTML/JS、`serve.py` |
| Phase 3：记忆系统完善 | ⬜ 未开始 | — | 记忆压缩、MBTI 描述、Road Map |
| Phase 4：用户形象 TextCard | ⬜ 未开始 | — | `avatar_data.json`、TextCardRenderer |
| Phase 5：笔记关联与链接增强 | ⬜ 未开始 | — | `relationships.json`、URL 摘要、关系图 |
| Phase 6：像素画形象 | ⬜ 未开始 | — | Replicate API、PixelArtRenderer |

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
| LLM 提供者 | `deepseek` \| `openai` \| `anthropic` |
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
