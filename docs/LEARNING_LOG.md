# Learning Log（学习日志，不上传 GitHub）

> 每日学习记录：提问、踩坑、犯错、详细进度。
> 项目整体规划见根目录 `CLAUDE.md`。

---

## 2026-04-30 — 数据集重构 + RAG 全量升级 + Docs 重组

### 今日提问记录

**数据处理**
- "数据是如何处理的？什么是按源分层采样？"
  → 完整 5 阶段：原始采集 → 清洗（去空/去重/格式转换/语言推断） → 统一 schema → split_and_tag 切分 eval/rag → Milvus 向量库构建
  → 分层采样 = 每组（源）各取等量，保证小数据集不被淹没。vs 简单随机：小源会被大源淹没
- "ground truth review 是什么？"
  → eval_set.jsonl 中的 `review` 字段，是真实人类审查者写的评审意见，用于和模型生成 review 计算 BERTScore

**GPU / 环境**
- "我有 GPU 为什么不使用？"
  → 根因：PyTorch 装成了 CPU 版本（`torch==2.10.0+cpu`）而非 CUDA 版本
  → 检查方法：`torch.cuda.is_available()`；版本确认：`torch.__version__` 看 `+cpu` 后缀
  → 解决方案：`uv pip install torch --index-url https://download.pytorch.org/whl/cu124`
  → GPU 加速效果：128 条嵌入从 ~50s（CPU）降至 ~0.6s（GPU），73K 全量从 ~32h 降至 ~1.8h

**架构与设计**
- "嵌入策略是什么？"
  → 嵌入策略 = 把什么内容变成向量 + 用什么查什么
  → 当前（A）：嵌入 code 字段，用 code 查 code。问题：代码长得像 ≠ 审查意见相关
  → 变体（B）：嵌入 review 字段，用 code 查 review。可能优势：直接匹配审查意见语义
  → 这是实验二要验证的核心假设

**文档管理**
- "根目录两个 md 可否删除？每次运行还会自动读取吗？"
  → CLAUDE.md 在根目录会被 Claude Code 自动加载，不能删（已恢复完整内容）
  → CLAUDE.local.md 不需要自动加载，已删除并移至 docs/LEARNING_LOG.md

### 今日踩坑

1. **BugsInPy 数据污染**：`dataset_stats.json` 显示 7 数据集 700 eval，但代码 DATASETS 列表只有 6 个
   → 根因：之前运行过的输出文件残留，代码已移除 buginspy 但数据未重跑
   → 修复：重跑 `python src/data/build_dataset.py`，验证输出为 600 eval + 6 数据集

2. **PyTorch CPU-only 问题**：BGE-M3 在 CPU 上一个 batch（32 条）需要 ~50s，73K 需要 ~32h
   → `torch.__version__` 发现是 `2.10.0+cpu`
   → 安装 CUDA 版后重跑，~1.8h 完成

3. **RAG 召回质量不理想**：73K 真实数据召回相似度 0.63-0.70，低于种子数据 0.83
   → 原因：真实 review 没有按 bug 类型分类标注，code 相似 ≠ review 相关
   → 留待 Week 4 实验验证（嵌入策略消融 + RAG vs No-RAG 对比）

### 今日所学

- **分层采样 vs 简单随机采样**：分层保底（每个源有代表性），随机会导致小源被淹没
- **PyTorch 版本检查**：`torch.cuda.is_available()` + `torch.__version__` 检查是否 GPU 版本
- **Milvus 简单 API 的动态 Schema**：不需要预定义字段，MilvusClient 自动推断类型
- **BGE-M3 GPU 配置**：`BGEM3FlagModel(path, use_fp16=True, device="cuda")`
- **嵌入策略本质**：向量空间中"查询点"和"被查点"的对应关系设计——嵌入什么、查什么
- **BERTScore 适用场景**：代码审查用词多样，BLEU 不适用，BERTScore 语义匹配更合理

### 今日进度（详见 CLAUDE.md Week 3 Day 1）

- Phase A: build_dataset.py 修复 + 重新生成干净数据
- Phase B: RAG store 全量升级（25 种子 → 73K 真实 review，GPU 嵌入）
- Phase C: Reviewer Agent 字段适配
- Docs 重组：web_sources 改名、LEARNING_LOG 改名、两个文档精简表格化
- Week 4 实验规划写入 CLAUDE.md

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

## 重要日期

- **5.9**：雅思考试
- **5.7**：简历开始投递
- **5月底-6月**：利物浦期末考

## 简历卖点（3条）

1. ✅ LangGraph 多 Agent 编排
2. ✅ Milvus + BGE-M3 代码 RAG（tree-sitter AST 切分）
3. ✅ FastAPI + Docker 工程化

## 每次会话开始时

请先回复"了解，继续上次进度"然后执行用户的新指令。**不要每次重新解释架构**，除非用户问。

---

## Week 1 任务清单（2026.04.17 - 04.23）

> 目标：**单 Agent 跑通 + GitHub 建仓 + 每天有 commit**

### ✅ Day 1 (周四 4.17)：环境 + 第一个 API 调用

#### 任务
- [x] 创建 GitHub 仓库 `multi-agent-code-reviewer`（public）
- [x] 本地 clone，初始化 Python 项目
- [x] 安装 uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- [x] 用 uv 创建虚拟环境：`uv venv && source .venv/bin/activate`
- [x] 安装核心依赖：`uv pip install anthropic langchain langgraph langchain-anthropic python-dotenv pydantic`
- [x] 配 `.env`：`ANTHROPIC_API_KEY=...`
- [x] 写 `scripts/hello.py` 调用 Claude API，成功返回
- [x] push 到 GitHub（必须有今天的 commit）

