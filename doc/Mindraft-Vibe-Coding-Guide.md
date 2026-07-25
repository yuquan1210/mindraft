# Mindraft — Vibe Coding 实操指南

> 面向首次使用 AI Agent 协作编码的开发者。
> 目标：用最少的指令，让 Agent 高效实现 Mindraft 产品。

---

## 核心原则

```
你是指挥官，Agent 是执行者。

你的职责：提供上下文、审查产出、做决策
Agent 的职责：写代码、解决技术细节、输出可运行的结果

不要自己写代码 → 描述你要什么
不要过度解释 → 给文档让 Agent 自己读
不要一次给太多 → 一个阶段一个阶段来
```

---

## 第一步：项目初始化

### 1.1 创建 Mindraft 仓库

在本地创建 mindraft 项目目录，然后用 Agent 打开它：

```
mkdir ~/Developer/mindraft && cd ~/Developer/mindraft
```

### 1.2 配置 MCP Server（关键）

MCP (Model Context Protocol) Server 让 Agent 拥有超出聊天窗口的能力——读写文件、执行命令、访问外部服务。

**VS Code 中配置 MCP Server**：

在 mindraft 项目根目录创建 `.vscode/mcp.json`：

```json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-filesystem@latest",
        "/Users/你的用户名/Developer/mindraft",
        "/Users/你的用户名/Documents/notes-vault"
      ]
    }
  }
}
```

**为什么需要 filesystem MCP？**
Mindraft 是双 Repo 架构——代码在 `mindraft/`，笔记在 `notes-vault/`。Agent 需要同时读写两个目录。MCP filesystem server 授予 Agent 对这两个路径的文件操作权限。

**后续阶段可能追加的 MCP Server**：

| 阶段 | MCP Server | 用途 |
|------|-----------|------|
| Phase 0 | filesystem | 读写双 Repo |
| Phase 2 | browser | 预览 Dashboard |
| Phase 5 | fetch | 抓取笔记中的 URL 生成摘要 |
| Phase 6 | replicate (自定义) | 调用 Replicate API 生成像素画 |

> 提示：VS Code Copilot Chat 自带文件读写和终端执行能力，很多场景不需要额外 MCP。MCP 主要用于 Agent 需要访问**当前 workspace 之外**的资源时。

---

## 第二步：喂给 Agent 的初始上下文

### 2.1 项目级指令文件（最重要）

在 mindraft 仓库根目录创建 `.github/copilot-instructions.md`（VS Code Copilot）或 `CLAUDE.md`（Claude Code），这是 Agent **每次对话都会自动读取**的上下文：

```markdown
# Mindraft 项目指令

## 项目概述
Mindraft 是一个本地运行的笔记分析引擎。用户在 Obsidian 中写日常笔记，
Mindraft 通过 LLM 自动处理、分类、生成洞见和用户画像。

## 关键文档
实现任何功能前，按以下顺序读取文档：

1. **必读速查**：`docs/Mindraft-AI-Reference.md`（核心约束、ADR、数据契约、阶段计划）
2. **阶段目标**：`docs/Mindraft.md` §9 对应 Phase（产品设计、验收标准）
3. **实现状态**：`docs/Mindraft-Log.md`（当前进度、待解决问题）
4. **按需查阅**：`docs/Mindraft-Technical.md`（具体代码示例、数据结构）

`Mindraft-Technical.md` 是参考实现草稿，不是最终规范；AI Agent 不必每次全读，只在需要具体代码片段或数据结构时查阅对应章节。

## 核心约束
- Python 3.11+，无 web 框架，前端原生 HTML/JS
- raw_notes/ 绝对不修改
- memory.json 必须用 safe_write_json() 原子写入
- LLM 返回必须用 jsonschema 校验
- 所有 Role Prompt 定义在 prompts.py，不要硬编码在业务代码中

## 当前阶段
读取 docs/Mindraft-Log.md 的「项目状态」获取当前阶段和进度。
```

### 2.2 把计划文档放进仓库

