# CLAUDE.md

> Auto-loaded by Claude Code at session start.
> 个人学习日志见 `docs/LEARNING_LOG.md`

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
- `src/tools/rag_store.py`：25 条种子 bug 模式 + BGE-M3 embed + Milvus 存取封装
- `src/tools/code_chunker.py`：tree-sitter 解析 Python AST，按函数/类切 chunk
- Reviewer Agent 接入 RAG：每个 chunk 查 Milvus → 召回历史 bug → 注入 reviewer prompt
- 端到端验证：3 函数代码 → RAG 召回 → 评分 3/10，5 个问题全部命中 ✅

### ✅ Week 2 Day 3 (2026-04-24，代码复习日)
- 逐行审阅昨天新写的 4 个文件：`rag_store.py` / `code_chunker.py` / `multi_agent.py` / `templates.py`

### ✅ Week 2 Day 4-5 (2026-04-25~26，FastAPI 网关 + 代码复习)
- `src/agents/multi_agent.py`：RAG 切块从 `chunk_python_code` 改为 `chunk_diff or chunk_python_code`
- `src/tools/review_runner.py`：返回值从文件名改为 `output` 字典
- `src/api/main.py`：新建 FastAPI 网关，`POST /review` + `GET /health`，Swagger UI
- `pyproject.toml`：补全缺失依赖

### ✅ Week 2 Day 6 (2026-04-27，Docker 容器化)
- `Dockerfile`：python:3.12-slim，分层构建，EXPOSE 8000
- `.dockerignore`：排除 models/、.venv/、outputs/、.env
- `docker-compose.yml`：新增 api 服务，挂载 models/ 和 outputs/
- `src/tools/rag_store.py`：MILVUS_URI 改读环境变量

### ✅ Week 2 Day 7 (2026-04-29，Benchmark + Token 追踪)
- `src/tools/token_tracker.py`：LangChain BaseCallbackHandler，跨三节点累计 token
- Benchmark 执行：6 repos × 4 PR = 23/24 PR，平均 6.2/10，~37 min
- Docker 重建 + README 更新

### ✅ Week 3 Day 1 (2026-04-30，数据集重构 + RAG 全量升级 + Docs 重组)

**数据集重构**
- `src/data/build_dataset.py`：修复 6 处编号错误，删除死代码 `load_buginspy`（158 行）
- 重新生成干净数据：600 eval + 73,343 RAG KB（6 数据集，无 buginspy 污染）
- 踩坑：发现 `dataset_stats.json` 含 buginspy 残留（700 eval），重跑后修正
- 分层采样：生成 `data/rag_kb_5k.jsonl`（3887 条），6 源各 ≤800 条

**RAG 全量升级**
- `src/tools/rag_store.py`：25 条手工种子 → 73K 真实人工 review 数据
  - 新集合 `code_review_rag`，字段：id/vector/source/code/review/language
  - 流式读取 JSONL + 批量嵌入 + 批量插入，避免内存溢出
  - 查询返回 `source`/`review`/`language` 替代旧的 `label`/`comment`
- 踩坑：PyTorch 安装的是 CPU 版本 (`2.10.0+cpu`)，BGE-M3 嵌入 73K 需 ~32h
  - 解决：`uv pip install torch --index-url https://download.pytorch.org/whl/cu124`
  - RTX 4060 8GB GPU 加速后，73K 嵌入 ~1.8h 完成
- `src/agents/multi_agent.py`：RAG 字段适配（`hit["label"]` → `hit["source"]`，`hit["comment"]` → `hit["review"]`）
  - 去重 key 改为 `source + review[:200]`

**Docs 重组**
- `docs/dataset_sources.md` → `docs/web_sources.md`：增加"访问原因"列，按任务分组
- `docs/CLAUDE.local.md` → `docs/LEARNING_LOG.md`：重命名为学习日志
- `docs/datasets.md`：6 数据集详细说明 → 3 张总表（总览/字段映射/语言分布），284 行精简至 130 行
- `docs/data_cleaning.md`：6 数据集重复步骤合并为问题总览表 + 清洗漏斗总表，390 行精简至 120 行
- 根目录 `CLAUDE.md` 恢复完整内容（自动加载入口），新增 Week 4 实验规划
- 删除根目录 `CLAUDE.local.md`（已移至 docs/）

## 里程碑

- **Week 1 (4.17-4.23)**：环境 + 单 Agent 跑通 + GitHub 建仓 ✅
- **Week 2 (4.24-4.30)**：Multi-Agent + RAG 接入 + FastAPI + Docker ✅
- **Week 3 (5.01-5.07)**：数据集构建 + RAG 升级 ✅（提前完成）

---

## Week 4 规划（实验验证）

> 目标：用系统实验回答"RAG 到底有没有用"、"怎么让它更有用"。
> 面试时能说出实验设计、结论和数据支撑，就是深度。