#### 今日八股（0.5h）
读 Anthropic Messages API 文档，理解：
- `messages` 数组结构
- `system` prompt vs user message 区别
- `max_tokens`、`temperature` 参数

#### 产出
一个能跑的 `hello.py` + 初始化的仓库

---

### ✅ Day 2 (周五 4.18)：LangChain 基础

#### 任务
- [x] 跟 LangChain 官方 Tutorial 做 3 个 demo：
  1. 简单 LLM chain（Prompt → LLM → OutputParser）
  2. Few-shot prompt template
  3. Structured output（用 Pydantic schema）
- [x] 每个 demo 单独一个文件放 `examples/` 下
- [x] 跑通、commit

#### 今日收获 / 踩坑
- `|` 管道符底层是 `__or__` 运算符重载，返回 `RunnableSequence`，invoke 时顺序执行
- `with_structured_output` 底层用 Function Calling（tool_choice 强制），不是 prompt 控制
- Anthropic 不支持 JSON Schema integer 字段的 `ge/le` 约束（去掉即可）
- `user` 和 `human` 在 prompt 里等价，统一用 `user` 与 OpenAI 风格对齐
- Pydantic `BaseModel` 的 Model 是"数据模型"，和 AI Model 无关

#### 今日提问记录（理解薄弱点）

**LangChain 框架**
- LangChain 是什么，模块有哪些（core / openai / community / LangGraph）
- `|` 管道符如何连接组件（`__or__` 重载 → `RunnableSequence` → invoke 顺序执行）
- ChatPromptTemplate 是什么数据类型，内容存在哪里（`prompt.messages[1].prompt.template`）
- `{占位符}` 如何与 invoke 参数匹配（key 名称对齐，同 `str.format()`）
- `user` 和 `human` 的区别（无区别，都映射 HumanMessage）
- Template 有哪些种类（ChatPromptTemplate / FewShotChatMessagePromptTemplate / MessagesPlaceholder）
- FewShot 中 examples dict 的 key 如何与 example_prompt 占位符绑定（key 名称对应占位符名称）
- 完善 prompt 的结构（Role / Context / Instruction / Few-shot / Output Format / Input）

**OutputParser**
- StrOutputParser 是什么、做什么（从 AIMessage 取 `.content` 纯文本）
- Parser 的种类和区别（Str / Json / with_structured_output）
- `with_structured_output` vs `StrOutputParser` 的关系（都是 Parser，输出格式不同）

**Pydantic**
- Pydantic 是什么，和 LangChain 的关系（独立库，LangChain 内部调用）
- BaseModel 是什么，为什么叫 Model（数据模型，非 AI 模型）
- Pydantic 的实际功能（类型校验 + JSON Schema 生成 + IDE 补全）
- IDE 补全是什么意思（类型明确后编辑器能提示字段名）
- 为什么不直接传 dict 给 `with_structured_output`（可以，但无类型校验和补全）

**Function Calling / Tool Use**
- Function Calling 是什么，和普通文本输出的区别（独立协议字段，非文本夹带 JSON）
- 手动要求 JSON vs Function Calling 的可靠性对比（协议层隔离 + tool_choice 强制）
- Tool Use 是训练进去的还是 prompt 控制的（SFT 训练植入，非 prompt）
- Pydantic 如何影响传给模型的内容（生成 JSON Schema → tools 参数 → 模型强制返回结构化 input）

**环境 / 工具**
- 如何自己测试代码（激活 .venv，改 test_code 变量跑）
- `load_dotenv()` 的作用（从 .env 注入环境变量到 os.environ）
- dotenv 全称（python-dotenv，处理 `.` 开头配置文件）

#### 今日八股（0.5h）
**Prompt Engineering 3 大技术**：
- Zero-shot：直接问
- Few-shot：给 2-3 个示例
- Chain-of-Thought (CoT)："Let's think step by step"
- 为什么 CoT work？（加长模型"思考链"，释放 reasoning 能力）

#### 产出
`examples/01_chain.py`、`02_fewshot.py`、`03_structured.py`

---

### ✅ Day 3 (周六 4.19)：LangGraph 官方 Tutorial

#### 任务
- [x] 跑通 LangGraph 官方 Quickstart
- [x] 理解核心概念：StateGraph、Node、Edge、conditional_edge
- [x] 实现一个最简单的 2-node graph（A → B），能跑
- [x] commit

#### 今日收获 / 踩坑
- LangGraph 把 Agent 执行流程建模成有向图，支持分支、循环，比 LangChain Chain 更灵活
- State 是所有 Node 共享的"全局黑板"，Node 只读写 State，不互相调用
- `add_messages` 是 LangGraph 提供的 reducer，append-only，防止 Node 覆盖对话历史
- `Annotated[list, add_messages]` = 类型是 list + 更新规则是 add_messages，框架读取元数据
- `builder.compile()` 之后才能 invoke，构建和执行分离

#### 今日提问记录（理解薄弱点）

**LangGraph 核心概念**
- LangGraph 是什么（基于有向图的 Agent 编排框架，支持分支/循环/多 Agent 并行）
- Node 是什么，作用是什么（处理函数，输入 State，输出 State 更新 dict）
- Builder 是什么组件（StateGraph 构造器，声明拓扑结构，compile() 后才可执行）
- State 是什么，为什么用 TypedDict（共享黑板，高频读写不需要校验，TypedDict 零开销）

**Reducer**
- Reducer 名字来源（函数式编程"归约/折叠"，不是减法，把多个值合并成一个）
- `Annotated[list, add_messages]` 含义（Annotated = 类型 + 元数据，框架读取后决定合并规则）
- 没有 Reducer 的字段默认行为（直接覆盖，最后写的赢）