```
mindraft/
├── docs/
│   ├── Mindraft.md                  ← 产品方案（按阶段读 §9）
│   ├── Mindraft-Technical.md        ← 技术参考/代码示例（按需查阅）
│   ├── Mindraft-Log.md            ← 实现状态与 ADR
│   └── Mindraft-AI-Reference.md   ← AI Agent 必读速查手册
├── .github/
│   └── copilot-instructions.md    ← 或 CLAUDE.md
└── (Agent 将在这里生成代码)
```

**为什么放在仓库里而不是贴到聊天窗口？**
- 文档太长，贴进去会占满上下文窗口
- Agent 可以按需读取特定章节，而不是一次性加载全部
- 指令文件让 Agent 知道去哪里找文档

---

## 第三步：Phase 0 的完整 Prompt 示例

### Phase 0 前的准备清单

你自己需要先完成以下事情，再让 AI 开始实现：

- [ ] 确认 Python 版本 >= 3.11（`python --version` 或 `python3 --version`）
- [ ] 创建 mindraft 项目目录并进入
- [ ] 创建并激活虚拟环境（`python -m venv .venv`，然后 `source .venv/bin/activate`）
- [ ] 确认虚拟环境已激活（命令行前缀应显示 `(.venv)`）
- [ ] 获取至少一个 LLM API Key（Phase 0 默认用 Kimi，需要 `KIMI_API_KEY`）
- [ ] 创建 `notes-vault` 目录，包含 `raw_notes/` 和 `analysis/` 子目录
- [ ] 将 `KIMI_API_KEY` 设为环境变量，或准备 `.env` 文件

### Phase 0 的范围边界

Phase 0 只做基础设施和骨架，**不要**让 AI 提前做以下事情：

- 不要实现 `process_notes.py`、`analyze.py`、`serve.py`
- 不要创建 `dashboard/` 目录和前端文件
- 不要创建 `skills/` 目录和 skill YAML 文件
- `run.py` 只解析 `--dry-run`，加载配置，初始化日志，获取进程锁
- `--dry-run` 模式下不执行任何实际业务逻辑，不写入 `memory.json`、`ai_notes/` 等状态文件

### 启动 Prompt（复制粘贴即可）

```
先读取 docs/Mindraft-AI-Reference.md 恢复项目上下文。
再读取 docs/Mindraft-Log.md 确认当前状态。
然后读取 docs/Mindraft.md 的 §9 "Phase 0 — 基础骨架" 了解本阶段目标和验收标准。
按需读取 docs/Mindraft-Technical.md 的 §1、§2、§5.1、§9、§10 获取具体代码参考。

请实现 Phase 0 — 基础骨架。严格遵守以下边界：
1. 只实现 Phase 0 明确列出的文件，不要提前创建 Phase 1/2/3 的模块（如 process_notes.py、analyze.py、serve.py、dashboard/、skills/）。
2. run.py 只需支持 --dry-run 参数：加载 config.yml、初始化日志、获取进程锁。在 dry-run 模式下不执行笔记处理、分析、dashboard 生成等实际业务逻辑，不修改 raw_notes/，不创建 ai_notes/，不写入 memory.json 等状态文件。日志初始化是允许的。
3. config.yml 中的 api_keys 使用环境变量占位符，不要写真实 key。
4. 创建一个临时测试脚本（可放在 tests/ 下或直接临时运行），验证 LLM 调用能返回正常响应。这个脚本不要作为项目正式入口。

按顺序实现并创建以下文件：
1. 目录结构（mindraft/ 和 notes-vault/ 的骨架）
2. mindraft/requirements.txt（包含 openai、pyyaml、jsonschema、filelock）
3. mindraft/config.yml
4. mindraft/scripts/llm/base.py
5. mindraft/scripts/llm/kimi.py（使用 OpenAI 兼容接口）
6. mindraft/scripts/llm/openai.py（占位实现即可）
7. mindraft/scripts/llm/anthropic.py（占位实现即可）
8. mindraft/scripts/llm_factory.py
9. mindraft/scripts/utils.py（load_config, safe_write_json, get_process_lock, token_estimate, setup_logging）
10. mindraft/scripts/schemas.py（PROCESS_NOTE_SCHEMA 和 validate_llm_output）
11. mindraft/scripts/prompts.py（NOTE_PROCESSOR_ROLE, COMPRESSOR_ROLE, ANALYZER_ROLE, PROFILE_ROLE）
12. mindraft/run.py（CLI 骨架，支持 --dry-run，含进程锁）
13. mindraft/.env.example
14. mindraft/.gitignore

安装依赖：生成 requirements.txt 后执行 `pip install -r requirements.txt`，并确保后续所有验证命令都在已激活的虚拟环境中运行。

验收标准：
1. python run.py --dry-run 执行不报错，且 notes-vault/ 下没有新增 ai_notes/、memory.json、avatar_data.json、relationships.json 等业务状态文件。
2. 运行临时 LLM 测试脚本能调用 API 并返回正常响应（贴出运行命令和输出片段）。
3. 日志同时输出到控制台和 notes-vault/analysis/process_log.jsonl。
4. 并发执行第二个 python run.py --dry-run 时，应因进程锁超时退出并返回非零状态码。

实现完成后，输出：
- 实现汇总（做了什么、关键决策）
- 测试结果/验收证据（运行了哪些命令、输出是什么）
- 待确认问题（需要我决策的点）
```

