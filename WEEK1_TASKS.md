# Week 1 任务清单（2026.04.17 - 04.23）

> 目标：**单 Agent 跑通 + GitHub 建仓 + 每天有 commit**

---

## Day 1 (周四 4.17)：环境 + 第一个 API 调用

### 任务
- [ ] 创建 GitHub 仓库 `multi-agent-code-reviewer`（public）
- [ ] 本地 clone，初始化 Python 项目
- [ ] 安装 uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] 用 uv 创建虚拟环境：`uv venv && source .venv/bin/activate`
- [ ] 安装核心依赖：`uv pip install anthropic langchain langgraph langchain-anthropic python-dotenv pydantic`
- [ ] 配 `.env`：`ANTHROPIC_API_KEY=...`
- [ ] 写 `scripts/hello.py` 调用 Claude API，成功返回
- [ ] push 到 GitHub（必须有今天的 commit）

### 今日八股（0.5h）
读 Anthropic Messages API 文档，理解：
- `messages` 数组结构
- `system` prompt vs user message 区别
- `max_tokens`、`temperature` 参数

### 产出
一个能跑的 `hello.py` + 初始化的仓库

---

## Day 2 (周五 4.18)：LangChain 基础

### 任务
- [ ] 跟 LangChain 官方 Tutorial 做 3 个 demo：
  1. 简单 LLM chain（Prompt → LLM → OutputParser）
  2. Few-shot prompt template
  3. Structured output（用 Pydantic schema）
- [ ] 每个 demo 单独一个文件放 `examples/` 下
- [ ] 跑通、commit

### 今日八股（0.5h）
**Prompt Engineering 3 大技术**：
- Zero-shot：直接问
- Few-shot：给 2-3 个示例
- Chain-of-Thought (CoT)："Let's think step by step"
- 为什么 CoT work？（加长模型"思考链"，释放 reasoning 能力）

### 产出
`examples/01_chain.py`、`02_fewshot.py`、`03_structured.py`

---

## Day 3 (周六 4.19)：LangGraph 官方 Tutorial

### 任务
- [ ] 跑通 LangGraph 官方 Quickstart
- [ ] 理解核心概念：StateGraph、Node、Edge、conditional_edge
- [ ] 实现一个最简单的 2-node graph（A → B），能跑
- [ ] commit

### 今日八股（0.5h）
**ReAct 范式**（必考）：
- 论文：Yao 2022 "ReAct: Synergizing Reasoning and Acting"
- 核心：Thought → Action → Observation → Thought 循环
- 相比纯 CoT 的优势：能调用外部工具，减少幻觉

面试追问准备：
- Q: ReAct 和 CoT 区别？
- A: CoT 是纯内部推理，ReAct 交错推理和工具调用
- Q: ReAct 什么时候不适用？
- A: 任务纯推理（数学题）不需要外部工具时，CoT 就够了

### 产出
`examples/04_langgraph_basic.py`

---

## Day 4 (周日 4.20)：第一个真正的 Reviewer Agent

### 任务
- [ ] 项目目录结构建立：
  ```
  src/
    agents/
      reviewer.py        # Reviewer Agent 主逻辑
    schemas/
      review.py          # Pydantic schema
    prompts/
      reviewer.py        # Prompt 模板
  tests/
  ```
- [ ] Reviewer Agent 功能：输入一段 Python 代码，输出 JSON 格式评审意见（问题类型、严重程度、建议）
- [ ] 测试：用几段有明显问题的 Python 代码验证
- [ ] commit

### 今日八股（0.5h）
**Function Calling 原理**：
- OpenAI 最早推，现在是 LLM 调用工具的标准方式
- 模型怎么学会的：synthetic data + SFT + RLHF
- JSON Schema 怎么引导模型输出
- Claude 的 Tool Use 和 OpenAI Function Calling 的区别

### 产出
`src/agents/reviewer.py`（能独立跑的 Reviewer）

