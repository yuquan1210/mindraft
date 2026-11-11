# Mindraft (涌现)
## 产品方案文档 v2.1

> 最后更新：2026-09-12
> 相关文档：[实现日志](mindraft-log.md) · Agent 入口：[../AGENTS.md](../AGENTS.md)

---

## 目录

1. [产品愿景](#1-产品愿景)
2. [系统架构](#2-系统架构)
3. [仓库与目录结构](#3-仓库与目录结构)
4. [技术选型](#4-技术选型)
5. [核心模块设计](#5-核心模块设计)
   - 5.1 [LLM 抽象层](#51-llm-抽象层)
   - 5.2 [Skill 配置系统](#52-skill-配置系统)
   - 5.3 [笔记处理流水线](#53-笔记处理流水线)
   - 5.4 [增量蒸馏记忆系统](#54-增量蒸馏记忆系统)
   - 5.5 [笔记关联关系](#55-笔记关联关系)
   - 5.6 [像素世界用户形象](#pixel-world-design)
6. [Dashboard 设计](#6-dashboard-设计)
7. [UI 风格定义](#7-ui-风格定义)
8. [数据流总览](#8-数据流总览)
9. [开发分阶段计划](#9-开发分阶段计划)
10. [run.py 入口设计](#10-runpy-入口设计)

---

## 1. 产品愿景

### 一句话描述

> 让 AI 成为你的第三方观察者——在你的日常碎片里，涌现出一个你从未完整见过的自己。

### 产品定位

Mindraft 不是笔记管理工具。笔记只是原材料。

真正的产品是：**一个持续运转的自我分析引擎**，它读你写下的每一句话，从第三方视角提炼规律、发现矛盾、生成洞见——最终让「自我认知」这件事变得自动化、可积累、可视化。

```
你只管写  →  Mindraft 负责观察  →  涌现出你自己
```

### 核心价值

**① 第三方视角**
你在写的时候，是第一人称的、碎片化的、情绪化的。
Mindraft 作为旁观者，以局外人的眼光重新审视这些文字，
找出你自己看不到的规律、盲点和变化。

**② 自我蒸馏**
不是整理笔记，而是从笔记中提炼「你是谁」——
你的工作状态、生活节奏、思维习惯、情绪信号，
随时间累积成一份专属于你的动态人格档案。

**③ 灵感激发**
当 AI 识别出你反复出现的需求、卡点或热情时，
它会主动提问、关联笔记、建立连接——
帮你把模糊的感觉变成清晰的想法，把想法变成可以行动的方向。

**④ 形象涌现**
你的数字形象不是一次性生成的，
它随每一篇新笔记缓慢进化——心情、场景、道具、气质，
像真实的你一样，每天都有细微的变化。

**⑤ 私人 AI 培养**
当下 AI 的本质是语言文字分析。
把你的日常信息文本化，持续输入大模型，
就是在培养一个越来越懂你的私人 AI——
笔记写得越多，它就越像你、越了解你。

### 设计原则

| 原则 | 说明 |
|------|------|
| 写作零负担 | 不改变 Obsidian 写作习惯，笔记随意记录即可 |
| 原文不可侵犯 | raw_notes 永远保持原样，AI 产物单独存放 |
| 记忆只增不减 | 任何历史信号永不删除，只会被归档或压缩 |
| 形象只进化不重置 | 数字形象在现有基础上演化，保留完整的历史轨迹 |
| LLM 可替换 | 不绑定任何一家模型，通过配置一键切换 |
| Skill 可扩展 | AI 行为规则通过配置文件管理，无需改动代码 |
| 画像渲染可替换 | 数据与渲染方式分离，切换表现形式只改一行配置 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     用户端                               │
│   Obsidian (写作) ──► Local Directory ──► GitHub (同步)  │
│                        notes-vault/                      │
└──────────────────────────┬──────────────────────────────┘
                           │
                    python run.py
                    (本地手动触发)
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    处理层 (Python)                        │
│                                                          │
│   skill_loader.py  →  拼装 system prompt                 │
│         ↓                                                │
│   process_notes.py →  读取 raw_notes                     │
│         ↓                                                │
│   llm_factory.py   →  调用 Kimi / OpenAI / Claude       │
│         ↓                                                │
│   ① 写入 ai_notes（分类 + 链接 + 追问标记）               │
│   ② 更新 memory.json（蒸馏记忆）                         │
│   ③ 笔记关联（Phase 5，MVP 后）                   │
│   ④ 更新 scene_state.json（Phase 4）                 │
│         ↓                                                │
│   analyze.py       →  生成 dashboard/data/*.json         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              展示层：本地 Web Dashboard                   │
│              http://localhost:8765                       │
│                                                          │
│   最近笔记 │ 五域摘要 │ 每日一句                        │
│   性格侧写 │ Road Map │ 单一像素世界（Phase 4）           │
│                                                          │
│   画像渲染层（可替换）：                                   │
│   PixelWorldRenderer（场景 JSON 与引擎解耦）     │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 仓库与目录结构

### 双 Repo 架构

```
┌──────────────────────────┐     ┌──────────────────────────────┐
│   Repo 1: notes-vault    │     │  Repo 2: mindraft            │
│   (Obsidian 管理)         │     │  (产品代码)                   │
│                          │     │                              │
│   raw_notes/             │◄────│  config.yml 配置路径          │
│   ai_notes/              │     │  scripts/ 读写此目录          │
│   .mindraft/ (隐藏目录)   │     │  logs/ 运行日志               │
└──────────────────────────┘     └──────────────────────────────┘
         ↑
    GitHub 同步
   （Obsidian 插件）
```

### Repo 1：notes-vault

```
notes-vault/
│
├── raw_notes/                    # Obsidian 原始输入，只写不改
│   ├── 2026-06-15.md
│   └── 2026-06-14.md
│
├── ai_notes/                     # AI 处理后，自动归类
│   ├── work/
│   │   ├── daily/
│   │   ├── epic_and_cards/
│   │   ├── tips/
│   │   └── publish/
│   ├── growth/
│   └── life/
│       ├── workout/
│       └── cooking/
│
└── .mindraft/                    # AI 分析产物（隐藏目录，非笔记；ADR-014）
    ├── memory.json               # 蒸馏记忆（核心状态文件，含 history_archive 统一归档）
    ├── relationships.json        # Phase 5 规划，MVP 后
    └── scene_state.json          # Phase 4B/C 规划，像素世界权威状态
```

> 运行日志与进程锁不在笔记仓库：`mindraft/logs/process_log.jsonl`、`mindraft/.mindraft.lock`。

### Repo 2：mindraft

```
mindraft/
│
├── skills/                       # AI Skill 配置文件
│   ├── note_style.yml
│   ├── summary_style.yml
│   ├── tagging.yml
│   ├── analysis_style.yml
│   ├── memory_compression.yml
│   └── json_output.yml
│
├── scripts/
│   ├── llm/                      # LLM 抽象层
│   │   ├── base.py
│   │   ├── kimi.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   └── deepseek.py
│   ├── llm_factory.py
│   ├── skill_loader.py           # Skill 加载与 prompt 拼装
│   ├── process_notes.py          # 笔记处理 + 记忆更新
│   ├── note_filter.py            # 笔记预筛选与批量分组
│   ├── analyze.py                # 生成 dashboard 数据 + 画像数据
│   ├── serve.py                  # 启动本地服务器
│   ├── schemas.py                # LLM 返回的 JSON Schema 校验
│   ├── prompts.py                # Base Role 定义
│   └── utils.py                  # 原子写入、进程锁、token 估算、日志
│
├── dashboard/                    # 前端静态文件
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── renderers/                # 画像渲染插件（可替换）
│   │   ├── base_renderer.js          # Phase 4A，最小生命周期接口
│   │   └── pixel_world_renderer.js   # Phase 4A（Kaplay.js 像素小人世界）
│   ├── vendor/                   # 前端依赖本地副本（Kaplay.js，Phase 4A）
│   ├── assets/                   # 像素素材图集（最小示例入库，外部素材按许可，Phase 4A）
│   │   └── assets_manifest.json  # 素材清单（AI 导演的可用资源目录）
│   └── data/                     # analyze.py 输出，JS 直接读取
│       ├── config.json            # 前端配置（含 memory_hash）
│       ├── stats.json             # 字数 / 日历数据
│       ├── summaries.json         # 每日摘要
│       ├── recent_notes.json      # 最近处理笔记列表
│       ├── roadmap.json           # 归档历史时间轴（已实现，ADR-016 单数据源）
│       ├── profile.json           # 已实现的性格侧写
│       └── scene.json             # 像素世界场景剧本（Phase 4B/C 规划）
│
├── config.yml                    # 配置文件
├── run.py                        # 一键入口
└── README.md
```

---

## 4. 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 笔记编写 | Obsidian | 现有工具不变 |
| 版本存储 | GitHub | 历史追溯，免费 |
| 处理脚本 | Python 3.11+ | vibe coding 友好，库丰富 |
| LLM（默认） | DeepSeek API | 速度快、成本低，OpenAI 兼容接口 |
| LLM（备选） | Kimi / OpenAI / Anthropic | 通过 config.yml 一键切换 |
| 前端 | 原生 HTML + CSS + JS | 零框架，直接上手 |
| 图表库 | Chart.js（CDN 引入） | 无需安装，一行引入 |
| 本地服务 | Python `http.server` | 内置模块，无需安装 |
| 像素世界渲染（Phase 4） | Kaplay.js（vendor 本地引入） | 轻量 2D 游戏引擎，原生支持 Aseprite 图集 |
| 像素素材（Phase 4） | 随包最小素材 + 可选外部素材 | manifest 编目；默认可离线复现，Aseprite 可选 |
| IDE | VS Code + Claude Code | 适合 vibe coding |

### config.yml 关键配置项

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `notes_vault_path` | 笔记仓库本地路径 | `~/Developer/GitHub/notes-vault` |
| `llm_provider` | 切换 LLM 的唯一入口 | `kimi \| openai \| anthropic \| deepseek` |
| `pixel_world.enabled` / `pixel_world.renderer` | Phase 4A 待实现；控制世界展示与渲染器 | `true` / `pixel_world` |
| `memory.active_memory_token_threshold` | 触发记忆压缩的 token 阈值 | `1500` |
| `memory.original_zone_tokens` | 原文区保留的最新观察 token 数（不参与浓缩） | `300` |
| `memory.condensed_zone_token_budget` | 浓缩区子预算，超出则整体再浓缩 | `900` |
| `token_estimation` | Token 估算方式 | `char_ratio \| tiktoken` |
| `note_filter.min_meaningful_chars` | 笔记最低有效字符数 | `20` |
| `note_filter.batch_char_threshold` | 短笔记合并阈值 | `200` |
| `logging.level` | 日志级别 | `INFO` |

→ 完整配置示例：`config.yml`

---

## 5. 核心模块设计

### 5.1 LLM 抽象层

通过统一接口抽象所有 LLM，切换模型只需修改 `config.yml`，代码零改动。

```
scripts/llm/
├── base.py          # 抽象基类，定义统一接口
├── kimi.py          # Kimi 实现（OpenAI 兼容接口）
├── openai.py        # OpenAI 实现
├── anthropic.py     # Claude 实现
└── deepseek.py      # DeepSeek 实现
```

→ 实现代码：`scripts/llm/` 与 `scripts/llm_factory.py`

---

### 5.2 Skill 配置系统

#### 设计思路

```
System Prompt = 角色定义 + 记忆摘要 + 挂载的 Skill 规则集

每个操作声明需要哪些 skill
    → skill_loader 自动查找并拼装
    → 无需手动维护 prompt 字符串
    → 新增 skill 只需新建 .yml 文件，声明 applies_to
```

#### Skill 文件格式

每个 skill YAML 文件声明名称、适用操作（`applies_to`）、和规则列表（`rules`）。`skill_loader.py` 根据当前 operation 自动找出并挂载适用的 skill。

→ 所有 skill 文件示例：`skills/`

#### Skill 与操作的对应关系

| 当前操作 | 挂载的 Skill | 输出 |
|------|-------------|------|
| `process_note` | `note_style` + `tagging` + `json_output` | 拆分笔记 + 记忆更新 |
| `dashboard_summary` | `summary_style` + `analysis_style` | 每日洞察、五域摘要、性格侧写（同一次调用） |
| `compress_memory` | `memory_compression` | 五域浓缩字符串 |

> 链接增强和像素场景导演是后续规划操作，尚未接入。`profile.json` 当前由 `dashboard_summary` 拆出，不额外调用 `generate_profile` 或 `generate_mbti_description`。

→ 实现代码：`scripts/skill_loader.py`

---

### 5.3 笔记处理流水线

#### 流程概览

```
run.py（在此获取进程锁，防止并发执行；--dashboard 模式不获取）
  │
  └─► process_notes.py
        │
        ├── 扫描 raw_notes/
        ├── 对比 memory.meta.processed_notes（找出未处理的笔记）
        │
        ├── [预筛选] 跳过无意义笔记：
        │     · 空文件
        │     · 低于 min_meaningful_chars 字符的笔记
        │     · 仅包含无法理解的代码片段（无自然语言文字）
        │     → 标记为已处理，记录跳过原因，不调用 LLM
        │
        ├── [分组] 当前逐篇独立处理；
        │     短笔记合并为一批（一次 LLM 调用）是 Phase 1 延后项
        │
        └── for each 组（按文件名升序）：
              │
              ├── 1. 加载 memory.json 中的 active_memory
              ├── 2. build_system_prompt("process_note", base_role)
              ├── 3. 调用 LLM：active_memory + 笔记原文
              ├── 4. JSON Schema 校验 LLM 返回结果
              ├── 5. 解析 JSON 返回：
              │       domain + subcategory（join 为 category）,
              │       tags, summary,
              │       rewritten_content,
              │       memory_updates
              │       （questions 字段保留在契约中，当前代码不消费；
              │         追问实际由 note_style 规则以 <!-- ❓ --> 注释内嵌正文实现）
              │
              ├── 6. 在候选副本上应用 memory_updates、标签与处理状态
              ├── 7. 写入 ai_notes/{category}/{title-slug}.md（重名追加 -2、-3）
              ├── 8. 将笔记名加入 memory.meta.processed_notes
              ├── 9. 原子写入 memory.json（逐篇 checkpoint，确保断点可恢复）
              │
              └── 10. if token_estimate(active_memory) > threshold:
                          compress_memory()（Phase 3 已实现）
```

#### AI 处理后笔记的 frontmatter 格式

```markdown
---
title: "Auth Redesign Notes"
processed_at: 2026-06-15T14:30:00
category: work/daily
tags: [backend, sprint]
summary: "今天完成了登录模块的代码审查，发现权限设计有漏洞"
source: raw_notes/2026-06-15.md
part: 1/2
---

...（AI 对原始笔记的清晰重写版本：结构化表达，补充必要背景知识）...

> 📎 [来源标题](https://example.com)：（该 URL 对应内容的摘要）

<!-- ❓ 待补充：这里提到的"权限漏洞"具体是哪种场景？AI 无法从现有上下文推断，请补充更多信息。 -->
```

> frontmatter 字段与 `write_ai_notes()` 实际输出一致；`related`（关联笔记列表）属 Phase 5 规划，当前不写入。

#### Tag 创建规则

```
候选阶段：每篇拆分后的 ai_note，AI 提出 ≤3 个候选 tag
          → 立即写入该篇 ai_note 的 frontmatter
          → 同时存入 memory.tag_candidates；每个 tag 在同一原笔记内去重后累计 count

升级规则（Phase 3 已实现）：
          当 tag_candidates 中某个 tag 的 count ≥ 3
          → status 升级为 "active"

目的：防止 tag 爆炸，确保每个 tag 都有足够的代表性
```

#### 笔记重写规则

AI 对原始笔记的核心处理是**重写**，而非仅整理或追加。

```
预筛选规则（在调用 LLM 之前，由代码判断）：
  · 空文件 → 跳过，标记为已处理，记录跳过原因
  · 字符数 < min_meaningful_chars (20) → 跳过
  · 去除代码块后无自然语言文字（< 10 字符）→ 跳过
  · 当前所有有效笔记逐篇独立处理；短笔记（≤ 200 字符）合并批处理（最多 5 篇、一次 LLM 调用）是 Phase 1 延后项，尚未实现

重写目标：将潦草、碎片化的原始笔记，重写为清晰、结构化、易读的版本

重写原则：
  · 保留原文所有核心信息，补充可从上下文或 AI 知识合理推断的背景
  · 如涉及代码/技术内容，格式化为规范的 markdown 代码块
  · 笔记中的 URL → 抓取页面内容 → 生成摘要 → 以引用块追加（Phase 5 规划，当前仅作为 skill 规则文本存在，无抓取代码）
    格式：> 📎 [页面标题](url)：内容摘要

无法推断内容的处理（禁止幻觉）：
  · AI 无法从已有知识推断的内容 → 添加注释要求作者补充
    格式：<!-- ❓ 待补充：[具体不清楚的点]，请作者补充更多信息。 -->
  · 严禁猜测或杜撰任何事实，宁可留空 + 追问，不可胡编乱造

原始笔记处理：
  · raw_notes/ 中的原始文件保持原样，永不修改
  · ai_notes/ 中只存放重写后的版本
  · Dashboard 不展示 raw_notes，只使用 ai_notes 内容
```

---

### 5.4 增量蒸馏记忆系统

#### 核心原则

```
LLM 每次处理笔记时，只看两样东西：
  ① active_memory（压缩的历史记忆，规模由 config 阈值控制，默认 1500 tokens）
  ② 当前这一篇新笔记（~100-200 字）

处理后更新 active_memory，而不是堆积原文
→ 历史上下文不随笔记总数线性增长；阈值是软目标，超长新笔记、原文保留和压缩失败均可能暂时超标
```

#### 双层记忆结构

```
memory.json
│
├── active_memory  (热层)
│     · 每次处理笔记时发给 LLM
│     · 超过阈值（config: memory.active_memory_token_threshold，默认 1500 tokens）时压缩
│     · 五域字段保留近期原文；_condensed 保存较早观察的浓缩字符串
│     · 热层可压缩，历史完整性由 history_archive 快照保证
│
└── history_archive  (冷层)
      · 永久追加，从不删除
      · 不发给 LLM（不占 token）
      · Road Map / Timeline 的数据来源
      · 每次压缩前，将 active_memory 完整归档于此
```

#### memory.json 示例（字段定义以代码为准）

```json
{
  "meta": {
    "version": 47,
    "last_updated": "2026-06-15",
    "processed_notes": [
      "2026-06-01.md",
      "2026-06-14.md",
      "2026-06-15.md"
    ],
    "active_memory_token_estimate": 620
  },

  "active_memory": {
    "work": {
      "current_focus": "登录模块重构，卡在权限设计上",
      "ongoing_projects": ["认证系统", "dashboard迁移"],
      "goals": [],
      "energy_pattern": "",
      "stress_sources": [],
      "recurring_signals": [
        "容易在细节上花过多时间",
        "喜欢在写代码前先理清思路"
      ],
      "recent_mood_trend": "疲惫但有动力，本周略有改善"
    },
    "life": {
      "current_routines": ["早上健身", "周末做饭"],
      "interests_observed": ["电影", "编程", "烹饪"],
      "social_connections": [],
      "places": [],
      "important_people": [],
      "recurring_signals": ["睡眠不规律是持续困扰"],
      "recent_mood_trend": ""
    },
    "growth": {
      "learning_topics": ["系统设计"],
      "active_skills": [],
      "challenges": [],
      "recurring_signals": []
    },
    "wellbeing": {
      "physical_patterns": [],
      "mental_patterns": [],
      "recovery_activities": ["健身"],
      "recurring_signals": []
    },
    "identity": {
      "core_traits": [
        "偏内向，独处时恢复能量",
        "目标感强，对自身完美主义有自我觉察"
      ],
      "values": [],
      "self_perception": [],
      "mbti_hints": [],
      "recurring_signals": []
    }
  },

  "tag_candidates": {
    "backend":       { "count": 5, "status": "active" },
    "sprint":        { "count": 3, "status": "active" },
    "side-project":  { "count": 2, "status": "pending" }
  },

  "history_archive": [
    {
      "archived_at": "2026-06-07",
      "iso_week": "2026-W23",
      "trigger": "compression",
      "note_count_at_time": 31,
      "snapshot": {
        "work": { "current_focus": "...", "ongoing_projects": ["..."] },
        "life": {},
        "growth": {},
        "wellbeing": {},
        "identity": {}
      }
    }
  ]
}
```

> Phase 3 还保存 `active_memory._condensed`（五域浓缩字符串）、`original_order`（原文观察追加顺序，不发送给 LLM）与 `meta.weekly_checkpoint`（周快照去重游标）。初始结构和兼容读取见 `memory_state.py`，校验见 `schemas.py`。

> `trigger` 取值：`compression`（压缩前的归档）/ `weekly`（检测到跨周时的纯拷贝快照，热层不变，零 LLM）。统一归档设计见 ADR-016（取代 ADR-013，不再有独立 `snapshots/` 文件）。

#### 追加更新规则

LLM 返回的 `memory_updates` 只允许两种操作，任何 DELETE / OVERWRITE 直接忽略：
- `APPEND_TO`：向已定义的字符串数组追加新字符串（仅忽略大小写和空白相同的重复项；保留相似但矛盾或更具体的观察）
- `SET_IF_NEW`：已定义的字段不存在或值为空（空串/空列表）时才写入，字段类型必须匹配

**Role Prompt 中固定的约束（代码同时校验路径和类型）：**

> 你只能追加新的观察，不能修改或删除已有内容。
> 如果新笔记与已有记忆存在矛盾，用 APPEND_TO 追加新信号，而不是覆盖旧信号。
> 矛盾本身也是有价值的历史信息。

→ 实现代码：`scripts/process_notes.py`、`scripts/note_filter.py`、`scripts/schemas.py`、`scripts/prompts.py`

#### 压缩触发与执行（Phase 3 已验收）

active_memory 分两个区（2026-08-18 grilling 第二轮决策）：

- **原文区**：最新的观察，逐字保留、不参与压缩，约 300 token（`memory.original_zone_tokens`）。近期观察零漂移由结构保证
- **浓缩区**：较早观察的 LLM 浓缩产物，子预算约 900 token（`memory.condensed_zone_token_budget`）

触发条件：每篇笔记 checkpoint 后检查，热层总 token 估算 > `memory.active_memory_token_threshold`（接受粗估，不按 provider 校准）。

执行（一次批次浓缩，必要时一次浓缩区治理 + 一次原子写入；每次 LLM 调用最多重试一次）：
1. 原文区只保留最新 300 token，其余作为一个批次交给 LLM 浓缩，结果追加进浓缩区（不预估浓缩比、不多轮）；
2. 浓缩区若超出 900 token 子预算，整体再浓缩一轮——老内容允许重复浓缩、缓慢漂移，接受为特性（人对自我的认知本就近重远轻）；
3. 向 `history_archive` 追加 `trigger: "compression"` 条目（归档），与热层替换在**同一次 `safe_write_json()` 原子写入**中完成；LLM 失败则 memory.json 无任何变化，记 error，下次运行重试。

目标：热层降回阈值 × `memory.compression_target_ratio`（默认 0.55）；仍未达标则接受现状 + 记 warning，不做压缩循环。

职责划分：正确性由归档保证（纯拷贝，「只增不减」的落点），压缩只负责热层质量——「不丢信号」不是验收承诺，测试断言结构合法 + token 达标，蒸馏质量人工抽查。

#### 各阶段记忆状态预估

| 阶段 | active_memory | history_archive | 每次 LLM 输入 token |
|------|--------------|-----------------|-------------------|
| 第 1-20 篇笔记 | 逐渐增长 | 空 | ~300-1500 |
| 触发第一次压缩 | 降至阈值 × 0.55 | 1 条归档 | 阈值内 |
| 第 500 篇笔记 | 通常回到阈值附近，允许暂时超标 | N 条归档 | 不随历史笔记数线性增长 |

---

### 5.5 笔记关联关系

> 本节整体为 Phase 5 规划，当前代码不写入 `related` frontmatter 与 `relationships.json`。注意示例中的文件名（如 `2026-06-15.md`）是早期设计，实际 ai_notes 文件名为 title slug。

#### 关联写入格式

```markdown
<!-- ai_notes/work/daily/2026-06-15.md -->

> 🔗 相关笔记：[[auth-redesign]] · [[permission-patterns]]
```

#### relationships.json 结构

```json
{
  "work/daily/2026-06-15.md": {
    "related": [
      {
        "note": "work/epic_and_cards/auth-redesign.md",
        "strength": "high",
        "reason": "同一个认证模块项目的延续"
      },
      {
        "note": "work/tips/permission-patterns.md",
        "strength": "medium",
        "reason": "涉及相同的权限设计主题"
      }
    ]
  }
}
```

#### 关联强度规则

| 强度 | 判断条件 | 动作 |
|------|---------|------|
| `high` | 同一项目/事件的直接延续 | 写入 wiki 链接 + relationships.json |
| `medium` | 相同主题但不同事件 | 只写入 relationships.json |
| `low` | 宽泛主题相似 | 忽略 |

---

<a id="pixel-world-design"></a>

### 5.6 像素世界用户形象（Phase 4 MVP，尚未实现）

> 2026-09-12 ADR-019：像素世界直接替代原 Text Card 形象方案。Work Me / Home Me 移至未来目标，不生成双画像、不做双场景切换。既有 `profile.json` 性格侧写保留，它不是被取消的 Text Card 渲染器。

#### 最小闭环与依赖

```text
已有 active_memory（五域原文 + _condensed）
    + 精简素材 manifest + 当前 scene_state 的可见状态
    → Python 场景导演（BaseLLM + skill + schema + 语义校验）
    → scene_state.json（单一权威状态，含演化记录）
    → dashboard/data/scene.json（可重新导出的渲染投影）
    → PixelWorldRenderer（本地 Kaplay，单角色、单房间）
```

不需要 `avatar_data.json` 中间层，不额外生成一套人格画像，也不依赖尚不存在的 `assess_change_magnitude()` / `evolve_avatar()`。场景表达综合五域观察，不把 work/life 分类映射为两个人格。后端与渲染通过版本化 Scene JSON 解耦；MVP 只实现一个渲染器，不为了可替换性先做第二个渲染器。

#### MVP 范围与预算

| 项目 | MVP 约束 |
|------|----------|
| 世界 | 一个固定布局的 16×12 网格房间，一个固定角色；固定地板/墙壁 |
| 物件 | 最多 8 个预定义槽位，槽位与交互站点由代码定义；LLM 只能选 manifest 内的道具 |
| 基础动作 | `walk_to`（合法站点）、`wait`、`emote`、`interact`；不执行生成的代码 |
| 剧本 | 最多 12 步；wait/interact 为 0.5–10 秒，行走有超时；正常一轮目标 ≤60 秒，结束可安全回到起点再循环 |
| 文本 | 一句状态说明和一句气泡，各 ≤60 字；无新证据时允许保持原样 |
| 外观 | 固定 skin；不推测用户真实相貌，不做部件拼装与人生阶段换装 |
| 交互 | 仅观看，可暂停/恢复；无用户操控、任务系统、NPC、音乐或物理模拟 |
| 素材 | 仓库自带可分发的最小示例素材和来源/许可记录；用户素材包可选，不作为跑通 MVP 的前置条件 |

以上数值是可验收的初始实现上限；验收前调整需同步 schema、测试和文档。素材美术精度可迭代，不阻塞功能闭环。

#### 数据契约与执行职责

| 产物 | 内容与职责 |
|------|------------|
| `dashboard/assets/assets_manifest.json` | 版本、资源 id、相对路径、尺寸、动画名、物件槽位类型、可用交互动作；AI 只接收筛选过的目录，不接收图片或全部资源路径 |
| 固定基础场景 fixture | 网格、阻挡格、角色 skin、起点、槽位与合法站点；纳入版本控制，4A 用它在无 AI 时展示明确标注的示例 |
| `{vault}/.mindraft/scene_state.json` | `schema_version`、`revision`、`input_hash`、manifest 版本、稳定角色 id、当前房间/物件、剧本、状态文本、生成时间、追加式 `evolution_log` |
| `dashboard/data/scene.json` | 仅渲染需要的当前状态与版本/说明，不含历史记忆、原笔记、API key、完整演化日志 |
| `scripts/scene.py`（规划） | 输入摘要、触发判断、调用导演、校验、在副本上应用变更、原子保存、场景投影导出 |
| `pixel_world_renderer.js`（规划） | `mount(container, scene, manifest)` / `update(scene)` / `destroy()`；只解释数据，不修改后端状态 |

后端分配稳定物件 id（基于槽位），LLM 不得重定义角色 id、房间尺寸、地形、资源路径或版本。4B 的导演输出为受限的 `activity`、`emote`、`bubble`、`description` 及最多 12 步剧本；4C 再增加 `add_prop(slot_id, asset_id)`，最多每次新增一个物件。不允许通用 JSON Patch、DELETE、任意坐标或任意动作。保留旧物件，满槽后仍可更新行为，不继续累积可见物件。

JSON Schema 校验类型、枚举、长度、数量；语义校验必须验证资源存在、动画/交互受素材支持、槽位兼容且未占用、站点可达、整个剧本及循环回程可执行。16×12 固定网格用确定性 BFS 寻路；路径由代码计算，不由 LLM 猜。运行时超时或资源加载失败进入 idle/静态状态，不阻塞其他卡片。

#### 更新、缓存和故障恢复

- 首次无状态：代码建立基础房间和固定角色；有非空观察（而非仅有空的五域字典）才调用导演进行初始行为设置（Genesis）。记忆为空时显示明确标注的示例/等待状态，不编造用户画像。
- 后续有变化：比较独立的场景 `input_hash`（active_memory + manifest 版本 + 场景 schema/导演规则版本），在已有场景上应用允许的更新。压缩可能改变表达并触发一次更新，但不意味着必须增加道具。
- 输入不变：零场景 LLM 调用。变化时最多一次逻辑导演调用（校验或调用失败只重试一次），与现有摘要调用独立；不读取原笔记全集或演化历史作为输入。
- 成功：一次 `safe_write_json()` 同时写入新状态、成功输入 hash 和演化记录，再导出 scene.json。先验证完整候选，再写磁盘；全量重建不由 LLM 或“重大生活转变”自动触发。
- 失败：保留旧状态、旧 hash 和旧导出，下次分析重试；首次生成失败使用基础示例。坏状态文件不视为“首次运行”，明确报错并保留现场。
- 导出中断：磁盘 state 是权威来源，scene.json 缺失/版本不符时无需 LLM 即可重导出。素材版本不兼容时不自动重置，先提示更换回兼容素材/执行明确迁移。
- 历史：`evolution_log` 追加实际成功的变更和输入 hash；不将旧记录发送给 LLM。MVP 不做回放功能，也不把场景历史混入记忆 `history_archive`。

`--analyze` 和默认流程在同一进程锁内更新场景；`--dry-run` 使用当前模拟记忆调用导演但不写 scene_state/scene；`--dashboard` 仅展示已有场景或随包示例。像素世界开启后，缺 scene.json 只触发场景修复，不让已有 summaries/profile 被迫重新调用 LLM。`--rebuild` 在 Phase 4 接入时明确扩展为一并清理 scene_state，重新创建世界；普通失败绝不建议用 rebuild 兜底。

#### 技术可行性与落地门槛

现有 Python 状态写入、filelock、BaseLLM、skill loader、校验重试和本地 HTTP 服务可以复用。尚无场景代码、渲染器或素材，因此 4A 必须先完成离线可运行的竖向原型，再接 AI。

KAPLAY 官方文档提供 sprite/图集与 Aseprite 导出加载接口，可用于这一规模的场景；Aseprite 不是必须采购的工具，普通 PNG sprite sheet 即可开始。引擎能力依据：[官方 API 文档](https://kaplayjs.com/docs/api/reference/)。实施时固定经验证的稳定版本，vendor 构建产物并保留许可证，不依赖 CDN 或开发预览版。

| 风险 | 收敛办法 / 验收门槛 |
|------|--------------------|
| 素材尺寸/动作不统一 | 4A 先用一套小素材验证 idle、walk、一个交互；manifest 缺动作时禁用相应能力 |
| LLM 生成不可执行的场景 | 固定房间/槽位，资源与动作白名单，完整候选语义校验，失败回退 |
| 仅装饰、与笔记无关联 | 用工作专注、运动恢复、学习阅读三类 fixture 及真实记忆人工抽查行为/气泡是否有依据；不验收“准确人格诊断” |
| 每次运行重建/重复新增 | 稳定 id + 持久状态 + hash + add_prop 幂等与满槽用例 |
| 浏览器循环泄漏或卡死 | 页面隐藏时暂停，destroy 释放引擎/事件/计时器；连续播放 10 分钟及重复更新 20 次无重复实例、未捕获异常或动作死锁 |
| AI 调用失败影响笔记主链路 | 场景为独立可失败阶段；失败后已处理笔记、记忆和现有 Dashboard 仍可用 |

---

## 6. Dashboard 设计

> Dashboard 展示 ai_notes 中的重写内容和分析产物，不直接展示 raw_notes 原始笔记。

### 组件总览

| 组件 | 描述 | 数据来源 |
|------|------|---------|
| 字数趋势图（未来） | 最近 7 天每天笔记总字数柱状图 | `stats.json` |
| 活跃日历（未来） | 类 GitHub 热力图，最近 12 周 | `stats.json` |
| 每日一句 | 当天（或最近一篇）笔记摘要 | `summaries.json` |
| MBTI 风格描述 | 基于 active_memory 的长期性格侧写 | `profile.json` |
| Road Map Timeline | 以周为节点的状态变化轨迹 | `roadmap.json` |
| 像素世界（Phase 4 MVP） | 单角色、单房间的记忆驱动形象 | `scene.json` |

### 组件详细设计

#### 字数趋势图

```
类型：柱状图（Chart.js Bar）
数据：最近 7 天，每天所有笔记的总字数
X 轴：日期（Mon / Tue / Wed...）
Y 轴：字数
颜色：渐变紫/蓝，极简风格
无笔记的天：柱高为 0，颜色置灰
```

#### 活跃日历

```
类型：热力图（自定义 CSS Grid）
范围：最近 12 周（84 天）
颜色深浅：对应当天笔记字数多少（4 级）
无笔记：空白格
有笔记：紫色系，字数越多颜色越深
Hover：显示日期 + 当天字数 + 摘要
```

#### MBTI 风格描述

```
输出示例：
"最近的你像一个在迷雾中摸索路径的建筑师——
 工作上高度专注，有明确的目标感，但对细节的执着
 偶尔让你陷入过度思考。生活中你正在寻找某种节奏感，
 健身和阅读是你给自己的喘息空间。"

更新频率：active_memory 变化或契约文件缺失时，与 summaries 共用一次 LLM 调用
数据来源：memory.active_memory
```

#### Road Map Timeline

```
形式：横向时间轴，每周一个节点
节点显示：截至归档时累计笔记数量 + 最多三条快照观察
Hover 展示：
  - 时间范围（如 Jun 8 - Jun 14）
  - 累计笔记数量（既有归档不提供可靠的当周篇数）
  - 模板生成的状态描述
  - 主要 tag
数据来源：history_archive 单数据源（ADR-016，trigger ∈ {weekly, compression}，
          节点按 archived_at 排序，同一周允许两类节点并存）

快照生成时机：检测到跨越自然周时自动追加 trigger="weekly" 归档条目
              （纯数据拷贝，零 LLM，不依赖"周末执行"）
早期数据保障：即使未触发过记忆压缩，weekly 条目也会独立生成，
              确保 Road Map 在早期不会空白
```

#### 像素世界窗口（Phase 4 MVP）

Dashboard 只增加一个世界窗口，展示一个角色、固定房间、气泡及一句状态说明；支持暂停/恢复。初始示例、生成失败和加载失败均有明确提示，其余卡片继续可用。既有性格侧写不删除，也不作为新世界渲染的依赖。

Work Me / Home Me 的划分、左右双卡和双场景切换均不属于 MVP。未来需要时再扩展同一用户的场景视角。

---

## 7. UI 风格定义

```
设计语言：Minimal Premium（极简高级）
参考：Linear.app / Craft.do / Raycast
模式：Dark Mode 优先
```

### 配色方案

| 变量 | 色值 | 用途 |
|------|------|------|
| `--bg-base` | `#0a0a0a` | 页面背景 |
| `--bg-card` | `#111111` | 卡片背景 |
| `--border` | `#222222` | 边框 |
| `--accent` | `#a78bfa` | 主色（紫） |
| `--text-primary` | `#e5e5e5` | 主文字 |
| `--text-secondary` | `#666666` | 次要文字 |
| `--success` | `#4ade80` | 有笔记标记 |

→ CSS 完整代码：`dashboard/style.css`

### 字体

Inter（Google Fonts CDN 引入，weight: 300 / 400 / 500），fallback 为 `system-ui`。

### 设计原则

```
· 大量留白，不做满版排版
· 卡片圆角：8px
· 阴影：subtle，不使用强阴影
· 动效：200ms fade-in，无炫技动画
· 字号层级清晰：标题 / 正文 / 次要 三级
```

---

## 8. 数据流总览

```
run.py 执行
    │
    ├─► [扫描] 找出 raw_notes/ 中未处理的笔记
    │          （对比 memory.meta.processed_notes）
    │
    ├─► [预筛选] 跳过无意义笔记；有效笔记逐篇处理
    │          · 空文件 / 低于 min_meaningful_chars / 无自然语言 → 跳过
    │          · 短笔记合并批处理仍属延后项
    │
    ├─► [处理] for each 组（按文件名升序）
    │     │
    │     ├── 加载 active_memory（规模由 config 阈值控制，默认 1500 tokens）
    │     ├── build_system_prompt("process_note", ...)
    │     ├── LLM 调用（active_memory + 笔记原文）
    │     ├── JSON Schema 校验返回结果
    │     ├── 解析返回的结构化 JSON
    │     │     ├── domain + subcategory → join 为 category，确定写入 ai_notes 的路径
    │     │     ├── tags            → 更新 tag_candidates
    │     │     ├── summary         → 写入 frontmatter
    │     │     ├── rewritten_content → 写入笔记正文（重写版本）
    │     │     ├── questions       → 契约保留但当前不消费；追问实际以 <!-- ❓ --> 注释内嵌正文
    │     │     └── memory_updates  → apply_memory_updates()
    │     │
    │     ├── 写入 ai_notes/{category}/{title-slug}.md
    │     ├── 原子写入 memory.json（逐篇 checkpoint）
    │     └── if token > threshold → compress_memory()（Phase 3 已实现）
    │
    ├─► [分析] analyze.py
    │     ├── memory_hash 仅对 active_memory 计算（归档追加不触发重新生成）；
    │     │     dashboard/data/ 契约文件缺失时无视 hash 跳过、强制重新生成
    │     ├── 从 memory.json 生成 dashboard/data/stats.json
    │     ├── 生成 summaries.json
    │     ├── 生成 recent_notes.json（最近处理笔记，processed_at 优先取 frontmatter，旧文件缺失时回退 mtime）
    │     ├── 生成 roadmap.json（from history_archive，ADR-016）（Phase 3 已实现）
    │     ├── 生成 profile.json（MBTI 风格描述）（Phase 3 已实现）
    │     ├── 生成像素世界场景剧本（Phase 4B/C 规划）
    │     │     └── LLM 基于 active_memory + 精简 manifest + 当前场景状态
    │     │             Genesis 基础房间 + AI 行为 / Evolution 受限变更
    │     │             写入 {vault}/.mindraft/scene_state.json
    │     ├── 导出前端配置到 dashboard/data/config.json
    │     ├── 像素世界启用时独立导出 scene.json（Phase 4）
    │     └── 入口先检测跨周，不受 hash 缓存影响；处理新笔记前也检查，避免覆盖旧周状态
    │
    └─► [展示] serve.py
          └── 启动 http://localhost:8765
              打开浏览器
              app.js 读取六个 JSON 数据文件；像素世界属 Phase 4 规划
```

---

## 9. 开发分阶段计划

### 实现方式

**Vibe-coding 协作模式**：AI Agent 负责实现代码，人工负责审查、指挥和决策。

- **AI 职责**：实现代码、每阶段完成后输出实现汇总和待确认问题
- **人工职责**：审查代码、回答问题、给出反馈、确认后进入下一阶段
- **决策日志**：实现决策记录入 [mindraft-log.md](mindraft-log.md)，供 Agent 中断后恢复上下文

**阶段推进规则**

```
实现阶段 N
    │
    ├── AI 实现代码
    ├── AI 输出：实现汇总 + 待确认问题
    ├── 人工：审查 + 回答 + 反馈
    ├── 确认无问题
    └── 进入阶段 N+1
```

**核心原则**
- 优先实现最核心的功能（笔记处理 + Dashboard UI），再逐步扩展
- 每个阶段结束时，产品必须处于可运行、可验证的状态
- 每个阶段不超出其目标范围，不提前实现下一阶段的功能

---

### Phase 0 — 基础骨架

**目标**：项目可以启动，能够调用 LLM，基础设施就绪

**实现内容**
- 目录结构初始化（notes-vault + mindraft 双 repo 结构）
- 虚拟环境配置：创建 `.venv`、生成 `requirements.txt`
- `config.yml` 配置文件
- LLM 抽象层（`base.py` + `kimi.py` + `llm_factory.py`）
- `run.py` CLI 骨架（能解析参数，能读取 config）
- 基础设施：
  - `utils.py`：原子写入 `safe_write_json()`、进程锁 `get_process_lock()`、Token 估算 `token_estimate()`、日志初始化 `setup_logging()`
  - `schemas.py`：LLM 返回的 JSON Schema 校验
  - `prompts.py`：所有 Base Role 定义

**依赖包**
- `openai`（Kimi 的 OpenAI 兼容接口）
- `pyyaml`（读取 config.yml）
- `jsonschema`（LLM 返回校验）
- `filelock`（进程级文件锁）

**验收标准**
- `requirements.txt` 已创建，包含全部依赖
- 在虚拟环境中执行 `pip install -r requirements.txt` 后，`python run.py --dry-run` 执行不报错，不写入任何业务状态文件
- 调用 LLM API 返回正常响应（可通过临时测试脚本验证）
- 日志输出到控制台和文件
- 并发执行时第二个实例被拒绝

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 1

---

### Phase 1 — 笔记处理核心

**目标**：原始笔记被 AI 处理分类，写入 ai_notes，记忆状态正确维护

**实现内容**
- `skill_loader.py` + 基础 skill 文件（`note_style.yml`、`tagging.yml`、`json_output.yml`；`summary_style.yml` 已在 Phase 3 补齐）
- `process_notes.py`：扫描 raw_notes → LLM 处理 → 写入 ai_notes
- `memory.json` 基础结构创建
- `apply_memory_updates()`：处理 LLM 返回的记忆更新指令

**验收标准**
- `python run.py` 成功处理 raw_notes 中的笔记
- ai_notes/ 目录中出现分类后的 markdown 文件，frontmatter 格式正确
- memory.json 中 `active_memory` 有更新，`processed_notes` 记录了已处理笔记

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 2

---

### Phase 2 — Dashboard MVP

**目标**：浏览器可以看到有真实笔记数据的 Dashboard（最小静态版本）

**实现内容**
- `analyze.py`：从 `memory.json` 生成 `summaries.json`、`stats.json`、`recent_notes.json`、`config.json`
- Dashboard 前端（`index.html` + `style.css` + `app.js`）：暗色主题、桌面优先
- 最近处理笔记列表（最多 10 篇）
- `active_memory` 五域一句话摘要卡片
- `tag_candidates` 列表
- 每日一句洞察卡片（带叙事色彩，基于 `active_memory`）
- `serve.py`：启动本地 HTTP 服务器，并自动打开浏览器
- `run.py` 命令语义：默认完整流程（处理笔记 → 生成数据 → 启动服务），`--analyze` 只做 AI 分析，`--dashboard` 只启动服务

**不做内容**
- Chart.js 字数趋势图、CSS Grid 活跃日历（继续延后，Phase 5 候选）
- 用户形象（Phase 4）
- 记忆压缩、MBTI 描述、Road Map Timeline（Phase 3）
- 统一归档 ADR-016（周快照并入 history_archive，延后到 Phase 3 实现）

**验收标准**
- `python run.py` 走完整流程：处理笔记、生成 dashboard 数据并自动在浏览器打开 Dashboard
- Dashboard 显示最近笔记列表、五域摘要卡片、tag 候选、每日一句
- `python run.py --dashboard` 只启动服务器并打开浏览器，无数据时显示空状态提示
- LLM 失败时 Dashboard 仍可启动并显示 fallback 提示

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 3

---

### Phase 3 — 记忆系统完善

**状态**：2026-09-07 实现完成；2026-09-12 用户确认 API 配置与人工测试通过。Phase 1–3 核心闭环已完成，后续按 Phase 4A–4C 像素世界 MVP 与 Phase 5（MVP 后）规划推进。

**目标**：记忆压缩机制正常运转，Dashboard 展示更丰富的自我分析

**实现内容**
- `compress_memory()`：触发压缩时归档 active_memory（一次原子写入）、调用 LLM 浓缩原文区、治理浓缩区子预算
- 统一归档：`history_archive` 条目化（`iso_week` + `trigger: weekly/compression`，ADR-016），跨周追加 weekly 条目
- `memory_compression.yml` skill 文件
- Tag 候选升级机制（count ≥ 3 → active）
- `analyze.py` 扩展：生成 `profile.json`（MBTI 风格描述）和 `roadmap.json`
- `analysis_style.yml` skill 文件
- Dashboard 新增：MBTI 风格描述卡片 + Road Map Timeline

**验收标准**
- active_memory 的估算 token 超过配置阈值时，自动触发记忆压缩，history_archive 有归档记录
- Dashboard 显示 MBTI 风格描述和 Road Map Timeline

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 4

---

<a id="pixel-world-mvp"></a>

### Phase 4 — 像素世界用户形象 MVP

**状态**：未开始。替代原 Phase 4 Text Card，并吸收原 Phase 6–7；原编号仅保留在历史日志中（ADR-019）。Phase 1–3 保持已完成。

**MVP 交付定义**：已有笔记处理和 Dashboard，加上一个依据记忆改变行为、随时间有限演化的像素小人世界。没有 Work Me / Home Me 双画像，也不以笔记关联、URL 抓取或用户互动为前置条件。

按 4A → 4B → 4C 顺序实施，每步都应可独立运行并验收；前一步未通过，不叠加下一步。正式 MVP 完成需三步全部通过，4A 示例渲染不等于 AI 形象已完成。

#### 4A — 离线像素世界竖向原型（零 LLM）

**工作**：
- 固定一个房间、一个角色、最多 8 槽位（初始仅占用 1–2 个，保留演化空间）；纳入最小可分发素材、manifest、引擎固定版本与许可记录。Aseprite 和付费素材不作为必需依赖。
- 定义版本化 Scene/manifest 契约，建立共享合法/非法 fixtures；先实现一个可播放剧本：站点间行走 → 等待/交互 → 表情/气泡 → 回程循环。
- 实现 renderer 生命周期、确定性寻路、idle fallback、暂停/恢复、页面隐藏暂停与像素缩放；Dashboard 新增一个世界窗口，保留所有已有卡片。
- 接入规划中的 `pixel_world.enabled` 与 renderer 配置；仅此阶段起配置生效。为 `--dashboard` 增加只读 `/runtime-config.json` 响应，只返回标题、世界开关、渲染器和本地 fixture 路径等白名单字段，不写业务文件、不暴露 provider/key/vault 路径。前端在六份分析数据缺失时仍可独立加载示例；关闭时不加载场景，老 Dashboard 正常工作。

**验收**：
- 全新 checkout 安装 Python 依赖后，无额外素材下载、无 key、断网时可用 `--dashboard` 看到明确标注的示例世界；不是直接双击 HTML。
- 至少一个完整循环可执行；不可达站点、缺图片、缺动画、剧本异常、只读运行配置请求失败都能降级，不出现空白页面或无限等待。
- 在主流桌面浏览器检查 800px/1200px 窗口、暂停/恢复和重复挂载；连续 10 分钟与 20 次更新检查通过。
- 后端已有回归通过；前端增加可重复运行的 fixture/浏览器 smoke 命令，写入 README。

#### 4B — 记忆驱动的场景行为（打通真实闭环）

**依赖**：4A 契约和渲染 smoke 通过；使用现有 active_memory，不增加 avatar_data 中间层。

**工作**：
- 新增 `scripts/scene.py`、`SCENE_DIRECTOR_ROLE`、`scene_director.yml` 和受限导演 schema，复用 `get_llm()`、统一重试/校验接口。
- 接入单独的场景缓存、scene_state 原子保存与 scene 导出；导演只更新行为、表情、说明、气泡和合法剧本，不能改变布局、外观或物件。
- 在现有分析之后独立执行场景生成，复用 dry-run 模拟记忆；拆分摘要缓存与场景刷新条件。
- 接入 scene_state 的 rebuild 清理和缺失导出修复；记录文件格式与错误处理。

**验收**：
- 三类 mock 记忆得到合法且可播放的行为；真实 key 下 dry-run 与测试 vault 的完整分析各完成一次人工检查。
- 同输入第二次分析不调用场景 LLM；修改记忆只增加一次逻辑调用；坏 schema、未知 id、不支持的动作、不通路径均重试一次，最终失败保留旧场景和有效笔记结果。
- 首次无记忆不调用导演且不编造用户状态；仅删除导出可从 state 修复；坏 state 不被悄悄重置。
- dry-run 无业务文件写入，`--dashboard` 不调用 AI，关闭像素世界不影响六份既有数据契约。

#### 4C — 有限增量进化与 MVP 验收

**依赖**：4B 的缓存、失败恢复和数据持久化通过。

**工作**：
- 在同一次导演响应中增加受限 `add_prop(slot_id, asset_id)`，每次最多一件；后端检查现有库存与槽位并赋稳定 id。
- 角色与房间不重建、旧物件不删除；无适合素材/满槽时只改变行为，不为视觉变化强行添物件。
- 同一次状态提交追加演化记录；增加失败重试、幂等重复、写入中断/重导出、20 次连续更新和满槽测试。
- 用测试 vault 验收“写一篇新笔记 → run.py → 看见有依据的行为或物件变化”；明确不承诺每篇笔记都产生视觉变化。

**验收**：
- 至少一次有依据的物件新增与一次纯行为更新，前后场景中角色 id、房间和原有物件 id 保持稳定。
- 重复输入/重试不重复新增，满槽不丢物件；非法更新和磁盘写入失败不改变成功场景及演化记录。
- 全量离线回归、场景浏览器 smoke、真实 API 流程通过，README 包含配置、素材来源、运行/测试和故障恢复说明。

**阶段结束**：用户验收 4C 后，像素世界 MVP 完成；是否进入后续增强再决定，不自动扩展范围。

### Phase 5 — 笔记关联与链接增强（MVP 后，独立排期）

保留原功能方向，但不再阻塞像素世界：`relationships.json`、URL 抓取与摘要、关系图。实际开始前重新拆分实施计划；追问闭环仍属于未来目标。不得为了本阶段反向修改 `raw_notes/`。

### 未来目标（不计入当前 MVP）

- **Work Me / Home Me**：按场景呈现同一个用户的不同侧面；届时再决定多房间、场景切换或其他形式，不现在预建双画像字段。
- 多角色、NPC、用户可操控互动、任务系统、声音；动态房间布局、角色换装、重大生活转变的 transformation。
- 高质量素材包、更多动作、场景演化回放；更换渲染引擎或表现形式。
- 短笔记批处理、字数趋势图、活跃日历、追问回答闭环。
- 自动触发、云端部署、多用户、移动端、更多笔记源、开放 API。

#### 新旧阶段映射

| 原计划 | 本次处理 |
|--------|----------|
| Phase 4 Text Card + avatar_data + Work/Home 双卡 | Text Card 与中间画像层取消；Work/Home 移至未来目标 |
| Phase 6 离线像素渲染 | 提前为 Phase 4A |
| Phase 7 AI 导演与进化 | 分解为 Phase 4B（行为）和 4C（有限进化） |
| Phase 5 关联与链接增强 | 保留 Phase 5 编号，明确 MVP 后独立排期 |

---

## 10. run.py 入口设计

| 命令 | 行为 |
|------|------|
| `python run.py` | 完整流程：处理新笔记（已处理的跳过，上次失败的重试）→ 生成 dashboard 数据 → 启动服务并自动打开浏览器 |
| `python run.py --analyze` | 执行全部 AI 分析（处理新笔记 + 生成 dashboard 数据），不启动服务；memory 未变化且数据文件齐全时跳过生成（零 LLM 调用），`--rebuild` 可强制重建 |
| `python run.py --dashboard` | 只启动本地服务器并自动打开浏览器，不做任何分析 |
| `python run.py --rebuild` | 清空全部分析结果（`ai_notes/`、`memory.json`、`dashboard/data/*.json`、`process_log.jsonl`），从头重新分析并走完整流程；`--rebuild --analyze` 则只重建不启动服务 |
| `python run.py --dry-run` | 干跑：调用全部 LLM（笔记处理 + analyze）但不写入任何文件、不启动服务 |

→ 完整实现：`run.py`

---

*产品名称：Mindraft | 文档版本：v2.1 | 最后更新：2026-09-12*
*相关文档：[mindraft-log.md](mindraft-log.md) · [../AGENTS.md](../AGENTS.md)*
