# Mindraft — AI Agent 速查手册

> 供 AI Agent 快速恢复上下文使用。是以下文档的浓缩版：
> - `doc/Mindraft.md`（产品方案）
> - `doc/Mindraft-Technical.md`（技术参考/代码示例）
> - `doc/Mindraft-Vibe-Coding-Guide.md`（协作指南）
> - `doc/Mindraft-Log.md`（实现日志与 ADR）
>
> 完整实现细节、代码示例、协作流程请回原文档按需查阅。

---

## 1. 项目定位

Mindraft 是本地运行的个人笔记分析引擎。用户用 Obsidian 在 `notes-vault/raw_notes/` 写 Markdown，运行 `python run.py` 后：

1. LLM 处理每篇笔记，生成结构化版本写入 `notes-vault/ai_notes/`；
2. 蒸馏记忆到 `notes-vault/analysis/memory.json`；
3. 生成 `relationships.json`、`avatar_data.json`、Dashboard 数据；
4. 本地 Web Dashboard 展示分析结果。

核心原则：
- 写作零负担，不改变 Obsidian 习惯。
- **原始笔记不可侵犯**：`raw_notes/` 永远只读。
- **记忆只增不减**：不删除历史信号，只归档或压缩。
- **形象只进化不重建**：默认增量更新，非必要不 Genesis。
- LLM、Skill、Renderer 全部可替换。

---

## 2. 当前状态（来自 Mindraft-Log.md）

- **当前阶段**：Phase 1（已完成）→ Phase 2（未开始）
- **最后更新**：2026-07-26
- **实现方式**：Vibe-coding —— AI 实现代码，人工审查 + 指挥
- **所有 ADR 已确认**：ADR-001 ~ ADR-013
- **待解决问题**：无
- **Phase 1 延后项**：batching 短笔记合并、summary_style.yml、relationships、URL 抓取、追问交互、像素画形象

---

## 3. 关键 ADR（不可违反）

| ADR | 内容 |
|-----|------|
| ADR-001 | 双 Repo：`mindraft`（代码）与 `notes-vault`（笔记）分离，通过 `config.yml → notes_vault_path` 关联。 |
| ADR-002 | 增量蒸馏记忆：LLM 每次只看 `active_memory`（~600 tokens）+ 当前笔记。 |
| ADR-003 | 记忆只增不减：`memory_updates` 只允许 `APPEND_TO`、`SET_IF_NEW`，其余忽略。 |
| ADR-004 | 形象进化：默认 `evolve_avatar()` 增量更新，仅在首次运行、重置或重大转变时 Genesis。 |
| ADR-005 | LLM 抽象层：`BaseLLM` + `llm_factory.py`，按 `config.llm_provider` 切换模型。 |
| ADR-006 | Skill YAML 配置：`skill_loader.py` 按 operation 自动拼装 system prompt。 |
| ADR-007 | Renderer 插件体系：`avatar_data.json` 数据契约固定，渲染器可替换。 |
| ADR-008 | 原子写入 + 进程锁：核心 JSON 用 `safe_write_json()`，`run.py` 启动时获取 `filelock`。 |
| ADR-009 | LLM 输出 JSON Schema 校验：所有 LLM 返回用 `jsonschema` 校验。 |
| ADR-010 | 笔记预筛选与批量处理：`note_filter.py` 跳过无意义笔记，短笔记合并一批。 |
| ADR-011 | 逐篇 checkpoint：每篇处理完立即持久化 `memory.json`，失败只跳过当前组。 |
| ADR-012 | 前端配置导出：`analyze.py` 将前端所需配置导出为 `dashboard/data/config.json`。 |
| ADR-013 | 跨周快照：检测到跨越自然周时自动生成 `snapshots/YYYY-WXX.json`。 |

---

## 4. 目录结构

```
notes-vault/
├── raw_notes/          # 原始笔记，AI 绝不修改
├── ai_notes/           # AI 处理后笔记
│   ├── work/
│   │   ├── daily/
│   │   ├── epic_and_cards/
│   │   ├── tips/
│   │   └── publish/
│   ├── study/
│   └── life/
│       ├── workout/
│       └── cooking/
└── analysis/
    ├── memory.json
    ├── avatar_data.json
    ├── relationships.json
    ├── tags.json
    ├── process_log.jsonl
    ├── snapshots/
    └── .mindraft.lock

mindraft/
├── config.yml
├── run.py
├── scripts/
│   ├── llm/            # base.py + kimi.py + openai.py + anthropic.py
│   ├── llm_factory.py
│   ├── skill_loader.py
│   ├── process_notes.py
│   ├── note_filter.py
│   ├── analyze.py
│   ├── serve.py
│   ├── schemas.py
│   ├── prompts.py
│   └── utils.py
├── skills/             # *.yml Skill 配置
└── dashboard/          # 前端静态文件
    ├── index.html
    ├── style.css
    ├── app.js
    ├── renderers/
    └── data/
```

