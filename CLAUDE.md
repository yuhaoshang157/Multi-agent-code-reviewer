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

### ✅ Week 1 Day 6 (2026-04-21，提前完成)
- 安装 PyGithub，`src/tools/github_fetcher.py`：抓取真实 GitHub PR diff
- `src/tools/review_runner.py`：PR diff → multi-agent Pipeline → 保存 JSON 报告
- 端到端验证：psf/requests PR #6710 → 评分 6/10，5 个问题，报告存入 `outputs/reviews/`

### ✅ Week 1 Day 5 (2026-04-21)
- `src/prompts/templates.py`：改进三节点 system prompt，加 few-shot 示例，全部改为中文输出
- `src/agents/multi_agent.py`：加 `max_retries=3` / `request_timeout=60` 重试机制
- `tests/test_multi_agent.py`：新建 pytest 测试（6 个单元测试 + 1 个集成测试）
- `pyproject.toml`：注册 `integration` 自定义 mark

### ✅ Week 1 Day 4 (2026-04-20)
- 跳过单 Agent，直接构建三节点多 Agent Pipeline
- 建立 `src/` 目录结构：`agents/` / `schemas/` / `prompts/`
- `src/schemas/review.py`：Pydantic schema（ReviewAspect / PlannerOutput / ReviewIssue / ReviewResult）
- `src/prompts/templates.py`：三节点 system prompt + user prompt 构造函数
- `src/agents/multi_agent.py`：LangGraph 三节点完整 Pipeline（Planner → Reviewer → Reporter）跑通
- 踩坑：OpenRouter 模型 ID 需用小数点格式 `anthropic/claude-sonnet-4.6`，横杠/缺版本号均 404
- 追加 Karpathy 行为规范到 CLAUDE.md

### ✅ Week 1 Day 7 + Week 2 Day 1 (2026-04-22，提前开始 Week 2)
- README.md 全面重写：Mermaid 架构图、Quick Start、项目结构、Roadmap
- ruff format + lint fix：10 个文件格式化，4 个 lint 问题自动修复
- `docker-compose.yml`：Milvus 完整栈（etcd + MinIO + Milvus），本地 19530 端口
- 安装 pymilvus（2.6.12）+ FlagEmbedding（BGE-M3）
- `examples/05_milvus_basic.py`：BGE-M3 embed 代码片段 → 存入 Milvus → 相似度检索跑通
- 踩坑：`HF_ENDPOINT=https://hf-mirror.com` 对 `.DS_Store` 返回 403，改用官方源即可
- 验证：查询 f-string SQL 拼接，召回 SQL injection 相似度 0.835 ✅

### ✅ Week 2 Day 2 (2026-04-23，概念复习 + RAG 接入 + 环境整理)
- 排查 `05_milvus_basic.py` 报错：根因是 PyCharm 运行按钮默认工作目录为脚本所在目录，相对路径 `models/bge-m3` 失效
- 修复：用 `Path(__file__).parent.parent` 构造绝对路径，不再依赖工作目录
- 修复：insert 后补加 `client.flush(COLLECTION)`，解决 Growing Segment 未刷写导致 search 返回空的问题
- 深化理解：Docker 容器化原理、Milvus 三组件职责、稠密向量 vs 稀疏向量本质区别、BGE-M3 双输出头、flush 分层存储逻辑
- `src/tools/rag_store.py`：25 条种子 bug 模式（SQL注入/资源泄漏/命令注入等）+ BGE-M3 embed + Milvus 存取封装
- `src/tools/code_chunker.py`：tree-sitter 解析 Python AST，按函数/类切 chunk
- Reviewer Agent 接入 RAG：每个 chunk 查 Milvus → 召回历史 bug → 注入 reviewer prompt
- 端到端验证：3 函数代码 → RAG 召回 → 评分 3/10，5 个问题全部命中 ✅
- 整理记忆系统：新建全局记忆（`~/.claude/memory/`）+ 项目记忆精简至 4 个文件
- 删除 conda env `multi-agent-code-reviewer`（包已全部在 `.venv`）

## 里程碑

- **Week 1 (4.17-4.23)**：环境 + 单 Agent 跑通 + GitHub 建仓
- **Week 2 (4.24-4.30)**：Multi-Agent + RAG 接入
- **Week 3 (5.01-5.07)**：FastAPI + Docker + benchmark + demo

## 每次会话开始时

请先回复"了解，继续上次进度"然后执行用户的新指令。不要重新解释架构，除非用户问。