**Message 类型**
- 除了 HumanMessage 还有哪些（AIMessage / SystemMessage / ToolMessage）
- ToolMessage 什么时候出现（Function Calling 流程中，工具结果传回模型）

**ChatPromptTemplate vs 直接 llm.invoke**
- 两种写法区别（有无模板中间层，llm 只认 messages list，模板只是帮你构造 list）
- 什么时候用模板（prompt 固定复用），什么时候直接构造（动态拼接逻辑复杂）

**Pydantic vs TypedDict**
- 核心区别（Pydantic 有运行时校验 + JSON Schema，TypedDict 是带类型注释的普通 dict）
- 使用场景（系统边界用 Pydantic，内部流转用 TypedDict）
- 数据校验是什么（在入口检查类型/规则，不符合立刻报错，防止错误数据流入系统）
- ge/le 全拼（greater/less than or equal，Anthropic 不支持 integer 带此约束的原因）
- with_structured_output 完整流程（BaseModel → JSON Schema → Function Call → JSON 字符串 → BaseModel 实例）
- BaseModel 是数据格式定义（class 是模具，实例化后才是数据）

#### 今日八股（0.5h）
**ReAct 范式**（必考）：
- 论文：Yao 2022 "ReAct: Synergizing Reasoning and Acting"
- 核心：Thought → Action → Observation → Thought 循环
- 相比纯 CoT 的优势：能调用外部工具，减少幻觉

面试追问准备：
- Q: ReAct 和 CoT 区别？
- A: CoT 是纯内部推理，ReAct 交错推理和工具调用
- Q: ReAct 什么时候不适用？
- A: 任务纯推理（数学题）不需要外部工具时，CoT 就够了

#### 产出
`examples/04_langgraph_basic.py`

---

### ✅ Day 4 (周日 4.20)：Multi-Agent Pipeline

#### 任务
- [x] 建立 `src/` 目录结构（agents / schemas / prompts）
- [x] 三节点 Pipeline 跑通（Planner → Reviewer → Reporter）
- [x] commit

#### 今日收获 / 踩坑
- 单 Agent vs 多 Agent：单 Agent 一个 LLM 干所有事，多 Agent 多个专职 LLM 通过 State 协作
- OpenRouter 模型 ID 必须用小数点：`anthropic/claude-sonnet-4.6`，横杠格式会 404
- Reporter 节点用普通 `llm` 不用 `with_structured_output`，因为输出是 Markdown 文本不需要结构化

#### 今日提问记录（理解薄弱点）

**类型注解 / typing 模块**
- `Optional[X]` 是什么：Python `typing`（type hinting utilities）标准库的类型标签，等价于 `X | None`，运行时不生效
- 类型标签在哪里起作用：IDE 实时补全（PyCharm/VSCode 内置 pyright）+ mypy 手动静态检查，两者本质相同只是触发时机不同
- 类型标签 vs Pydantic 校验：TypedDict 层只是标签给 IDE 看；Pydantic 层运行时真正强制校验
- 常用 typing 标签：`Optional` / `Union` / `Literal` / `Annotated` / `Any` / `Final`
- LangGraph State 最常用三类：`Annotated`（自定义 reducer）/ `Optional`（初始为 None）/ 普通类型（直接覆盖）

**LangGraph 节点返回值**
- `return {"review": result}` 含义：只返回需要更新的字段，LangGraph 自动 merge 到 State，其他字段不变
- 节点职责分离：每个节点只写自己负责的 State 字段

**json 模块**
- `json` 全拼：JavaScript Object Notation
- `dump` 含义：倾倒/转储，原样导出数据
- `dumps` = dump to string；`dump` = dump to file
- `model_dump()` 含义：Pydantic 对象 → Python dict（Pydantic 自带方法）
- 完整链路：Pydantic对象 → `model_dump()` → dict → `json.dumps()` → JSON字符串 → 塞进 prompt

**AIMessage 结构**
- `llm.invoke()` 返回 `AIMessage` 对象，含 `content`（文本）/ `response_metadata`（模型信息）/ `usage_metadata`
- `with_structured_output` 返回直接是 Pydantic 对象，不是 AIMessage，所以取值方式不同

#### 今日八股（0.5h）
**Function Calling 原理**：
- OpenAI 最早推，现在是 LLM 调用工具的标准方式
- 模型怎么学会的：synthetic data + SFT + RLHF
- JSON Schema 怎么引导模型输出
- Claude 的 Tool Use 和 OpenAI Function Calling 的区别

#### 产出
`src/agents/reviewer.py`（能独立跑的 Reviewer）

---

### ✅ Day 5 (周二 4.21)：Reviewer Agent 加强

#### 任务
- [x] 引入结构化输出：用 Pydantic v2 定义 `ReviewResult`（Day 4 已完成）
- [x] 改进 system prompt（加优先级顺序、严格规则、中文输出）
- [x] 加 few-shot 示例（内嵌在 REVIEWER_SYSTEM，XML 标签包裹）
- [x] 加重试机制（`max_retries=3`、`request_timeout=60`）
- [x] 写单元测试（pytest，6 个单元测试全通过）
- [x] commit

#### 今日收获 / 踩坑
- ChatPromptTemplate vs 直接构造 messages：两者效果相同，动态拼接复杂时直接用函数更灵活
- XML 标签包裹 few-shot：Claude 对 XML 有特殊识别能力，边界清晰不会误解
- pytest 命名规范：文件必须 `test_*.py`，函数必须 `test_` 开头，自动发现无需注册
- uv 是 pip 的替代品（Rust 实现），只管包安装速度，不替代 conda 的环境管理
- IDE 标红 import：不是缺包，是解释器没指向项目 `.venv`，需在 PyCharm 手动切换