---

## 5. 核心数据契约

### 5.1 `memory.json`

```json
{
  "meta": {
    "version": 47,
    "last_updated": "2026-06-15",
    "processed_notes": ["2026-06-01.md", "2026-06-14.md", "2026-06-15.md"],
    "active_memory_token_estimate": 620
  },
  "active_memory": {
    "work": {
      "current_focus": "登录模块重构，卡在权限设计上",
      "ongoing_projects": ["认证系统", "dashboard迁移"],
      "goals": ["提升代码可维护性"],
      "energy_pattern": "上午效率高，下午容易疲惫",
      "stress_sources": ["权限设计边界不清晰"],
      "recurring_signals": ["容易在细节上花过多时间"],
      "recent_mood_trend": "疲惫但有动力"
    },
    "life": {
      "current_routines": ["早上健身", "周末做饭"],
      "interests_observed": ["电影", "编程", "烹饪"],
      "social_connections": ["朋友A"],
      "places": ["家", "健身房"],
      "important_people": ["mentor"],
      "recurring_signals": ["睡眠不规律是持续困扰"],
      "recent_mood_trend": "稳定"
    },
    "growth": {
      "learning_topics": ["系统设计", "权限模型"],
      "active_skills": ["Python", "React"],
      "challenges": ["分布式事务"],
      "recurring_signals": ["喜欢通过项目实践学习"]
    },
    "wellbeing": {
      "physical_patterns": ["早上健身", "久坐"],
      "mental_patterns": ["压力大时容易过度思考"],
      "recovery_activities": ["看电影", "散步"],
      "recurring_signals": ["睡眠不足时效率下降"]
    },
    "identity": {
      "core_traits": ["注重细节", "内向", "逻辑导向"],
      "values": ["质量优先", "持续学习"],
      "self_perception": ["偏内向，独处时恢复能量", "目标感强，对自身完美主义有自我觉察"],
      "mbti_hints": ["偏好结构化思考", "对抽象概念感兴趣"],
      "recurring_signals": ["独处时恢复能量"]
    }
  },
  "tag_candidates": {
    "backend": { "count": 5, "status": "pending" },
    "sprint": { "count": 3, "status": "pending" },
    "side-project": { "count": 2, "status": "pending" }
  },
  "history_archive": [
    {
      "archived_at": "2026-06-07",
      "trigger": "compression",
      "note_count_at_time": 31,
      "snapshot": { ... }
    }
  ]
}
```

### 5.2 `avatar_data.json`

```json
{
  "generated_at": "2026-06-15",
  "genesis": false,
  "avatar_identity": {
    "version": 4,
    "established_at": "2026-06-01",
    "last_evolved_at": "2026-06-15",
    "base_image_seed": "kimi_seed_20260601_7a3f",
    "core_traits": ["注重细节", "内向", "逻辑导向"],
    "visual_anchors": ["眼镜", "深色系穿搭", "短发"],
    "style_era": {
      "name": "early_builder",
      "started_at": "2026-06-01",
      "description": "初期摸索阶段，专注于构建基础，对细节有执着"
    }
  },
  "evolution_log": [
    {
      "timestamp": "2026-06-15",
      "change_magnitude": "micro",
      "trigger_notes": ["2026-06-15.md"],
      "changes_summary": { ... }
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
    "recent_highlights": ["正在攻克一个复杂的权限设计问题"],
    "thought_bubble": "这个边界条件到底该怎么处理...",
    "room_objects": ["机械键盘", "多个显示器", "咖啡杯", "白板"],
    "color_palette": ["#1a1a2e", "#16213e", "#a78bfa"]
  },
  "home_me": { ... }
}
```

### 5.3 `relationships.json`

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

---

## 6. 核心接口与约定

### 6.1 `config.yml` 关键项