### 实验一：RAG vs No-RAG 消融实验

| 维度 | 说明 |
|---|---|
| 数据 | `eval_set.jsonl` 中随机抽 50-100 条，覆盖 6 数据集和主要语言 |
| 方法 | 每条 code 送 Reviewer Agent 跑两遍——带 RAG vs 不带 RAG |
| 指标 | BERTScore（与 ground truth review 语义相似度）、review_score、issues_count |
| 统计 | 配对 t 检验验证差异显著性 |
| 产出 | `src/eval/evaluator.py` + `outputs/eval/rag_vs_no_rag.json` |

### 实验二：嵌入策略消融实验

嵌入策略 = 把什么内容变成向量 + 用什么查什么。

| 变体 | RAG 知识库嵌入 | 查询 | 假设 |
|---|---|---|---|
| A（当前 baseline） | `code` 字段 | code → code 相似 | 代码长得像 → 审查意见相关 |
| B | `review` 字段 | code → review 相似 | 直接匹配审查意见语义 |
| C | `code + review` 拼接 | code → code+review | 信息最多，但向量空间混杂 |

> 如果 B 组 BERTScore 显著高于 A 组 → 重建 Milvus 集合，切换嵌入策略。

### 实验三：数据规模缩放实验

| 规模 | 条数 | 说明 |
|---|---|---|
| 小 | 1,000 | 随机采样 |
| 中 | 10,000 | 分层采样（每源等量） |
| 大 | 73,343 | 全量 |

> 检验"数据越多效果越好"的假设，找到收益递减点。

### 实验四（可选）：检索策略对比

| 方式 | 说明 | 面试价值 |
|---|---|---|
| 单路稠密（当前） | BGE-M3 语义匹配 | baseline |
| 混合检索 | BM25（稀疏）+ BGE（稠密）双路融合 | 工业界标准 |
| 重排序 | 加 Cross-Encoder Reranker 精排 top-k | 两阶段检索是生产标配 |

### 实验五（可选）：Self-Reflection Agent

在 Reviewer 之后加一个自省环节：模型检查自己的 review 是否有误判或遗漏。用实验一的 eval set 对比 reflection 前后的 BERTScore 变化。

### 时间安排

| 天 | 任务 |
|---|---|
| Day 1 | 搭建实验框架：`src/eval/evaluator.py`，BERTScore 计算，两组对比 |
| Day 2 | 执行实验一（RAG vs No-RAG），输出对比报告 |
| Day 3 | 执行实验二（嵌入策略消融），确定最优策略 |
| Day 4 | 执行实验三（数据规模），确定最优数据量 |
| Day 5 | 汇总实验报告，更新 README 加入实验数据 |

---

## 项目深度总结（面试准备）

### 当前可讲的亮点

1. **LangGraph 多 Agent 编排**：三节点 Pipeline（Planner → Reviewer → Reporter），State 共享、节点职责分离
2. **代码 RAG**：73K 真实 code review 数据集 + tree-sitter AST 切块 + BGE-M3 稠密检索 + Milvus 向量库
3. **数据工程**：6 源异构数据清洗、统一 schema、分层采样、eval/rag 严格分离
4. **工程化**：FastAPI + Docker Compose + Token 追踪 + Benchmark
5. **实验验证**（Week 4 完成后）：消融实验 + BERTScore + 统计检验

### 面试可能追问的技术点

- **嵌入策略**：为什么嵌入 code vs review？code→review 跨模态匹配的 trade-off
- **检索质量**：COSINE vs IP 区别？HNSW 索引原理？nlist 参数如何影响召回率？
- **稠密 vs 稀疏**：BGE-M3 学的是什么语义？什么时候 BM25 更好？
- **Agent 设计**：为什么三节点线性而不是并行？Self-Reflection 如何实现？
- **数据质量**：如何评估异构数据源的清洗效果？数据泄露如何防止？

## 🔧 待优化项

### RAG 上下文质量：用完整函数体替代纯 diff 行
- **当前问题**：`chunk_diff` 只提取 `+` 新增行，若 PR 只改了函数内部几行，extracted code 没有 `def`，tree-sitter 找不到函数节点
- **优化方案**：解析 diff 的 `@@` 行号 → GitHub API 拿原始文件 → tree-sitter 定位完整函数体
- **当前状态**：暂不做，fallback 对简历项目够用

## ⚠️ 避坑提醒

1. **API Key 不要提交**：`.env` 加到 `.gitignore`
2. **不要过度优化**：本周就是跑通，不要花 2 小时调 prompt
3. **遇到问题 30 分钟没解决 → 问 Claude Code**：不要自己死磕

## 每次会话开始时

请先回复"了解，继续上次进度"然后执行用户的新指令。不要重新解释架构，除非用户问。