#### 今日提问记录（理解薄弱点）

**Prompt 工程**
- system prompt 结构：角色定位 → 任务说明 → 规则约束 → 输出要求
- few-shot 示例作用：直接展示期望输出格式，比文字描述更可靠
- XML 标签为何有效：Claude 训练时见过大量 XML，能准确识别示例边界
- ChatPromptTemplate vs 直接构造：前者适合固定模板，后者适合动态拼接

**pytest 模块**
- `pytest`（Python Test Framework）全拼：测试框架，自动扫描 `test_*.py` 执行
- `assert` 含义：断言，条件为假时测试失败并打印实际值
- `@pytest.mark.integration`：装饰器，给测试打标签，用 `-m` 参数筛选执行
- 单元测试 vs 集成测试：单元不调 API（快/免费），集成调真实模型（慢/花钱）
- `-v`（verbose）：详细模式，显示每个测试的通过/失败状态

**重试机制**
- `max_retries=3`：API 失败时自动重试，触发条件：限流(429) / 服务器错误(5xx) / 网络抖动
- `request_timeout=60`：单次请求最长等待时间，防止请求一直挂起

**uv 命令**
- `uv`（Ultra-fast Python package manager）全拼：Rust 实现的 pip 替代品
- 常用：`uv venv`（建环境）/ `uv pip install`（装包）/ `uv pip list`（查包）
- 和 conda 关系：uv 替代 pip，不替代 conda；conda 还负责非 Python 包（如 CUDA）

#### 每日结束检查
- [x] 实际完成 vs 计划对齐 ✅ 全部完成
- [x] 新增：prompt 全部改为中文输出
- [x] commit 了吗？→ 待执行

---

### ✅ Day 6 (周三 4.22)：接入真实 GitHub PR

#### 任务
- [x] 用 PyGithub 获取 psf/requests PR #6710 的 diff
- [x] 获取 PR 的 diff
- [x] 把 diff 送进 multi-agent Pipeline 跑通
- [x] 把结果保存到 `outputs/reviews/psf_requests_pr6710.json`
- [x] commit

#### 今日收获 / 踩坑
- PR diff = difference，逐行差异，`+` 新增 `-` 删除
- GitHub Token 两种：classic（简单，按大类权限）/ fine-grained（精确到单仓库单操作）
- 只读公开仓库只需勾选 `public_repo` scope，最小权限原则

#### 今日提问记录（理解薄弱点）

**PyGithub / GitHub API**
- `diff`（difference）全拼：两个版本之间的逐行差异文本
- `src`（source）全拼：存放源代码的约定目录名
- PR = Pull Request：开发者请求把自己分支的改动合并进主分支
- Token classic vs fine-grained：classic 按大类权限，fine-grained 精确到单仓库操作

**文件操作**
- `os.makedirs(path, exist_ok=True)`：递归创建多级目录，`exist_ok=True` 表示目录已存在不报错
- `with open(filename, "w", encoding="utf-8") as f:`：上下文管理器，自动关闭文件，`"w"` = write 写入模式
- `repo_name.replace('/', '_')`：`replace(old, new)` 把所有 `/` 替换成 `_`，文件名不能含路径分隔符

**json 模块补充**
- `json.dump(obj, f)`：Python对象 → 写入文件（不是加载）
- `json.load(f)`：从文件读取 → Python对象
- `json.dumps(obj)`：Python对象 → 字符串
- `json.loads(s)`：字符串 → Python对象
- 记忆规律：带 `s` 的操作字符串（string），不带 `s` 的操作文件
- `ensure_ascii=False`：关闭"只输出ASCII字符"限制，中文直接输出而非 `\uXXXX` 转义

**@dataclass 装饰器**
- 自动生成 `__init__`，比普通 class 少写代码
- 和 Pydantic BaseModel 区别：dataclass 更轻量，不做运行时校验，适合纯数据容器

#### 每日结束检查
- [x] 实际完成 vs 计划对齐 ✅ 全部完成
- [x] 新增：今天提前完成 Day 6，进度超前
- [x] commit 了吗？→ 待执行

#### 今日八股（0.5h）
**Tool Use vs Function Calling 对比**：
- Claude 叫 Tool Use，OpenAI 叫 Function Calling，本质一样
- 两家 API 协议差异（Claude 要 tool_use/tool_result，OpenAI 要 tool_calls）
- 并行工具调用支持情况

#### 产出
能跑真实 GitHub PR 的 end-to-end demo

#### 每日结束检查
- [ ] 实际完成 vs 计划是否对齐？（打 ✅ 或说明偏差）
- [ ] 有无新增任务或可改进项？（如有，更新到后续 Day）
- [ ] commit 了吗？

---

### ✅ Day 7 + Week 2 Day 1 (周三 4.22，提前开始 Week 2)

#### 任务
- [x] 写 README.md（英文，Mermaid 架构图 + Quick Start + Roadmap）
- [x] 清理代码、统一格式（ruff format + lint fix，10 文件格式化，4 问题修复）
- [x] 盘点 Week 2 计划（Day 1-7 详细规划已确认）
- [x] docker-compose.yml：etcd + MinIO + Milvus 三容器本地启动
- [x] 安装 pymilvus + FlagEmbedding（BGE-M3）
- [x] `examples/05_milvus_basic.py`：BGE-M3 embed → Milvus store → 相似度检索全链路跑通
- [ ] commit + push（待执行）

#### 今日收获 / 踩坑
- ruff 是 Rust 实现的 Python 格式化+lint 工具，`format` 管样式，`check --fix` 管规范
- Docker Desktop 可通过命令行启动，需轮询等待 daemon 就绪后再执行 compose
- HF_ENDPOINT 设为国内镜像时，对 `.DS_Store` 文件返回 403 导致模型下载失败，改用官方源解决
- BGE-M3 首次下载约 2GB，之后本地缓存复用