### 验收检查清单

AI 输出结果后，你按这个清单审查：

- [ ] `requirements.txt` 已创建，包含 `openai`、`pyyaml`、`jsonschema`、`filelock`
- [ ] 在虚拟环境中执行 `pip install -r requirements.txt` 成功
- [ ] `python run.py --dry-run` 不报错
- [ ] `notes-vault/` 下没有新增 `ai_notes/`、`memory.json` 等业务状态文件
- [ ] `process_log.jsonl` 中有 DRY-RUN 相关日志
- [ ] 临时 LLM 测试脚本运行成功，且没有写死 API key
- [ ] 并发执行第二个实例时被拒绝并返回非零退出码
- [ ] `config.yml` 中 API key 使用环境变量占位符
- [ ] `.gitignore` 已忽略 `.env`、`.venv`、`__pycache__` 等
- [ ] 没有提前创建 Phase 1/2/3 的文件

### 常见翻车点

| 问题 | 对策 |
|------|------|
| AI 提前实现 `process_notes.py` | 明确说"Phase 0 不实现"，发现后要求删除 |
| `config.yml` 写死真实 API key | 要求改为 `${KIMI_API_KEY}`，并创建 `.env.example` |
| 相对导入路径错误 | 检查 `from scripts.llm.base import BaseLLM` 等路径 |
| `notes_vault_path` 中的 `~` 未展开 | 要求用 `Path(...).expanduser()` |
| `run.py` 引入未实现的模块 | 验收时确认没有 `import process_notes` / `import analyze` |
| 并发锁未生效 | 验收时必须手动测试同时启动两个实例 |
| 依赖没安装就运行 | 自己先安装 `openai pyyaml jsonschema filelock` |

### 为什么这个 Prompt 有效？

| 要素 | 说明 |
|------|------|
| **指向文档而非复述** | 让 Agent 自己读源文档，避免信息在传递中失真 |
| **明确范围** | 列出要实现的文件清单，不多不少 |
| **验收标准** | Agent 知道怎样算"完成" |
| **要求输出汇总** | 强制 Agent 在结束时回顾，你可以审查 |

---

## 第四步：后续阶段的 Prompt 模板

每个新阶段开始时，使用这个模板：

```
先读取 docs/Mindraft-AI-Reference.md 恢复上下文（必读）。
再读取 docs/Mindraft-Log.md 确认当前阶段和待解决问题。

开始实现 Phase N — [阶段名]。
读取 docs/Mindraft.md 的 §9 "Phase N" 了解目标和验收标准。
如需具体代码示例，按需读取 docs/Mindraft-Technical.md 的 §[X]。

[可选：补充的具体指示或变更]

验收标准：[从文档中复制]

实现完成后，输出：
- 实现汇总（做了什么、关键决策、遇到的问题）
- 测试结果/验收证据（运行了哪些命令、是否通过）
- 待确认问题（需要我决策的点）

确认无问题后，我会让你更新 docs/Mindraft-Log.md：
- 将 Phase N 状态改为 ✅ 已完成
- 追加实现汇总到「实现汇总历史」
- 如有待确认问题，记录到「待解决问题」
```

---

## 第五步：日常协作模式