| 配置项 | 说明 | 典型值 |
|--------|------|--------|
| `notes_vault_path` | 笔记仓库本地路径 | `~/Developer/GitHub/notes-vault` |
| `llm_provider` | 切换 LLM | `kimi \| openai \| anthropic` |
| `llm_model` | 模型名 | `moonshot-v1-32k` |
| `api_keys.*` | 环境变量占位 | `${KIMI_API_KEY}` |
| `memory.active_memory_token_threshold` | 触发压缩阈值 | `1500` |
| `memory.compression_target_ratio` | 压缩目标 | `0.55` |
| `skills.*.enabled` | Skill 开关 | `true/false` |
| `note_filter.*` | 预筛选与批量配置 | 见原技术文档 |
| `avatar.renderer` | 渲染器 | `text_card \| pixel_art \| animated_sprite \| game` |
| `token_estimation` | Token 估算方式 | `char_ratio \| tiktoken` |
| `dashboard_port` | 本地服务端口 | `8080` |

### 6.2 Skill 与 operation 对应关系

| operation | 挂载的 Skill |
|-----------|-------------|
| `process_note` | `note_style` + `tagging` |
| `enrich_with_link` | `note_style` |
| `generate_daily_summary` | `summary_style` |
| `generate_profile` | `analysis_style` |
| `generate_mbti_description` | `analysis_style` |
| `generate_avatar_data` | `analysis_style` |
| `compress_memory` | `memory_compression` |

### 6.3 命名约定

| 类别 | 可选值 |
|------|--------|
| LLM 提供者 | `kimi \| openai \| anthropic` |
| 渲染器类型 | `text_card \| pixel_art \| animated_sprite \| game` |
| 变化量级 | `micro \| macro \| transformation` |
| Memory 操作 | `APPEND_TO \| SET_IF_NEW`（仅这两种，其余忽略） |
| Token 估算 | `char_ratio \| tiktoken` |
| 笔记处理 | `skip \| single \| batch` |

### 6.4 关键文件路径

| 文件 | 路径 |
|------|------|
| 主配置 | `mindraft/config.yml` |
| 记忆状态 | `{notes_vault}/analysis/memory.json` |
| 形象数据 | `{notes_vault}/analysis/avatar_data.json` |
| 关联图谱 | `{notes_vault}/analysis/relationships.json` |
| 日志 | `{notes_vault}/analysis/process_log.jsonl` |
| 进程锁 | `{notes_vault}/analysis/.mindraft.lock` |
| 前端配置 | `mindraft/dashboard/data/config.json` |

---

## 7. 开发阶段计划

| Phase | 目标 | 核心产物 |
|-------|------|---------|
| 0 | 基础骨架 | `.venv`、`.gitignore`、`.env.example`、`requirements.txt`、`config.yml`、LLM 抽象层、`utils.py`、`schemas.py`、`prompts.py`、`run.py` |
| 1 | 笔记处理核心 | `process_notes.py`、`note_filter.py`、skill 系统、`memory.json` |
| 2 | Dashboard MVP | `analyze.py`、前端 HTML/JS、`serve.py`、dashboard/data/*.json |
| 3 | 记忆系统完善 | 记忆压缩、MBTI 描述、Road Map、跨周快照 ADR-013、Chart.js 字数图/活跃日历 |
| 4 | 用户形象 TextCard | `avatar_data.json`、TextCardRenderer |
| 5 | 笔记关联增强 | `relationships.json`、URL 摘要 |
| 6 | 像素画形象 | Replicate API、PixelArtRenderer |

**当前阶段：Phase 2（进行中）。**

---

## 8. AI Agent 读取建议

实现新功能前，按以下顺序读取：

1. **必读**：`doc/Mindraft-AI-Reference.md`（本文件）—— 恢复上下文。
2. **按阶段精读**：`doc/Mindraft.md` §9 对应 Phase 的目标与验收标准。
3. **按需查阅**：`doc/Mindraft-Technical.md` 对应章节的具体代码示例。
4. **开始/结束时**：读取/更新 `doc/Mindraft-Log.md` 的项目状态和实现汇总。

**不需要每次读取完整 `Mindraft-Technical.md`**；只有在需要具体代码片段、schema 或数据结构细节时才查阅。

---

## 9. 给 AI 的核心约束

- **不修改** `raw_notes/` 任何文件。
- `memory.json` 等核心状态文件必须通过 `safe_write_json()` 原子写入。
- LLM 返回必须通过 `jsonschema` 校验；失败时记录日志并跳过当前组。
- Role Prompt 必须定义在 `prompts.py`，业务代码不硬编码 system prompt。
- 所有 LLM 调用只通过 `BaseLLM` 接口，不直接实例化具体模型类。
- 失败时优雅降级：单篇/单组失败不中断整个 `run.py` 流程。
- 每次实现变更后，同步更新 `doc/Mindraft-Log.md`。