#### 今日提问记录（理解薄弱点）

**Docker Desktop 导航**
- Containers（容器）：运行中的程序实例，镜像是模具，容器是产品
- Images（镜像）：容器的只读安装包，`docker compose up` 首次自动拉取
- Volumes（数据卷）：容器外的持久化存储，容器删除后数据仍在
- Builds（构建）：`docker build` 自定义镜像的历史，本项目暂不用
- Docker Hub：官方镜像仓库，类似 PyPI
- Docker Scout：镜像 CVE（Common Vulnerabilities and Exposures，公共漏洞和暴露）安全扫描

**Milvus 三组件**
- etcd（etc distributed）：分布式键值存储，存 Collection Schema 等元数据，不存向量
- MinIO（Mini Input/Output）：对象存储，兼容 Amazon S3（Simple Storage Service）API，存向量数据文件和索引文件
- Milvus：向量数据库主进程，是真正执行相似度计算的计算引擎

**Milvus 检索流程（三阶段）**
- 冷启动：Milvus 查 etcd 获取 Schema → 从 MinIO 加载向量数据和 HNSW 索引到内存
- 查询阶段：pymilvus 通过 gRPC（Google Remote Procedure Call，谷歌远程过程调用）发送 query_vec → Milvus 在内存中执行 HNSW 相似度计算 → 返回 top-k
- 后续查询：etcd 和 MinIO 不再参与，纯内存计算

**核心概念澄清**
- etcd 的"索引" ≠ 向量索引：etcd 存的是 Collection 目录/元数据；向量索引（HNSW）是加速相似度搜索的数据结构，存在 MinIO 里
- gRPC 的"远程"：指跨进程调用，pymilvus 和 Milvus 在不同进程，看似本地调用实际是网络通信
- Schema（希腊语 σχήμα，结构/蓝图）：字段名 + 数据类型 + 约束 + 索引配置的完整定义，数据类型只是其子集
- COSINE（余弦相似度）：值域 [-1,1]，越接近 1 越相似；用点积（Dot Product）除以两向量模长（Magnitude）计算
- HNSW（Hierarchical Navigable Small World，层次可导航小世界）：图结构 ANN（Approximate Nearest Neighbor，近似最近邻）算法，搜索复杂度从 O(n) 降至约 O(log n)

**验证结果**
- 查询 f-string SQL 拼接代码 → 召回 "SQL injection vulnerability" 相似度 0.835 ✅
- 未使用关键词"injection"，纯语义匹配成功

#### 每日结束检查
- [x] 实际完成 vs 计划对齐 ✅ 提前完成 Day 7，并完成 Week 2 Day 1
- [x] 新增：Week 2 完整规划已制定（Day 1-7）
- [ ] commit 了吗？→ 待执行

---

### ✅ Week 2 Day 2 (周四 4.23)：概念复习 + 环境排查

#### 任务
- [x] 复习 Docker、Milvus、向量检索核心概念
- [x] 排查并修复 PyCharm 运行 `05_milvus_basic.py` 报错
- [x] 修复 search 返回空的 flush 问题

#### 今日收获 / 踩坑
- PyCharm 运行按钮默认工作目录是脚本所在文件夹（`examples/`），相对路径 `models/bge-m3` 找不到；用 `Path(__file__).parent.parent` 解决
- `client.insert()` 后数据落在 Growing Segment（内存缓冲区），search 有时跳过未建索引的 Growing Segment 返回空；`client.flush()` 强制刷写到 Sealed Segment 后稳定命中
- BGE-M3 一次 encode 同时输出稠密向量（`dense_vecs`）和稀疏向量（`lexical_weights`），两个并行输出头，主干 Transformer 只算一次
- `max_length=512` 是输入 token 数上限，`dimension=1024` 是输出向量维度，两者完全无关

#### 今日提问记录（理解薄弱点）

**Docker**
- Docker 是什么：容器化工具，把程序 + 依赖打包成容器，共享宿主机 OS 内核，比虚拟机轻
- 为什么用 Docker 跑 Milvus：Milvus 是 C++ 程序，依赖 etcd + MinIO + 特定系统库，Windows 无原生二进制；Docker 一行命令解决三组件协同
- 不用 Docker 的替代方案：ChromaDB（`pip install`，纯 Python）/ FAISS（Meta，纯内存）/ SQLite-vec；但简历含金量不如 Milvus

**BGE-M3 encode 参数**
- `max_length=512`：输入 token 数量截断上限，超出部分忽略；token ≠ 字符，中文约 1 token/字，代码约 0.3 token/字符
- `dimension=1024`：模型架构固定输出，和输入长度无关；无论输入几个 token，输出永远 1024 个浮点数
- `tolist()`：NumPy ndarray → Python 原生 list，Milvus SDK 不接受 NumPy 类型

**稠密向量 vs 稀疏向量**
- 稠密向量：固定长度浮点数列表，每维是抽象语义特征，模型训练出来的，人看不懂；`[0.023, -0.134, 0.891, ...]`
- 稀疏向量：字典形式，key 是词表 token ID（有明确含义），value 是该词重要性权重；`{15234: 0.82, 3301: 0.67}`
- 本质区别：稠密 = "这段代码是什么意思"（语义坐标）；稀疏 = "这段代码用了哪些词"（词频统计）
- 为何选稠密：代码审查需要语义理解，"f-string SQL拼接" 要匹配 "SQL injection"，词不同但意思同，只有稠密向量能做到
- BGE-M3 同时输出两种：`result["dense_vecs"]` / `result["lexical_weights"]`，生产级 RAG 可融合使用（混合检索 Hybrid Search）

