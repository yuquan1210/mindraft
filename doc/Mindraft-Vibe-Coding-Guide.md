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
实现任何功能前，先读取以下文档获取完整上下文：
- 产品方案：`docs/Mindraft.md`（产品设计、流程、阶段计划）
- 技术参考：`docs/Mindraft-Technical.md`（代码示例、数据结构）
- 实现日志：`docs/Mindraft-Log.md`（当前进度、ADR、待解决问题）

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
├── docs/                          ← 把三份文档放这里
│   ├── Mindraft.md
│   ├── Mindraft-Technical.md
│   └── Mindraft-Log.md
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

### 启动 Prompt（复制粘贴即可）

```
读取 docs/Mindraft-Log.md 了解当前项目状态。
读取 docs/Mindraft.md 的 §9 "Phase 0 — 基础骨架" 了解本阶段目标。
读取 docs/Mindraft-Technical.md 的 §1 和 §2 获取配置和 LLM 代码。

按 Phase 0 的目标实现以下内容：
1. 创建完整的目录结构
2. config.yml（使用 docs 中定义的格式）
3. scripts/llm/base.py + kimi.py + llm_factory.py
4. scripts/utils.py（safe_write_json, get_process_lock, token_estimate, setup_logging）
5. scripts/schemas.py（PROCESS_NOTE_SCHEMA）
6. scripts/prompts.py（所有 Base Role 定义）
7. run.py（含进程锁和 dry-run）

验收标准：python run.py --dry-run 执行不报错。

实现完成后，输出：
- 实现汇总（做了什么）
- 待确认问题（需要我决策的点）
```

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
先读取 docs/Mindraft-Log.md 恢复上下文。

开始实现 Phase N — [阶段名]。
读取 docs/Mindraft.md 的 §9 "Phase N" 了解目标和验收标准。
读取 docs/Mindraft-Technical.md 的 §[X] 获取技术细节。

[可选：补充的具体指示或变更]

验收标准：[从文档中复制]

完成后更新 docs/Mindraft-Log.md：
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

## Prompt 技巧速查

| 场景 | Prompt 写法 |
|------|------------|
| 让 Agent 读文档 | `读取 docs/Mindraft-Technical.md §5` |
| 限制实现范围 | `只实现 X 和 Y，不要提前做 Z` |
| 要求解释决策 | `实现完成后，解释为什么选择了这个方案` |
| 拒绝过度设计 | `用最简单的方式实现，不要添加我没要求的功能` |
| 要求测试 | `写完代码后运行一次验证，确认不报错` |
| 批量修改 | `同时修改 A.py 和 B.py 中的 [X]` |
| 回退错误修改 | `撤销上一次对 X.py 的修改，恢复到之前的版本` |
| 更新文档 | `将这次的实现变更同步更新到 docs/Mindraft-Log.md` |

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

每个阶段结束后必须审查：
- 代码结构是否符合文档定义？
- 是否有多余的文件或功能？
- 验收标准是否真的通过了？

### ❌ 文档和代码脱节

如果你在对话中临时改了需求但没更新文档，下次 Agent 读文档时会用旧的信息。

**规则：每次变更都要求 Agent 同步更新 Mindraft-Log.md。**

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
│  2. 放入三份文档到 docs/                      │
│  3. 创建 copilot-instructions.md             │
│  4. 配置 MCP Server（如需要）                 │
│                                              │
└──────────────────────────────────────────────┘
            │
            ▼
┌─ Phase N 循环 ──────────────────────────────┐
│                                              │
│  5. 发送阶段启动 Prompt                       │
│     → Agent 读文档 → 实现 → 输出汇总          │
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

*指南版本：v1.0 | 最后更新：2026-06-19*
*配套文档：[# Mindraft.md](# Mindraft.md) · [Mindraft-Technical.md](Mindraft-Technical.md) · [Mindraft-Log.md](Mindraft-Log.md)*