---

## Day 5 (周一 4.21)：Reviewer Agent 加强

### 任务
- [ ] 引入结构化输出：用 Pydantic v2 定义 `ReviewResult`
- [ ] 改进 system prompt（参考真实代码 review 规范）
- [ ] 加 few-shot 示例
- [ ] 加一个简单的 rate-limiter / 重试机制
- [ ] 写单元测试（pytest）
- [ ] commit

### 今日八股（0.5h）
**Structured Output 的实现方式**：
- Method 1: Prompt 里明确要求 JSON 格式（最脆弱）
- Method 2: Function Calling 强制 schema（推荐）
- Method 3: JSON mode（OpenAI 原生支持）
- Method 4: Outlines / Guidance 等约束解码（最硬核）

### 产出
更完善的 Reviewer Agent + 测试

---

## Day 6 (周二 4.22)：接入真实 GitHub PR

### 任务
- [ ] 用 PyGithub 或 GitHub API 爬一个目标项目的 PR 列表（比如 requests / flask）
- [ ] 获取 PR 的 diff
- [ ] 把 diff 送进 Reviewer Agent 跑
- [ ] 把结果保存到 `outputs/reviews/*.json`
- [ ] commit

### 今日八股（0.5h）
**Tool Use vs Function Calling 对比**：
- Claude 叫 Tool Use，OpenAI 叫 Function Calling，本质一样
- 两家 API 协议差异（Claude 要 tool_use/tool_result，OpenAI 要 tool_calls）
- 并行工具调用支持情况

### 产出
能跑真实 GitHub PR 的 end-to-end demo

---

## Day 7 (周三 4.23)：整理 + 第一版 README

### 任务
- [ ] 写 README.md（英文）：
  - 项目介绍
  - 架构图（用 mermaid）
  - 快速开始
  - 当前进度（Week 1 完成）
- [ ] 录一个 30 秒的终端演示（用 asciinema 或手机录屏）
- [ ] 清理代码、统一格式（用 ruff format）
- [ ] 盘点下周要做的事
- [ ] commit + push

### 今日八股（0.5h）
**Agent 基本概念面试 5 问**：
1. 什么是 Agent？（LLM + 工具 + 记忆 + 规划）
2. Agent 和 Chain 区别？（Chain 固定流程，Agent 动态决策）
3. 为什么 Agent 现在火？（模型能力提升 + 工具生态 + MCP 标准化）
4. Agent 落地的三大挑战？（稳定性、成本、评估）
5. 你做的这个 Agent 系统主要解决什么？（用自己的项目答）

### 产出
**本周完整 GitHub 仓库**：Reviewer Agent 能跑 + README + demo + 7+ commits

---

## ⚠️ 避坑提醒

1. **API Key 不要提交**：`.env` 加到 `.gitignore`，否则会被 GitHub 扫到自动 revoke
2. **commit message 规范**：用 `feat: ...` / `fix: ...` / `docs: ...` 前缀
3. **不要过度优化**：本周就是跑通，不要花 2 小时调 prompt
4. **每天结束时 commit**：哪怕只是加了一行注释，让 GitHub contribution 图连成线
5. **遇到问题 30 分钟没解决 → 问 Claude Code**：不要自己死磕

---

## 🚀 给 Claude Code 的第一条指令

把这个当作你第一条对 Claude Code 说的话：

```
请阅读 CLAUDE.md 和 WEEK1_TASKS.md。

我现在要开始 Day 1 的任务。当前环境：
- 操作系统：[macOS / Windows / Linux]
- Python 版本：[比如 3.11]
- 已有 Anthropic API key：[是 / 否]

请帮我：
1. 初始化项目目录结构
2. 生成 .gitignore、pyproject.toml、README.md 骨架
3. 写第一个 hello.py 调用 Claude API

每步做完等我确认再继续下一步。
```