**Milvus search 机制**
- 必须指定 collection：Milvus 实例 = 数据库，collection = 表；不同 collection schema 和维度不同，不能跨表搜索
- 多 collection 同时搜：分别 search 再手动合并排序
- flush 逻辑：insert → Growing Segment（内存缓冲，无 HNSW 索引）→ flush → Sealed Segment（持久化到 MinIO，有 HNSW 索引）→ search 稳定命中；小数据量时 Growing Segment 可能被 search 跳过，flush 是保险操作

#### 今日结束检查
- [x] 概念复习完成，理解深化
- [x] 两个 bug 修复（路径 + flush）
- [x] `src/tools/rag_store.py`：25 条种子 bug 模式 + Milvus 存取封装
- [x] `src/tools/code_chunker.py`：tree-sitter 按函数/类切 chunk
- [x] Reviewer Agent 接入 RAG，端到端验证通过
- [x] 记忆系统整理：全局 + 项目两层分工
- [x] 删除 conda env multi-agent-code-reviewer
- [ ] 代码学习环节 → 明天进行
- [ ] commit 了吗？→ 待执行

---

### ✅ Week 2 Day 3 (周五 4.24)：代码复习日

#### 任务
- [x] 逐行审阅昨天新写的 4 个文件

#### 今日收获 / 踩坑
- `chunk_diff` 已定义但全项目无调用点，属于预留函数，后续 `review_runner.py` 接 PR diff 时接入
- RAG 注入 prompt 的内容只有 `label + comment`，不含种子 `code`：种子代码的作用是辅助向量匹配，注入会让 LLM 把它和被审代码混淆
- Docker Volume 持久化规则：`down` 不删，`down -v` 才删；正常重启 Milvus 数据不丢

#### 今日提问记录（理解薄弱点）

**tree-sitter**
- 为何接受 bytes 不接受 str：tree-sitter 是 C 库，返回 `start_byte / end_byte` 字节偏移；中文等多字节字符用 str 索引会偏移错误，必须 `.encode("utf-8")` 后切 bytes 再 `.decode()`

**RAG 设计**
- query 时只用 label + comment：种子 code 只是向量匹配的依据，不适合注入 prompt（增加 token、可能混淆 LLM）
- `chunk_diff` 预留位置：用于处理 PR 原始 diff（带 +/- 前缀），当前 `reviewer_node` 传入的是纯 Python 代码，所以用 `chunk_python_code` 而非 `chunk_diff`

**LangGraph / Pydantic**
- `PlannerOutput.summary`：一句话描述代码整体功能（`str`），给 Reviewer 提供上下文背景
- `PlannerOutput.aspects`：`list[ReviewAspect]`，3-5 个具体检查点，每个含 `category + description`，拼成"评审清单"注入 prompt
- `COLLECTION = "bug_patterns"`：模块级常量，函数体内直接引用全局变量，不是函数参数；统一用常量防止拼写错误，改名只改一处

#### 今日结束检查
- [x] 4 个文件逐行审阅完成
- [x] 今日无新代码，仅学习复习
- [ ] commit 了吗？→ 仅学习日，无新代码，不需要 commit

---

### ✅ Week 2 Day 4 (周六 4.25)：FastAPI 网关

#### 任务
- [x] `src/api/main.py`：POST /review + GET /health
- [x] `review_runner.py` 返回值改为 output dict
- [x] `multi_agent.py`：chunk_diff or chunk_python_code 双模式
- [x] `pyproject.toml` 补全缺失依赖
- [x] 重建 .venv（uv python install 3.12）

#### 今日收获 / 踩坑
- 删除 conda env 导致 .venv Python 基础断裂；正确修复是只改 `pyvenv.cfg` 的 `home` 字段，不需要 `--clear` 重建（误操作，教训）
- uv 命令丢失是因为 PATH 没有包含 `~/.local/bin`，重装 uv 解决
- pyproject.toml 和 .venv 是独立的，`uv pip install` 不会自动更新 pyproject.toml，每次装新包应同步写进去

#### 今日提问记录（理解薄弱点）

**FastAPI**
- 网关含义：把内部 Python 函数暴露成 HTTP 接口，外部通过 HTTP 请求调用，不需要 Python 环境
- GET vs POST：GET 参数在 URL，用于读取；POST 参数在 body，用于提交/触发操作
- Swagger UI（`/docs`）：FastAPI 自动生成的可视化文档，可直接在浏览器发请求测试，面试演示用
- `response_model=ReviewResponse`：FastAPI 用此类校验返回数据，多余字段过滤，同时生成 Swagger 响应示例
- `def` vs `async def`：pipeline 是同步阻塞调用，用 `def` FastAPI 自动放入线程池，不阻塞主线程

**Pydantic**
- Pydantic 输出是类实例，不是 dict；用点号访问字段（`request.repo`），不支持中括号
- `model_dump()`：类实例 → Python dict
- `model_dump_json()`：类实例 → JSON 字符串
- FastAPI 看到参数类型是 Pydantic 模型，自动从请求 body 解析 JSON 并校验，类型不对返回 422 错误

**Python 语法**
- `review: ReviewResult = state["review"]`：变量类型标注，运行时无效，仅供 IDE 补全字段名使用

#### 今日结束检查
- [x] FastAPI 服务启动验证：GET /health 返回 `{"status": "ok"}` ✅
- [x] Swagger UI 可访问 ✅
- [ ] commit 了吗？→ 待执行

---

### ✅ Week 2 Day 5 (周日 4.26)：代码复习日

#### 任务
- [x] 复习 Week 2 Day 4 新写的三个文件

