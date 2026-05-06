# CLAUDE.md

> Auto-loaded by Claude Code at session start.
> 个人学习日志见 `docs/LEARNING_LOG.md`

## 技术栈（已拍板，不要改）

| 层 | 选择 |
|---|---|
| 主模型 API | Claude Sonnet 4.6 via OpenRouter (`anthropic/claude-sonnet-4.6`) |
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

> 目标：用系统实验回答"RAG 到底有没有用"，产出可量化的 BERTScore 数据。
> **时间约束**：5.7 简历投递、5.9 雅思，Week 4 有效工期约 4 天，优先完成实验一。

### 文件结构

```
src/eval/
├── __init__.py
└── evaluator.py              # 评估框架核心：采样 + 运行 + BERTScore + 统计检验

outputs/eval/
├── exp1_rag_ablation.json    # 实验一：RAG vs No-RAG
├── exp2_embed_strategy.json  # 实验二：嵌入策略对比（可选）
└── exp3_data_scale.json      # 实验三：数据规模缩放（可选）
```

### 核心变更（已完成）：`ReviewState` 新增 `use_rag` 字段

```python
# src/agents/multi_agent.py — 已加入
class ReviewState(TypedDict):
    ...
    use_rag: bool  # 传 False 关闭 RAG，用于消融实验

# reviewer_node 已改为：
if state.get("use_rag", True):
    # 执行 RAG 召回 ...

# 调用示例
graph.invoke({"code": code, ..., "use_rag": False})   # 关闭 RAG
graph.invoke({"code": code, ..., "use_rag": True})    # 开启 RAG（默认）
```

### 依赖安装

```bash
uv pip install bert-score scipy
# bert_score 首次运行自动下载 microsoft/deberta-xlarge-mnli（约 900 MB），只需一次
```

### `evaluator.py` 接口设计

```python
# ---- 底层运行函数 ----
def run_review(code: str, ground_truth: str, use_rag: bool) -> dict:
    """调 graph.invoke，返回:
    {"review_text": str, "review_score": int, "issues_count": int}
    """

# ---- 评分函数 ----
def score_bertscore(predictions: list[str], references: list[str]) -> list[float]:
    """用 bert_score 库计算每条样本的 F1，model_type="microsoft/deberta-xlarge-mnli"
    返回长度与输入相同的 float 列表。
    """

# ---- 实验一：RAG vs No-RAG ----
def exp1_rag_ablation(n_samples: int = 50, seed: int = 42) -> None:
    """
    1. 从 data/eval_set.jsonl 随机采样 n_samples 条（seed 固定）
    2. 每条 code 跑两遍：use_rag=True 和 use_rag=False
    3. 计算两组 BERTScore F1 均值 + 配对 t 检验（scipy.stats.ttest_rel）
    4. 写 outputs/eval/exp1_rag_ablation.json
    """

# ---- 实验二：嵌入策略 ----
def exp2_embed_strategy(n_samples: int = 30) -> None:
    """
    需提前准备三个 Milvus collection：
      code_review_rag_A（嵌入 code，当前默认）
      code_review_rag_B（嵌入 review）
      code_review_rag_C（嵌入 code + review 拼接）
    对比三种策略下 BERTScore，写 exp2_embed_strategy.json
    """

# ---- 实验三：数据规模 ----
def exp3_data_scale(n_samples: int = 30) -> None:
    """
    需提前准备三个 collection：1K / 10K / 73K 规模
    对比不同数据量下 BERTScore，写 exp3_data_scale.json
    """

# ---- CLI 入口 ----
# python -m src.eval.evaluator --exp rag_ablation --n 50
# python -m src.eval.evaluator --exp embed_strategy --n 30
# python -m src.eval.evaluator --exp data_scale --n 30
# python -m src.eval.evaluator --exp rag_ablation --n 5   ← 先用 5 条验证流程
```

### 实验一输出格式 (`exp1_rag_ablation.json`)

