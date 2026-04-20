# CLAUDE.md

> Auto-loaded by Claude Code at session start.

## 技术栈（已拍板，不要改）

| 层 | 选择 |
|---|---|
| 主模型 API | Claude 3.5 Sonnet via OpenRouter (`anthropic/claude-3-5-sonnet`) |
| Agent 编排 | LangGraph |
| RAG 向量库 | Milvus (docker 本地起) |
| Embedding | BGE-M3 |
| 代码解析 | tree-sitter |
| 后端 | FastAPI (async) |
| 部署 | Docker + docker-compose |
| 结构化输出 | Pydantic v2 |
| 包管理 | uv |

## 系统架构（已定，不要重构）

```
FastAPI Gateway
    ↓
LangGraph Orchestrator (StateGraph)
    ├── Planner Agent   → 拆解 PR 评审任务
    ├── Reviewer Agent  → 评审，调用 RAG 查历史 bug
    └── Reporter Agent  → 聚合生成 Markdown 报告
           ↓
    MCP Tool Layer（简化版，仅 file I/O + Git）
           ↓
    Milvus 向量库 (代码 RAG) + tree-sitter AST 切分
```

## 范围管控

不做：
- ❌ Tester Agent
- ❌ 本地部署 Qwen3
- ❌ K8s / CI/CD
- ❌ 前端 UI（Swagger 演示即可）
- ❌ 100+ PR benchmark（20-30 个）

## 工作方式

- 简洁回答，节省 Token
- 先跑通再优化
- 修改现有文件，不新建
- 代码注释用英文

## 进度记录

### ✅ Week 1 Day 1 (2026-04-17)
- 项目目录结构初始化
- uv 虚拟环境 + 核心依赖安装
- `scripts/hello.py` 调通 OpenRouter → Claude 3.5 Sonnet
- pyproject.toml、.gitignore、README.md
- GitHub 仓库建立并 push

### ✅ Week 1 Day 2 (2026-04-18)
- 安装 `langchain-openai`，使用 OpenRouter 兼容接口
- `examples/01_chain.py`：LCEL 管道（ChatPromptTemplate | ChatOpenAI | StrOutputParser）
- `examples/02_fewshot.py`：FewShotChatMessagePromptTemplate 多轮示例注入
- `examples/03_structured.py`：Pydantic v2 + with_structured_output 结构化输出
- 踩坑：Anthropic 不支持 JSON Schema integer 字段的 `ge/le` 约束，去掉即可

### ✅ Week 1 Day 3 (2026-04-19)
- `examples/04_langgraph_basic.py`：LangGraph StateGraph 2-node pipeline（Planner → Reviewer）
- 核心概念：State / Node / Reducer / add_messages / Builder / compile

### ✅ Week 1 Day 4 (2026-04-20)
- 跳过单 Agent，直接构建三节点多 Agent Pipeline
- 建立 `src/` 目录结构：`agents/` / `schemas/` / `prompts/`
- `src/schemas/review.py`：Pydantic schema（ReviewAspect / PlannerOutput / ReviewIssue / ReviewResult）
- `src/prompts/templates.py`：三节点 system prompt + user prompt 构造函数
- `src/agents/multi_agent.py`：LangGraph 三节点完整 Pipeline（Planner → Reviewer → Reporter）跑通
- 踩坑：OpenRouter 模型 ID 需用小数点格式 `anthropic/claude-sonnet-4.6`，横杠/缺版本号均 404
- 追加 Karpathy 行为规范到 CLAUDE.md

## 里程碑

- **Week 1 (4.17-4.23)**：环境 + 单 Agent 跑通 + GitHub 建仓
- **Week 2 (4.24-4.30)**：Multi-Agent + RAG 接入
- **Week 3 (5.01-5.07)**：FastAPI + Docker + benchmark + demo

## 每次会话开始时

请先回复"了解，继续上次进度"然后执行用户的新指令。不要重新解释架构，除非用户问。

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
