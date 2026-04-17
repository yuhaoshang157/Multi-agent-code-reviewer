# CLAUDE.md

> 此文件由 Claude Code 在每次会话开始时自动读取，作为项目长期记忆。

## 项目身份

- **项目名**：multi-agent-code-reviewer
- **定位**：作者 Die 申请 2026 暑期实习的简历项目（LLM应用 / Agent算法方向）
- **目标公司**：字节、腾讯、阿里、AI独角兽（Moonshot/DeepSeek/智谱/MiniMax）
- **时间窗口**：2026.04.17 - 2026.05.17（1个月冲刺）
- **最终交付**：能跑、能演示、GitHub公开、README + Demo视频、能在面试讲 10 分钟

## 作者背景（简要）

- 华北电力大学（211）智能科学与技术，GPA 91.14 / 排名 2/23
- 交换：利物浦大学（2026.01-05）
- 录取：Imperial College London MSc Advanced Computing（2026.09 入学）
- 实习经历：
  - 清华大学智能产业研究院（AIR）- LLM 算法实习生（2025.06-09）：做数据中心告警收敛判定评测平台，流式推理状态机，多模型接入（GPT-4o/o1/R1/Qwen3），RAG 增强
  - 数势科技 - 算法实习（2024.12-2025.03）：LLM + SQL解析做时间实体提取
  - 无人机安全帽检测项目负责人：YOLOv8 + BiFPN + SE

## 技术基础（已有）

作者对以下概念已有扎实理解，**无需从基础讲解**：
- Transformer 架构、Attention 机制
- LoRA / QLoRA / 知识蒸馏
- DeepSpeed ZeRO 三阶段
- vLLM PagedAttention / Continuous Batching / Flash Attention
- LLaMA 3 架构：RoPE / RMSNorm / SwiGLU / GQA
- RLHF：PPO / GRPO / DPO
- PyTorch 熟练
- Python、Java、C/C++、SQL

## 技术栈决定（已拍板，不要改）

| 层 | 选择 | 备选（不用） |
|---|---|---|
| 主模型 API | Claude Sonnet 4 (`claude-sonnet-4-5`) | GPT-4o（仅做对比实验时调一次）|
| Agent 编排 | **LangGraph** | AutoGen / CrewAI（都不用）|
| RAG 向量库 | **Milvus** (docker 本地起) | Qdrant / Pinecone（不用）|
| Embedding | **BGE-M3** | OpenAI ada-002（不用）|
| 代码解析 | **tree-sitter** | 正则（不用）|
| 后端 | **FastAPI** (async) | Flask（不用）|
| 部署 | **Docker + docker-compose** | K8s（不用）|
| 结构化输出 | **Pydantic v2** | 裸 JSON（不用）|
| 包管理 | **uv**（比 pip 快 10 倍）| pip / poetry |

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

## 🚨 范围管控（重要）

作者时间极度有限（1个月，还有期末考+雅思），**严格砍掉以下，不做**：
- ❌ Tester Agent（不做真实代码执行）
- ❌ 本地部署 Qwen3
- ❌ K8s
- ❌ CI/CD
- ❌ 前端 UI（用 FastAPI 的 Swagger 页面演示就够）
- ❌ 100+ PR benchmark（只做 20-30 个）

**保留的卖点**（简历 3 条）：
1. ✅ LangGraph 多 Agent 编排
2. ✅ Milvus + BGE-M3 代码 RAG（tree-sitter AST 切分）
3. ✅ FastAPI + Docker 工程化

## 工作方式偏好

- 作者偏好**简洁回答、节省 Token**：修改原脚本而非新建，不要长篇解释
- 作者**先跑通再优化**：先出 MVP，不要过早追求完美
- 作者**每天需要有 commit**：保持 GitHub 活跃度给 HR 看
- 作者用中文沟通，但代码注释用英文（国际化，给 IC 老师/面试官也能看）

## 四周里程碑

- **Week 1 (4.17-4.23)**：环境 + 单 Agent 跑通 + GitHub 建仓
- **Week 2 (4.24-4.30)**：Multi-Agent + RAG 接入
- **Week 3 (5.01-5.07)**：FastAPI + Docker + benchmark + demo
- **Week 4 (5.08-5.17)**：投简历 + 面试

## 重要日期

- **5.9**：雅思考试
- **5.7**：简历开始投递
- **5月底-6月**：利物浦期末考

## 每次会话开始时

请先回复"了解，继续上次进度"然后执行用户的新指令。**不要每次重新解释架构**，除非用户问。