```json
{
  "experiment": "rag_ablation",
  "n_samples": 50,
  "seed": 42,
  "rag": {
    "bertscore_f1_mean": 0.712,
    "bertscore_f1_std": 0.043,
    "avg_review_score": 6.4,
    "avg_issues_count": 3.8
  },
  "no_rag": {
    "bertscore_f1_mean": 0.688,
    "bertscore_f1_std": 0.051,
    "avg_review_score": 5.9,
    "avg_issues_count": 3.1
  },
  "delta_bertscore_f1": 0.024,
  "t_stat": 2.31,
  "p_value": 0.025,
  "significant_at_0.05": true
}
```

### 成本估算

| 实验 | 样本数 | API 调用次数 | 估算费用 |
|---|---|---|---|
| 实验一 | 50 | 150（3 节点 × 2 组 × 50）| ~$6.50 |
| 实验二 | 30 | 270（3 节点 × 3 策略 × 30）| ~$3.90 |
| 实验三 | 30 | 270（3 节点 × 3 规模 × 30）| ~$3.90 |
| **合计** | | ~690 次调用 | **~$14** |

> 建议先用 `--n 5` 验证流程跑通（~$0.65），再扩到 50 条。

### 实验二三的前置准备

实验二（嵌入策略）和实验三（数据规模）需要额外构建 Milvus collection：

```bash
# 实验二：重建两个不同嵌入字段的 collection（在 rag_store.py 加参数支持）
# 实验三：从 rag_kb.jsonl 分别采样 1K/10K 写成新 JSONL，再 ingest
python -m src.tools.rag_store --ingest --jsonl data/rag_kb_1k.jsonl --collection code_review_1k
python -m src.tools.rag_store --ingest --jsonl data/rag_kb_10k.jsonl --collection code_review_10k
# 73K 用现有 code_review_rag
```

### 时间安排（修订版，已按实际截止日调整）

| 天 | 日期 | 任务 |
|---|---|---|
| Day 1 | 5.06 | 代码 review + bug 修复 + CLAUDE.md 完善（本次）|
| Day 2 | 5.07 | 搭 `src/eval/` 框架，`--n 5` 验证，简历投递 |
| Day 3 | 5.08 | 实验一全量（50 条），产出 BERTScore 对比数据 |
| Day 4 | 5.09（雅思后）| 实验二/三酌情，汇总结果写入 README |
| Day 5 | 5.10+ | README 加实验表，项目收尾，准备面试讲解 |

### 实验四（可选）：检索策略对比

| 方式 | 说明 | 面试价值 |
|---|---|---|
| 单路稠密（当前） | BGE-M3 语义匹配 | baseline |
| 混合检索 | BM25（稀疏）+ BGE（稠密）双路 RRF 融合 | 工业界标准 |
| 重排序 | Cross-Encoder Reranker 精排 top-k | 两阶段检索是生产标配 |

### 实验五（可选）：Self-Reflection Agent

在 Reviewer 之后加自省节点：模型检查自己的 review 是否有误判或遗漏。
实现方式：`StateGraph` 新增 `reflector` 节点，`ReviewState` 加 `reflection: str` 字段。
用实验一的 eval set 对比 reflection 前后 BERTScore 变化。

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

> 最后更新：2026-05-06。按对项目稳定性和面试价值的影响排序。

### 高优先级（直接影响正确性）

#### 1. 集成测试缺少 `use_rag` 字段
- **文件**：`tests/test_multi_agent.py:77`
- **问题**：`graph.invoke({"code": code, "plan": None, "review": None, "report": ""})` 未传 `use_rag`；虽然 `.get("use_rag", True)` 有默认值不会崩，但 State schema 已声明该字段，语义不完整
- **修复**：加 `"use_rag": True`

#### 2. `rag_store.py` 全局单例线程竞争
- **文件**：`src/tools/rag_store.py:27-38`
- **问题**：FastAPI 把同步 endpoint 放进线程池；两个并发请求都看到 `_embedder is None`，导致 BGE-M3 被重复初始化（GPU 内存翻倍占用）
- **修复**：double-checked locking
  ```python
  import threading
  _lock = threading.Lock()
  def _get_embedder():
      global _embedder
      if _embedder is None:
          with _lock:
              if _embedder is None:
                  ...
  ```
- `_get_client()` 同理