#### 今日结束检查
- [x] 代码复习完成
- [x] 今日无新代码
- [ ] commit 了吗？→ 待执行

---

### ✅ Week 2 Day 6 (周日 4.27)：Docker 容器化 + 代码复习

#### 任务
- [x] Dockerfile：python:3.12-slim，分层构建，EXPOSE 8000
- [x] .dockerignore：排除大文件和敏感文件
- [x] docker-compose.yml：新增 api 服务
- [x] rag_store.py：MILVUS_URI 改读环境变量
- [x] docker compose up 验证通过

#### 今日收获 / 踩坑
- Dockerfile 只负责构建单个服务的**镜像**（image），docker-compose.yml 负责多服务协作
- 镜像 vs 进程：镜像是快照（静止的），容器是运行中的进程（活的）
- Docker 层缓存：COPY 依赖文件 → RUN pip install → COPY 其余文件，依赖没变就复用缓存
- `MILVUS_URI` 用环境变量解耦：本地用 localhost，容器内用服务名 milvus，同一份代码两种环境都能跑
- torch（PyTorch）是 FlagEmbedding 的间接依赖，自动被 pip 拉进来，不是主动安装的

#### 今日提问记录（理解薄弱点）

**Docker 命令**
- `docker images`：列出本地所有镜像，任意目录可运行
- `docker ps`：列出运行中的容器，`-a` 包含已停止的
- `docker compose up/logs/config`：必须在有 docker-compose.yml 的目录运行
- `docker build -t name .`：按 Dockerfile 构建镜像，`.` 指构建上下文为当前目录
- `--format "table {{.Names}}\t{{.Ports}}"`：自定义输出列，Go 模板语法

**命令行参数**
- 单横杠 `-`：短参数，单字母简写（`-E` `-i` `-a`）
- 双横杠 `--`：长参数，完整单词（`--format` `--no-cache-dir`）
- 两种写法通常等价，长参数可读性更好适合脚本

**管道符 `|`**
- 把左边命令的输出作为右边命令的输入
- `docker images | grep -E "milvus|minio"`：只显示含 milvus 或 minio 的行
- `-E`：开启扩展正则，支持 `|` 表示"或"

**docker compose 执行顺序**
- 读 docker-compose.yml → 读 Dockerfile（build 服务）→ 读 .dockerignore → 读 .env

**Docker 镜像概念**
- 镜像 = 静止的安装包（包含系统层 + 依赖 + 代码），容器 = 运行中的进程；一个镜像可以启动多个容器
- "api 镜像"= docker-compose.yml 里名为 `api` 的服务对应的镜像，即我们自己写的 FastAPI 服务（`src/api/main.py`）打包后的结果
- 项目四个服务：etcd（元数据）/ minio（向量文件）/ milvus（搜索引擎）/ api（我们写的评审服务），前三个用官方现成镜像，api 用 Dockerfile 自己构建
- docker-compose.yml 里服务名（api / etcd 等）是自己起的，改成 backend / server 都行

#### 今日结束检查
- [x] Docker 容器化完成，四服务全部运行 ✅
- [x] 代码复习完成
- [ ] commit 了吗？→ 待执行

---

### ✅ Week 2 Day 7 (周二 4.29)：Benchmark + Token 追踪 + README 更新

#### 任务
- [x] `src/tools/token_tracker.py`：LangChain callback 跨三节点累计 token 用量和费用
- [x] `src/tools/review_runner.py`：接入 TokenUsageCallback，output 新增 token_usage 字段
- [x] `src/benchmark.py`：移入 src/，支持断点续跑，逐 PR 写盘
- [x] Benchmark 执行：23/24 PR，平均 6.2/10，总耗时 ~37 min
- [x] Docker 镜像重建：含最新 token_tracker
- [x] README 全面更新：benchmark 结果表、API 示例、完整项目结构

#### 今日提问记录（理解薄弱点）

**Pipeline / Docker / 端口**
- pipeline 是什么：数据经过多个处理阶段的流水线；这里指 Planner → Reviewer → Reporter 三节点 LangGraph 有向图，每个节点是一个 LLM 调用
- Docker 容器里包含 FastAPI 代码吗：是的，`docker compose build api` 把 `src/` 打包进镜像，容器内运行 `uvicorn src.api.main:app`
- 暴露端口的作用：`EXPOSE 8000`（Dockerfile）声明容器监听 8000；`"8000:8000"`（docker-compose）把宿主机 8000 映射到容器 8000，外部才能访问
- 目前 benchmark 测评时代码在哪跑：benchmark.py 在本地 .venv 运行，但它通过 HTTP 调用 `localhost:8000`，实际 review 逻辑（LangGraph pipeline）在 Docker 容器内执行

**uvicorn**
- uvicorn 是什么：ASGI（Asynchronous Server Gateway Interface）服务器，负责把 HTTP 请求转发给 FastAPI app；类比 gunicorn 之于 Flask
- "进入容器里的 uvicorn"：`docker exec` 可以进入容器 shell 看到 uvicorn 进程，不是指宿主机进程

**Benchmark 设计**
- 走 HTTP vs 不走 HTTP：走 HTTP = benchmark 调 Docker API，pipeline 在容器内跑，版本隔离但需要容器有最新代码；不走 HTTP = 直接 `import review_pr`，pipeline 在本地跑，用的是最新 .venv 代码，token 追踪更准确
- benchmark 为什么属于系统一部分：它是用来评测系统质量的工具，应该和 src/ 其他模块放一起方便管理和导入，而不是放 scripts/（scripts/ 一般放一次性脚本）
- 每个仓库 PR 数为什么可能少于 4：`fetch_merged_prs` 遍历最近 100 个 closed PR 找满足条件的（merged=True + 含 .py 文件），如果符合条件的不足 4 个则返回实际数量
- 100 是固定参数吗：是的，PyGithub `get_pulls()` 默认每页 30，这里没有显式限制遍历数量，实际是遍历直到找够 n 个或 API 返回结束

