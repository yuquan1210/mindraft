# Mindraft (涌现)
## 产品方案文档 v2.0

> 最后更新：2026-06-19  
> 相关文档：[技术参考](Mindraft-Technical.md) · [实现日志](Mindraft-Log.md)

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
   - 5.6 [用户画像系统](#56-用户画像系统)
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
│   ③ 更新 relationships.json（关联图谱）                   │
│   ④ 更新 avatar_data.json（画像数据契约）                 │
│         ↓                                                │
│   analyze.py       →  生成 dashboard/data/*.json         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              展示层：本地 Web Dashboard                   │
│              http://localhost:8080                       │
│                                                          │
│   字数趋势图 │ 活跃日历 │ 每日一句                        │
│   MBTI 风格描述 │ Road Map │ Work Me │ Home Me           │
│                                                          │
│   画像渲染层（可替换）：                                   │
│   TextCardRenderer → PixelArtRenderer → GameRenderer     │
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
│   analysis/              │     │                              │
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
│   ├── study/
│   └── life/
│       ├── workout/
│       └── cooking/
│
└── analysis/                     # AI 分析产物（非笔记）
    ├── memory.json               # 蒸馏记忆（核心状态文件）
    ├── relationships.json        # 笔记关联图谱
    ├── tags.json                 # 全局 tag 汇总
    ├── avatar_data.json          # 用户画像数据契约
    ├── process_log.jsonl         # 处理日志（JSONL 格式）
    ├── .mindraft.lock            # 进程锁文件（运行时自动创建）
    └── snapshots/                # 每周快照（Road Map 数据源）
        ├── 2026-W24.json
        └── 2026-W23.json
```

### Repo 2：mindraft

```
mindraft/
│
├── skills/                       # AI Skill 配置文件
│   ├── note_style.yml
│   ├── summary_style.yml
│   ├── tagging.yml
│   ├── analysis_style.yml
│   └── memory_compression.yml
│
├── scripts/
│   ├── llm/                      # LLM 抽象层
│   │   ├── base.py
│   │   ├── kimi.py
│   │   ├── openai.py
│   │   └── anthropic.py
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
│   │   ├── base_renderer.js
│   │   ├── text_card_renderer.js     # Phase 1 MVP
│   │   ├── pixel_art_renderer.js     # Phase 2
│   │   ├── animated_sprite_renderer.js
│   │   └── game_renderer.js          # Phase 3
│   └── data/                     # analyze.py 输出，JS 直接读取
│       ├── config.json            # 前端配置（从 config.yml 导出）
│       ├── stats.json             # 字数 / 日历数据
│       ├── summaries.json         # 每日摘要
│       ├── roadmap.json           # 周快照历史
│       └── avatar_data.json       # 画像数据（从 analysis/ 同步）
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
| LLM（默认） | Kimi API | 长上下文和中文能力强，OpenAI 兼容接口 |
| LLM（备选） | OpenAI / Anthropic | 通过 config.yml 一键切换 |
| 前端 | 原生 HTML + CSS + JS | 零框架，直接上手 |
| 图表库 | Chart.js（CDN 引入） | 无需安装，一行引入 |
| 本地服务 | Python `http.server` | 内置模块，无需安装 |
| 画像生成（Phase 2） | Replicate API | 有专门的 pixel art 模型 |
| 画像游戏化（Phase 3） | Phaser.js / Three.js | 成熟的前端游戏/3D 框架 |
| IDE | VS Code + Claude Code | 适合 vibe coding |

### config.yml 关键配置项

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `notes_vault_path` | 笔记仓库本地路径 | `~/Developer/GitHub/notes-vault` |
| `llm_provider` | 切换 LLM 的唯一入口 | `kimi \| openai \| anthropic` |
| `avatar.renderer` | 切换画像渲染器 | `text_card \| pixel_art \| game` |
| `memory.active_memory_token_threshold` | 触发记忆压缩的 token 阈值 | `1500` |
| `token_estimation` | Token 估算方式 | `char_ratio \| tiktoken` |
| `note_filter.min_meaningful_chars` | 笔记最低有效字符数 | `20` |
| `note_filter.batch_char_threshold` | 短笔记合并阈值 | `200` |
| `logging.level` | 日志级别 | `INFO` |

→ 完整配置示例：[Mindraft-Technical.md § 1](Mindraft-Technical.md#1-配置文件-configyml)

---

## 5. 核心模块设计

### 5.1 LLM 抽象层

通过统一接口抽象所有 LLM，切换模型只需修改 `config.yml`，代码零改动。

```
scripts/llm/
├── base.py          # 抽象基类，定义统一接口
├── kimi.py          # Kimi 实现（OpenAI 兼容接口）
├── openai.py        # OpenAI 实现
└── anthropic.py     # Claude 实现
```

→ 实现代码：[Mindraft-Technical.md § 2](Mindraft-Technical.md#2-llm-抽象层)

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

→ 所有 skill 文件示例：[Mindraft-Technical.md § 3](Mindraft-Technical.md#3-skill-配置文件)

#### Skill 与操作的对应关系

| 操作 | 挂载的 Skill |
|------|-------------|
| `process_note` | `note_style` + `tagging` |
| `enrich_with_link` | `note_style` |
| `generate_daily_summary` | `summary_style` |
| `generate_profile` | `analysis_style` |
| `generate_mbti_description` | `analysis_style` |
| `generate_avatar_data` | `analysis_style` |
| `compress_memory` | `memory_compression` |

→ 实现代码：[Mindraft-Technical.md § 4](Mindraft-Technical.md#4-skill_loaderpy)

---

### 5.3 笔记处理流水线

#### 流程概览

```
run.py
  │
  └─► process_notes.py
        │
        ├── 获取进程锁（防止并发执行）
        ├── 扫描 raw_notes/
        ├── 对比 memory.processed_notes（找出未处理的笔记）
        │
        ├── [预筛选] 跳过无意义笔记：
        │     · 空文件
        │     · 低于 min_meaningful_chars 字符的笔记
        │     · 仅包含无法理解的代码片段（无自然语言文字）
        │     → 标记为已处理，记录跳过原因，不调用 LLM
        │
        ├── [分组] 将未跳过的笔记分为两类：
        │     · 短笔记（≤ batch_char_threshold 字符）→ 合并为一批，一次 LLM 调用
        │     · 长笔记 → 各自独立处理
        │
        └── for each 组（按日期升序）：
              │
              ├── 1. 加载 memory.json 中的 active_memory
              ├── 2. build_system_prompt("process_note", base_role)
              ├── 3. 调用 LLM：active_memory + 笔记原文
              ├── 4. JSON Schema 校验 LLM 返回结果
              ├── 5. 解析 JSON 返回：
              │       category, tags, summary,
              │       rewritten_content, questions,
              │       related_notes, memory_updates
              │
              ├── 6. 写入 ai_notes/{category}/{filename}.md
              ├── 7. apply_memory_updates() → 更新 active_memory
              ├── 8. 更新 relationships.json
              ├── 9. 将笔记名加入 memory.processed_notes
              ├── 10. 原子写入 memory.json（逐篇 checkpoint，确保断点可恢复）
              │
              └── 11. if token_estimate(active_memory) > threshold:
                          compress_memory()
```

#### AI 处理后笔记的 frontmatter 格式

```markdown
---
original: raw_notes/2026-06-15.md
processed_at: 2026-06-15
category: work/daily
tags: [backend, sprint]
summary: "今天完成了登录模块的代码审查，发现权限设计有漏洞"
related:
  - work/epic_and_cards/auth-redesign.md
  - work/tips/permission-patterns.md
---

...（AI 对原始笔记的清晰重写版本：结构化表达，补充必要背景知识）...

> 📎 [来源标题](https://example.com)：（该 URL 对应内容的摘要）

<!-- ❓ 待补充：这里提到的"权限漏洞"具体是哪种场景？AI 无法从现有上下文推断，请补充更多信息。 -->
```

#### Tag 创建规则

```
候选阶段：每篇笔记处理时，AI 提出 ≤3 个候选 tag
          存入 memory.tag_candidates，status: "pending"

升级规则：当 tag_candidates 中某个 tag 的 count ≥ 3
          → status 升级为 "active"
          → 写入对应的所有笔记 frontmatter

目的：防止 tag 爆炸，确保每个 tag 都有足够的代表性
```

#### 笔记重写规则

AI 对原始笔记的核心处理是**重写**，而非仅整理或追加。

```
预筛选规则（在调用 LLM 之前，由代码判断）：
  · 空文件 → 跳过，标记为已处理，记录跳过原因
  · 字符数 < min_meaningful_chars (20) → 跳过
  · 去除代码块后无自然语言文字（< 10 字符）→ 跳过
  · 短笔记（≤ 200 字符）→ 合并为一批（最多 5 篇），一次 LLM 调用处理
  · 长笔记 → 各自独立处理

重写目标：将潦草、碎片化的原始笔记，重写为清晰、结构化、易读的版本

重写原则：
  · 保留原文所有核心信息，补充可从上下文或 AI 知识合理推断的背景
  · 如涉及代码/技术内容，格式化为规范的 markdown 代码块
  · 笔记中的 URL → 抓取页面内容 → 生成摘要 → 以引用块追加
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
  ① active_memory（压缩的历史记忆，~600 tokens）
  ② 当前这一篇新笔记（~100-200 字）

处理后更新 active_memory，而不是堆积原文
→ 无论写了 100 篇还是 10000 篇，每次 LLM 输入的 token 消耗恒定
```

#### 双层记忆结构

```
memory.json
│
├── active_memory  (热层)
│     · 每次处理笔记时发给 LLM
│     · 始终保持压缩，控制在 ~800 tokens 内
│     · 内容只增不减（压缩 ≠ 删除）
│
└── history_archive  (冷层)
      · 永久追加，从不删除
      · 不发给 LLM（不占 token）
      · Road Map / Timeline 的数据来源
      · 每次压缩前，将 active_memory 完整归档于此
```

#### memory.json 完整结构

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
      "recurring_signals": [
        "容易在细节上花过多时间",
        "喜欢在写代码前先理清思路"
      ],
      "recent_mood_trend": "疲惫但有动力，本周略有改善"
    },
    "life": {
      "current_routines": ["早上健身", "周末做饭"],
      "recurring_signals": ["睡眠不规律是持续困扰"],
      "interests_observed": ["电影", "编程", "烹饪"]
    },
    "personality_signals": [
      "偏内向，独处时恢复能量",
      "目标感强，对自身完美主义有自我觉察",
      "表达方式直接，情绪起伏不大"
    ]
  },

  "tag_candidates": {
    "backend":       { "count": 5, "status": "active" },
    "sprint":        { "count": 3, "status": "active" },
    "side-project":  { "count": 2, "status": "pending" }
  },

  "history_archive": [
    {
      "archived_at": "2026-06-07",
      "trigger": "compression",
      "note_count_at_time": 31,
      "snapshot": {
        "work": {
          "current_focus": "...",
          "ongoing_projects": ["..."],
          "recurring_signals": ["..."],
          "recent_mood_trend": "..."
        },
        "life": {},
        "personality_signals": []
      }
    }
  ]
}
```

#### 追加更新规则

LLM 返回的 `memory_updates` 只允许两种操作，任何 DELETE / OVERWRITE 直接忽略：
- `APPEND_TO`：向指定数组追加新元素（语义去重后追加）
- `SET_IF_NEW`：只有字段不存在时才写入

**System prompt 中写死的约束：**

> 你只能追加新的观察，不能修改或删除已有内容。
> 如果新笔记与已有记忆存在矛盾，用 APPEND_TO 追加新信号，而不是覆盖旧信号。
> 矛盾本身也是有价值的历史信息。

→ 实现代码：[Mindraft-Technical.md § 5](Mindraft-Technical.md#5-笔记处理)

#### 压缩触发与执行

压缩分三步：① 将 active_memory 完整归档至 history_archive（永久保留）→ ② 调用 LLM 压缩（精简表达，不丢信号）→ ③ 热层 token 降回 ~600。

→ 实现代码：[Mindraft-Technical.md § 6](Mindraft-Technical.md#6-记忆系统)

#### 各阶段记忆状态预估

| 阶段 | active_memory | history_archive | 每次 LLM 输入 token |
|------|--------------|-----------------|-------------------|
| 第 1-20 篇笔记 | 逐渐增长 | 空 | ~300-800 |
| 触发第一次压缩 | 重置 ~600 | 1 条归档 | ~800 |
| 第 500 篇笔记 | 始终 ~600 | N 条归档 | 恒定 ~800 |

---

### 5.5 笔记关联关系

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

### 5.6 用户形象进化系统

#### 设计思路：数据与渲染分离，形象持续进化

画像系统分为两层，两层之间通过稳定的数据契约解耦。

**核心进化原则：形象不是每次重新生成，而是在已有形象的基础上持续演化。** 就像真实的人一样——每天都会有细微变化，但不会每天都变成另一个人。稳定的核心不变，细节随生活随时间流动。

```
LLM 分析结果
    │
    ▼
Avatar Data（稳定的数据契约）    ← 这层永远不变
    │
    ▼
Avatar Renderer（可替换的插件）  ← 只改这层
    │
    ├── TextCardRenderer         # Phase 1 MVP
    ├── PixelArtRenderer         # Phase 2
    ├── AnimatedSpriteRenderer   # Phase 2+
    └── GameRenderer             # Phase 3
```

**切换表现形式的成本：**

| 替换内容 | 难度 | 需要改动的地方 |
|---------|------|--------------|
| 换艺术风格（像素 → 水彩） | 低 | 改 `pixel_art_renderer.js` 中的 prompt 模板 |
| 换图片生成服务（Replicate → DALL-E） | 低 | 改 `analyze.py` 中一个函数 |
| 换整体形式（图片 → 小游戏） | 中 | 新建 `game_renderer.js`，config 改一行 |

---

#### 形象进化机制

**两种生成模式：**

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| Genesis Mode（创世） | 首次运行 / 用户主动重置 / 检测到重大生活转变 | 从零生成全新形象 |
| Evolution Mode（进化） | 常规每次 run.py 执行 | 在现有形象基础上做增量调整 |

**变化的三个层级：**

```
Micro（每次运行都可能更新）
  · mood / energy_level / stress_level
  · thought_bubble（角色当前在想什么）
  · recent_highlights（近期发生的亮点）
  · 像素画：低 denoising (0.2)，保留形象主体，只更新表情/姿态

Macro（数周内缓慢积累）
  · room_objects 追加新物件（新爱好 → 书桌多了本新书）
  · traits 权重调整（某个特质越来越突出则加粗描述）
  · description 的侧重点/语气随状态演变
  · scene 细节调整（时间段、光线、氛围）
  · 像素画：中 denoising (0.45)，添加新配饰/道具，整体轮廓保持

Transformation（稀有，标志性人生转变）
  · visual_anchors 更新（风格/外貌大幅变化）
  · color_palette 整体切换（气质转变）
  · style_era 更新（进入新的人生阶段）
  · 像素画：高 denoising (0.80)，大幅重绘，但保留 seed 作为历史参照
```

**变化量级评估规则：**

| 量级 | 触发条件 |
|------|----------|
| `transformation` | memory_delta 包含：换城市、换工作、重大关系变化、user_reset |
| `macro` | memory_delta 涉及：`ongoing_projects`、`current_routines`、`interests_observed` |
| `micro` | 其他任何情况（默认） |

→ 实现代码：[Mindraft-Technical.md § 7](Mindraft-Technical.md#7-用户形象系统)

---

#### Avatar Data 契约

这是整个画像系统唯一稳定的接口。无论渲染方式怎么变，此数据结构不变。字段只增不减，新渲染器需要更多数据时追加字段，不改动现有字段。

```json
// analysis/avatar_data.json

{
  "generated_at": "2026-06-15",
  "genesis": false,          // true = 本次为全新创世；false = 进化模式

  // 稳定的形象身份锚点，跨所有场景共用，只在 Transformation 时更新
  "avatar_identity": {
    "version": 4,
    "established_at": "2026-06-01",
    "last_evolved_at": "2026-06-15",
    "base_image_seed": "kimi_seed_20260601_7a3f",      // 像素画可复现基础形象
    "core_traits": ["注重细节", "内向", "逻辑导向"],    // 稳定人格特质
    "visual_anchors": ["眼镜", "深色系穿搭", "短发"],   // 外貌稳定元素
    "style_era": {
      "name": "early_builder",
      "started_at": "2026-06-01",
      "description": "初期摸索阶段，专注于构建基础，对细节有执着"
    }
  },

  // 记录每次进化的变化历史（只增不删）
  "evolution_log": [
    {
      "timestamp": "2026-06-15",
      "change_magnitude": "micro",
      "trigger_notes": ["2026-06-15.md"],
      "changes_summary": {
        "work_me.core.mood": "focused → tired",
        "work_me.thought_bubble": "这个边界条件到底该怎么处理..."
      }
    }
  ],

  "work_me": {
    "core": {
      "mood": "focused",
      "energy_level": 0.7,
      "stress_level": 0.4,
      "primary_activity": "deep work"
    },
    "traits": ["注重细节", "容易过度思考", "逻辑导向"],
    "scene": "studio",
    "description": "工作中的你像一个在迷雾中摸索路径的建筑师...",
    "recent_highlights": [
      "正在攻克一个复杂的权限设计问题",
      "本周 code review 效率有所提升"
    ],
    "thought_bubble": "这个边界条件到底该怎么处理...",
    "room_objects": ["机械键盘", "多个显示器", "咖啡杯", "白板"],
    "color_palette": ["#1a1a2e", "#16213e", "#a78bfa"]
  },

  "home_me": {
    "core": {
      "mood": "relaxed",
      "energy_level": 0.45,
      "stress_level": 0.2,
      "primary_activity": "cooking"
    },
    "traits": ["享受独处", "有创造力", "喜欢动手"],
    "scene": "home",
    "description": "下班后的你像一个终于可以放松的手艺人...",
    "recent_highlights": [
      "上周末尝试了新菜谱",
      "恢复了早起健身的习惯"
    ],
    "thought_bubble": "今晚做什么吃...",
    "room_objects": ["锅铲", "绿植", "书", "瑜伽垫"],
    "color_palette": ["#2d1b00", "#4a3728", "#f59e0b"]
  }
}
```

**各字段的渲染器使用情况：**

| 字段 | TextCard | PixelArt | Game |
|------|---------|----------|------|
| `core.mood` / `energy_level` | 选择占位表情 | 选择角色动作帧 | 驱动角色动画状态 |
| `description` | ✅ 显示文字 | ✅ 显示文字 | 作为 NPC 对话 |
| `traits` | ✅ tag 标签 | ✅ tag 标签 | 影响角色行为逻辑 |
| `thought_bubble` | ❌ 忽略 | ❌ 忽略 | ✅ 角色头顶气泡 |
| `room_objects` | ❌ 忽略 | ❌ 忽略 | ✅ 生成场景物品 |
| `color_palette` | ❌ 忽略 | ✅ 图片配色参考 | ✅ 场景主色调 |

---

#### Renderer 插件设计

所有渲染器继承 `BaseAvatarRenderer`，实现 `render()` 方法。切换渲染器只需改 `config.yml` 一行，无需修改业务代码。

→ 所有渲染器实现：[Mindraft-Technical.md § 8](Mindraft-Technical.md#8-dashboard-前端)

---

## 6. Dashboard 设计

> Dashboard 展示 ai_notes 中的重写内容和分析产物，不直接展示 raw_notes 原始笔记。

### 组件总览

| 组件 | 描述 | 数据来源 |
|------|------|---------|
| 字数趋势图 | 最近 7 天每天笔记总字数柱状图 | `stats.json` |
| 活跃日历 | 类 GitHub 热力图，最近 12 周 | `stats.json` |
| 每日一句 | 当天（或最近一篇）笔记摘要 | `summaries.json` |
| MBTI 风格描述 | 基于近 4 周笔记的性格分析 | `profile.json` |
| Road Map Timeline | 以周为节点的状态变化轨迹 | `roadmap.json` |
| Work Me | 工作场景用户画像 | `avatar_data.json` |
| Home Me | 生活场景用户画像 | `avatar_data.json` |

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

更新频率：每次 run.py 执行后重新生成
数据来源：memory.active_memory
```

#### Road Map Timeline

```
形式：横向时间轴，每周一个节点
节点显示：该周笔记数量 + 关键词 top 3
Hover 展示：
  - 时间范围（如 Jun 8 - Jun 14）
  - 笔记数量
  - 一句话状态描述
  - 主要 tag
数据来源：history_archive 中的归档快照 + snapshots/*.json

快照生成时机：检测到跨越自然周时自动生成（不依赖"周末执行"）
早期数据保障：即使未触发过记忆压缩，周快照也会独立生成，
              确保 Road Map 在早期不会空白
```

#### 用户画像：Work Me / Home Me

```
布局：左图右文
左侧：由当前 renderer 渲染的画像区域
右侧：description 文字 + traits 标签 + recent_highlights 列表

Phase 1（text_card）：左侧为根据 mood 状态切换的预设占位像素图
Phase 2（pixel_art）：左侧为 Replicate API 生成的个性化像素图
Phase 3（game）：     整个区域替换为可交互的内嵌游戏场景
```

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

→ CSS 完整代码：[Mindraft-Technical.md § 11](Mindraft-Technical.md#11-ui-样式)

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
    │          （对比 memory.processed_notes）
    │
    ├─► [预筛选] 跳过无意义笔记 + 短笔记合并分组
    │          · 空文件 / 低于 min_meaningful_chars / 无自然语言 → 跳过
    │          · 短笔记 ≤ batch_char_threshold → 合并为一批（一次 LLM 调用）
    │          · 长笔记 → 各自独立处理
    │
    ├─► [处理] for each 组（按日期升序）
    │     │
    │     ├── 加载 active_memory（~600 tokens）
    │     ├── build_system_prompt("process_note", ...)
    │     ├── LLM 调用（active_memory + 笔记原文）
    │     ├── JSON Schema 校验返回结果
    │     ├── 解析返回的结构化 JSON
    │     │     ├── category        → 确定写入 ai_notes 的路径
    │     │     ├── tags            → 更新 tag_candidates
    │     │     ├── summary         → 写入 frontmatter
    │     │     ├── rewritten_content → 写入笔记正文（重写版本）
    │     │     ├── questions       → 以注释嵌入笔记，要求作者补充
    │     │     ├── related_notes   → 更新 relationships.json
    │     │     └── memory_updates  → apply_memory_updates()
    │     │
    │     ├── 写入 ai_notes/{category}/{filename}.md
    │     ├── 原子写入 memory.json（逐篇 checkpoint）
    │     └── if token > threshold → compress_memory()
    │
    ├─► [分析] analyze.py
    │     ├── 从 memory.json 生成 dashboard/data/stats.json
    │     ├── 生成 summaries.json
    │     ├── 生成 roadmap.json（from history_archive + snapshots）
    │     ├── 生成 profile.json（MBTI 风格描述）
    │     ├── 生成 avatar_data.json（画像数据契约）
    │     │     └── if renderer == "pixel_art":
    │     │             调用 Replicate API 生成图片
    │     │             将 image_url 写入 avatar_data
    │     ├── 导出前端配置到 dashboard/data/config.json
    │     ├── 同步 avatar_data.json 到 dashboard/data/
    │     └── 检测跨周 → 自动生成 snapshots/YYYY-WXX.json
    │
    └─► [展示] serve.py
          └── 启动 http://localhost:8080
              打开浏览器
              app.js 根据 config.avatar.renderer 加载对应渲染器
```

---

## 9. 开发分阶段计划

### 实现方式

**Vibe-coding 协作模式**：AI Agent 负责实现代码，人工负责审查、指挥和决策。

- **AI 职责**：实现代码、每阶段完成后输出实现汇总和待确认问题
- **人工职责**：审查代码、回答问题、给出反馈、确认后进入下一阶段
- **决策日志**：实现决策记录入 [Mindraft-Log.md](Mindraft-Log.md)，供 Agent 中断后恢复上下文

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
- `skill_loader.py` + 基础 skill 文件（`note_style.yml`、`summary_style.yml`、`tagging.yml`）
- `process_notes.py`：扫描 raw_notes → LLM 处理 → 写入 ai_notes
- `memory.json` 基础结构创建
- `apply_memory_updates()`：处理 LLM 返回的记忆更新指令

**验收标准**
- `python run.py --notes-only` 成功处理 raw_notes 中的笔记
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
- `run.py` 命令语义调整：默认只处理笔记，`--analyze` 生成数据并启动服务

**不做内容**
- Chart.js 字数趋势图、CSS Grid 活跃日历（延后到 Phase 3/5）
- 用户形象（Phase 4）
- 记忆压缩、MBTI 描述、Road Map Timeline（Phase 3）
- 跨周快照 ADR-013（延后到 Phase 3）

**验收标准**
- `python run.py --analyze` 生成 dashboard 数据并自动在浏览器打开 Dashboard
- Dashboard 显示最近笔记列表、五域摘要卡片、tag 候选、每日一句
- `python run.py --serve` 只启动服务器，无数据时显示空状态提示
- LLM 失败时 Dashboard 仍可启动并显示 fallback 提示

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 3

---

### Phase 3 — 记忆系统完善

**目标**：记忆压缩机制正常运转，Dashboard 展示更丰富的自我分析

**实现内容**
- `compress_memory()`：触发压缩时归档 active_memory、调用 LLM 压缩、更新 history_archive
- `memory_compression.yml` skill 文件
- Tag 候选升级机制（count ≥ 3 → active）
- `analyze.py` 扩展：生成 `profile.json`（MBTI 风格描述）和 `roadmap.json`
- `analysis_style.yml` skill 文件
- Dashboard 新增：MBTI 风格描述卡片 + Road Map Timeline

**验收标准**
- 处理笔记数量超过阈值时，自动触发记忆压缩，history_archive 有归档记录
- Dashboard 显示 MBTI 风格描述和 Road Map Timeline

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 4

---

### Phase 4 — 用户形象（Text Card）

**目标**：Dashboard 出现随笔记进化的用户形象卡片

**实现内容**
- `analyze.py` 扩展：生成 `avatar_data.json`（Genesis Mode，首次创建）
- `assess_change_magnitude()` + `evolve_avatar()`（Evolution Mode，后续增量更新）
- `base_renderer.js` + `text_card_renderer.js`
- Dashboard：Work Me / Home Me 画像卡片区域

**验收标准**
- 首次 run.py 执行后，avatar_data.json 生成（genesis=true）
- 后续执行在现有形象上做增量更新（genesis=false）
- Dashboard 显示 Work Me / Home Me 文字卡片，内容与笔记内容相符

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 5

---

### Phase 5 — 笔记关联与链接增强

**目标**：笔记之间建立语义关联，URL 内容自动补充摘要

**实现内容**
- `relationships.json` 更新逻辑（在 process_notes.py 中实现）
- 链接抓取与摘要补充（URL → 页面内容 → LLM 摘要 → 追加到笔记）
- Dashboard：关系网络图可视化
- 追问标记交互处理（用户回答追问 → 补充到对应笔记）

**验收标准**
- 包含 URL 的笔记，ai_notes 中有 `> 📎 AI补充` 摘要追加
- relationships.json 记录笔记间关联
- Dashboard 有关系网络图

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认 → 进入 Phase 6

---

### Phase 6 — 像素画形象

**目标**：用户形象升级为 AI 生成的个性化像素画，随笔记进化演变

**实现内容**
- Replicate API 集成（像素画生成 + 基于 seed 重绘）
- `pixel_art_renderer.js`
- 三级变化机制与 denoising 参数（micro: 0.20 / macro: 0.45 / transformation: 0.80）
- Dashboard：像素画过渡动效（subtle / morph / dramatic）

**验收标准**
- 首次运行生成像素画像，`avatar_data.json` 记录 `base_image_seed`
- 后续运行根据变化量级选择重绘强度，形象可识别地延续
- Dashboard 显示带过渡效果的像素画

**阶段结束**：AI 输出实现汇总 + 待确认问题 → 人工审查确认

---

### 未来阶段（Future）

- 自动触发：GitHub Actions（push 后自动执行）
- 云端部署：Vercel（前端）+ Railway（Python 后端）
- 游戏形象：`game_renderer.js`（Phaser.js 内嵌小游戏）
- 多用户支持（账号系统 + 数据隔离）
- 移动端适配
- 接入更多笔记源（Notion / Apple Notes）
- 开放 API，供第三方集成

---

## 10. run.py 入口设计

| 命令 | 行为 |
|------|------|
| `python run.py` | 只处理新笔记 |
| `python run.py --notes-only` | 同默认，只处理新笔记（保留兼容） |
| `python run.py --analyze` | 生成 dashboard 数据并启动服务、自动打开浏览器 |
| `python run.py --serve` | 只启动本地服务器，不生成数据 |
| `python run.py --dry-run` | 模拟执行：调用 LLM 但不写入任何文件 |
| `python run.py --analyze --dry-run` | 调用 analyze 相关 LLM 但不写入文件、不启动服务 |

→ 完整实现：[Mindraft-Technical.md § 10](Mindraft-Technical.md#10-runpy-实现)

---

*产品名称：Mindraft | 文档版本：v2.0 | 最后更新：2026-06-19*  
*相关文档：[Mindraft-Technical.md](Mindraft-Technical.md) · [Mindraft-Log.md](Mindraft-Log.md)*