#### 3. RAG 结果无上限，大 PR 撑爆 prompt
- **文件**：`src/agents/multi_agent.py:62-73`
- **问题**：`top_k=2` per chunk，15 个函数的 diff → 最多 30 条结果全拼进 prompt，大幅增加 token 成本且稀释重点
- **修复**：加全局上限常量 `MAX_RAG_RESULTS = 5`，命中后 `break`

#### 4. FastAPI 入参无校验
- **文件**：`src/api/main.py:15-18`
- **问题**：`repo="notvalid"` 或 `pr_number=-1` 触发 PyGithub 原始异常，500 响应直接暴露内部堆栈
- **修复**：在 `ReviewRequest` 里加 `@field_validator`，校验 `repo` 格式为 `owner/name`、`pr_number > 0`

---

### 中优先级（Week 4 实验前置条件）

#### 5. `rag_store.py` CLI 不支持多集合参数
- **文件**：`src/tools/rag_store.py:183-190`
- **问题**：实验二/三需要往不同 collection 注入不同嵌入字段的数据，但 CLI 写死了 `COLLECTION` 和嵌入 `code` 字段
- **修复**：`init_rag_from_dataset()` 增加 `collection` 和 `embed_field` 参数，CLI 加 `--collection` / `--embed-field` 选项

#### 6. `src/eval/` 目录不存在
- **问题**：`python -m src.eval.evaluator` 直接失败
- **修复**：创建 `src/eval/__init__.py` + `src/eval/evaluator.py` 骨架

#### 7. `TokenUsageCallback` 无法区分节点级 token 消耗
- **文件**：`src/tools/token_tracker.py`
- **问题**：三个节点的 token 都累加进总量，看不出 Reviewer（有 RAG）比 Planner 贵多少
- **修复**：记录每次 `on_llm_end` 调用明细 `self.calls: list[dict]`，支持按调用序号分析

---

### 低优先级（可观测性 / 代码整洁）

#### 8. 全 `print()` 无日志级别
- **问题**：生产服务里无 timestamp、无级别、无法静音 RAG 进度刷新（`[RAG] Embedded 1000 items...`）
- **修复**：改用 `logging.getLogger(__name__)`，通过 `LOG_LEVEL=WARNING` 环境变量控制

#### 9. `benchmark.py` HTTP 调用用标准库 `urllib.request`
- **问题**：项目已依赖 `requests`，benchmark 却用更啰嗦的 `urllib.request`，不一致
- **修复**：改用 `requests.post(url, json=payload, timeout=180)`

#### 10. `code_chunker.py` 只处理 Python，非 Python 文件静默降级
- **问题**：评 huggingface/transformers PR 时若改动涉及 `.js`/`.yaml`，tree-sitter Python 解析失败 fallback 成整段残缺代码送 RAG，召回质量差
- **当前状态**：已知限制，简历项目可接受；生产级需要按文件扩展名路由到对应 Language grammar

#### 11. RAG 上下文质量：用完整函数体替代纯 diff 行
- **问题**：`chunk_diff` 只提取 `+` 新增行，函数内部小改动提取出来没有 `def`，tree-sitter 找不到函数节点，fallback 成残缺代码
- **优化方案**：解析 diff 的 `@@` 行号 → GitHub API 拿原始文件 → tree-sitter 定位包含该行的完整函数体
- **当前状态**：暂不做，fallback 对简历项目够用

#### 12. `CLAUDE.md` 技术栈表模型名与代码不一致
- **问题**：`CLAUDE.md:10` 写的是 `claude-3-5-sonnet`，`multi_agent.py:27` 实际用 `claude-sonnet-4.6`
- **修复**：把表里的模型 ID 改成 `anthropic/claude-sonnet-4.6`

## ⚠️ 避坑提醒

1. **API Key 不要提交**：`.env` 加到 `.gitignore`
2. **不要过度优化**：本周就是跑通，不要花 2 小时调 prompt
3. **遇到问题 30 分钟没解决 → 问 Claude Code**：不要自己死磕

## 每次会话开始时

请先回复"了解，继续上次进度"然后执行用户的新指令。不要重新解释架构，除非用户问。