### 5.1 审查 → 反馈 → 继续

```
Agent 实现完一个阶段
    ↓
你审查代码 + 阅读汇总
    ↓
├── 没问题 → "确认，进入 Phase N+1"
├── 有问题 → "这里有问题：[具体描述]，请修复"
└── 有疑问 → 回答 Agent 提出的待确认问题
```

### 5.2 中途修改需求

```
不好的说法：
  "我想改一下笔记处理的逻辑"

好的说法：
  "修改 process_notes.py 中的笔记分组逻辑：
   当同一天有多篇笔记时，无论长短都合并为一批处理。
   更新 docs/Mindraft-Technical.md §5.2 反映这个变更。"
```

**原则：修改需求时，同步要求更新文档。** 否则文档和代码会逐渐脱节。

### 5.3 Debug 时的沟通

```
不好的说法：
  "报错了"

好的说法：
  "运行 python run.py --dry-run 报错：
   [粘贴完整错误信息]
   请诊断并修复。"
```

### 5.4 上下文丢失后恢复

Agent 的上下文窗口有限。当对话变长或开新会话时：

```
读取 docs/Mindraft-Log.md 恢复项目上下文。
我们正在实现 Phase N。上次做到了 [简述]。
请继续。
```

**这就是 Mindraft-Log.md 存在的意义** —— 它是 Agent 的"记忆文件"。

---

## 第六步：阶段推进检查清单

### 6.1 启动阶段前（你检查）

- [ ] 上一阶段已验收完成
- [ ] `docs/Mindraft-Log.md` 中的「项目状态」已更新为当前阶段
- [ ] 没有未解决的待确认问题
- [ ] 已准备好该阶段的启动 Prompt（可复制第四步模板）

### 6.2 Agent 输出规范（每个阶段结束后必须包含）

Agent 实现完成后，必须输出以下三部分：

1. **实现汇总**
   - 完成了哪些文件
   - 关键实现决策
   - 与文档有出入的地方及原因

2. **测试结果 / 验收证据**
   - 运行了哪些命令验证
   - 是否通过验收标准
   - 如有失败，失败原因和修复方式

3. **待确认问题**
   - 需要你做决策的点
   - 方案选择的 trade-off
   - 下一步建议

### 6.3 你审查时重点检查

- [ ] 代码结构是否符合 `Mindraft-AI-Reference.md` 中的架构约定
- [ ] 是否有多余文件或提前实现的下一阶段功能
- [ ] `raw_notes/` 是否未被修改
- [ ] `memory.json` 是否使用 `safe_write_json()` 写入
- [ ] LLM 返回是否经过 `jsonschema` 校验
- [ ] Role Prompt 是否放在 `prompts.py` 而非硬编码
- [ ] 验收标准是否真的通过了（要求 Agent 提供运行证据）

### 6.4 阶段交接流程

```
Agent 输出实现汇总 + 测试结果 + 待确认问题
    ↓
你审查代码和汇总
    ↓
├── 没问题 → 让 Agent 更新 Mindraft-Log.md → 进入 Phase N+1
├── 有小问题 → 指出具体问题，Agent 修复后重新审查
└── 有大问题/需求变更 → 要求 Agent 回退或重新设计，更新文档
```

**原则：不更新 Mindraft-Log.md 就不算阶段结束。**

---

## Prompt 技巧速查

| 场景 | Prompt 写法 |
|------|------------|
| 让 Agent 恢复上下文 | `先读取 docs/Mindraft-AI-Reference.md 和 docs/Mindraft-Log.md` |
| 让 Agent 读阶段目标 | `读取 docs/Mindraft.md §9 "Phase N — ..."` |
| 让 Agent 查技术细节 | `按需读取 docs/Mindraft-Technical.md §X` |
| 限制实现范围 | `只实现 X 和 Y，不要提前做 Z` |
| 要求解释决策 | `实现完成后，解释为什么选择了这个方案` |
| 拒绝过度设计 | `用最简单的方式实现，不要添加我没要求的功能` |
| 要求测试 | `写完代码后运行一次验证，确认不报错` |
| 要求输出三部分 | `实现完成后输出：实现汇总、测试结果、待确认问题` |
| 批量修改 | `同时修改 A.py 和 B.py 中的 [X]` |
| 回退错误修改 | `撤销上一次对 X.py 的修改，恢复到之前的版本` |
| 更新日志 | `将这次实现更新到 docs/Mindraft-Log.md` |
| 更新技术文档 | `如实现与 docs/Mindraft-Technical.md 有出入，说明是否需同步更新` |