**LangChain Callback**
- `BaseCallbackHandler.on_llm_end`：每次 LLM 调用结束时触发，response.llm_output 含 token_usage（prompt_tokens / completion_tokens），三节点各触发一次，累加得到本次 review 总用量
- 为什么 Docker 容器旧版本 token 显示 $0：容器镜像构建于 token_tracker.py 添加之前，review_runner 里没有 callback 注入，API 返回的 token_usage 字段为空 dict

#### 今日代码复习提问记录

**@property 和装饰器**
- `@property` 是谁规定的：Python 内置类，和 `int`/`str`/`list` 地位相同，语言规范自带，不需要 import
- `@` 是什么：装饰器语法糖（Python 2.4 引入），等价于 `func = decorator(func)`，`@property` 等价于 `total_tokens = property(total_tokens)`
- `@` 后面可以跟什么：任何可调用对象——`@property`（内置）、`@app.get`（FastAPI）、`@pytest.mark.integration`（pytest）、自定义函数均可；`@` 是语法，后面的内容是独立的
- 描述符协议：`@property` 把函数包装成描述符对象（实现了 `__get__`），访问 `tracker.total_tokens` 时 Python 检测到描述符，调用 `__get__` 执行函数体，调用方无需加括号

**插件式注入**
- 什么是插件式：主体代码（三个 agent 节点）不知道也不关心 callback 的存在，只管调 LLM；LangGraph 框架在 LLM 调用结束后自动遍历 callbacks 列表触发 `on_llm_end()`，功能可独立附加不修改被监听代码
- 对比侵入式：侵入式需要改每个节点手动记录 token，插件式通过 `config={"callbacks": [tracker]}` 一次注入全覆盖
- 设计模式：观察者模式（Observer Pattern）——LangGraph 是被观察者，callback 是观察者，接口解耦

**HTTP body / Content-Type / payload**
- body 必须是 bytes vs Content-Type 是 JSON 不矛盾：bytes 是传输层的物理事实（网络只认字节流）；Content-Type 是 header 里的"货物标签"，告诉接收方这堆 bytes 按 JSON 格式解读，两者各司其职
- 发送链路：dict → `json.dumps()` → str → `.encode()` → bytes → HTTP body；header 里写 Content-Type: application/json
- payload：英语单词非缩写，原意"有效载荷"（航天/军事术语），网络编程里指请求中真正有业务含义的数据部分，不含 header、协议开销

**urllib.request.urlopen**
- `urlopen(req, timeout=180)`：发送 HTTP 请求，最多等 180 秒（LLM review 很慢）
- `with ... as resp:`：上下文管理器，确保请求结束后自动关闭连接
- `resp.read()`：读取响应 body，返回 bytes
- `json.loads(...)`：bytes → Python dict，整体作用：发 POST 请求等 LLM 跑完，把返回 JSON 解析成 dict

**Shell 通配符**
- shell 是终端里接受命令的程序（bash/zsh/PowerShell）；通配符是 shell 发明的模糊匹配符号：`*`（任意多字符）/ `?`（恰好一个字符）/ `[abc]`（括号内任一）
- `Path.glob()` 借用这套语法，由 Python 自己做展开，不经过系统 shell，跨平台

**json.dump vs json.dumps**
- 带 `s`（string）操作字符串，不带 `s`（file）操作文件；`json.dumps()` 返回字符串，`json.dump(obj, f)` 写入文件无返回值
- 对应加载：`json.loads(s)` 从字符串，`json.load(f)` 从文件

#### 今日结束检查
- [x] Benchmark 执行完成 ✅
- [x] Docker 重建完成 ✅
- [x] README 更新完成 ✅
- [x] CLAUDE.md / CLAUDE.local.md 学习记录写入 ✅
- [x] commit + push 完成 ✅

---

## 🔧 待优化项

### RAG 上下文质量：用完整函数体替代纯 diff 行
- **当前问题**：`chunk_diff` 只提取 `+` 新增行，若 PR 只改了函数内部几行，extracted code 没有 `def`，tree-sitter 找不到函数节点，fallback 成整段残缺代码送 RAG，召回精度下降
- **根本原因**：纯 diff 行缺少函数签名、类上下文，语义不完整
- **优化方案**：解析 diff 的 `@@ -10,6 +10,12 @@` 拿到行号 → 调 GitHub API 拿该文件原始内容 → tree-sitter 定位包含该行的完整函数体 → 替换当前 chunk 送 RAG
- **触发条件**：做 benchmark 时若发现 RAG 召回质量差，优先修这里
- **当前状态**：暂不做，fallback 对简历项目够用

**设计分层原则（不要合并这两个函数）**：
- `chunk_diff`：专门处理 diff 格式的"入口防火墙"，负责把任意 diff 转化为干净 Python 代码；后续所有 diff 相关优化（拉完整函数体、处理多文件、跨文件上下文）都在这里扩展
- `chunk_python_code`：只做纯 Python 代码切块，永远接收干净代码；也可单独接受完整脚本/多文件进行 review，与 diff 无关
- 两者职责不同，不能合并；`chunk_diff` 是 `chunk_python_code` 的上游预处理层

## ⚠️ 避坑提醒

1. **API Key 不要提交**：`.env` 加到 `.gitignore`，否则会被 GitHub 扫到自动 revoke
2. **不要过度优化**：本周就是跑通，不要花 2 小时调 prompt
3. **遇到问题 30 分钟没解决 → 问 Claude Code**：不要自己死磕