---

## 常见陷阱与对策

### ❌ 一次给太多

```
不要：
  "实现 Phase 0 到 Phase 3 的所有功能"

要：
  "实现 Phase 0"
  → 审查确认 →
  "实现 Phase 1"
```

Agent 一次做太多，质量会下降，错误会累积。

### ❌ 不审查就继续

每个阶段结束后必须审查，详见"第六步：阶段推进检查清单"。

核心检查项：
- 代码结构是否符合 `Mindraft-AI-Reference.md` 中的架构约定？
- 是否有多余的文件或提前实现的下一阶段功能？
- 验收标准是否真的通过了？要求 Agent 提供运行证据。
- `Mindraft-Log.md` 是否已更新？

### ❌ 让 Agent 读太多文档

`Mindraft-Technical.md` 是参考实现草稿，不是最终规范，不要每次让 Agent 全读。

正确做法：
- 启动阶段时：让 Agent 先读 `Mindraft-AI-Reference.md` + `Mindraft-Log.md`
- 需要具体代码时再指引：按需读取 `Mindraft-Technical.md §X`

### ❌ 文档和代码脱节

如果你在对话中临时改了需求但没更新文档，下次 Agent 读文档时会用旧的信息。

**规则：**
- 每次实现变更后，要求 Agent 更新 `Mindraft-Log.md`。
- 如果实现与 `Mindraft-Technical.md` 的参考代码有出入，让 Agent 说明是否需要同步更新技术文档。
- 如果产品方案或核心约束需要变更，同步更新 `Mindraft.md` 和 `Mindraft-AI-Reference.md`。

### ❌ API Key 泄露

```
不要：在 config.yml 中写真实 API key
要：  使用环境变量 ${KIMI_API_KEY}，在 .env 文件中配置

提醒 Agent：
  "config.yml 中的 API key 使用环境变量占位符，
   创建 .env.example 说明需要哪些环境变量，
   .env 加入 .gitignore"
```

---

## 完整工作流总结

```
┌─ 准备阶段 ──────────────────────────────────┐
│                                              │
│  1. 创建 mindraft 仓库                        │
│  2. 放入四份文档到 docs/                      │
│     · Mindraft.md（产品方案）                  │
│     · Mindraft-Technical.md（技术参考）        │
│     · Mindraft-Log.md（实现日志）             │
│     · Mindraft-AI-Reference.md（AI 必读速查）  │
│  3. 创建 copilot-instructions.md             │
│     或 CLAUDE.md，引用 Mindraft-AI-Reference.md │
│  4. 配置 MCP Server（如需要）                 │
│                                              │
└──────────────────────────────────────────────┘
            │
            ▼
┌─ Phase N 循环 ──────────────────────────────┐
│                                              │
│  5. 发送阶段启动 Prompt                       │
│     → Agent 读 Mindraft-AI-Reference.md      │
│     → Agent 读 Mindraft-Log.md               │
│     → Agent 读 Mindraft.md §9 阶段目标       │
│     → 按需读 Mindraft-Technical.md            │
│     → 实现 → 输出汇总 + 测试结果 + 待确认问题    │
│                                              │
│  6. 你审查代码 + 回答问题                      │
│     → 确认 / 修改 / 追问                      │
│                                              │
│  7. Agent 更新 Mindraft-Log.md               │
│                                              │
│  8. 确认 → 进入 Phase N+1                    │
│                                              │
└──────────────────────────────────────────────┘
            │
            ▼
         产品完成
```

---

*指南版本：v1.1 | 最后更新：2026-07-25*
*配套文档：[Mindraft.md](Mindraft.md) · [Mindraft-Technical.md](Mindraft-Technical.md) · [Mindraft-Log.md](Mindraft-Log.md) · [Mindraft-AI-Reference.md](Mindraft-AI-Reference.md)*
