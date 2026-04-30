# Code Review Datasets — Reference Catalog

> 构建脚本：`src/data/build_dataset.py`
> 最后更新：2026-04-30

---

## 统一 Item Schema

```json
{
  "id":       "<source>_<split>_<index>",
  "source":   "数据集名称",
  "code":     "被审代码 / diff（≤8000 字符）",
  "review":   "人工审查意见（≤2000 字符）",
  "language": "编程语言（小写）",
  "split":    "eval | rag",
  "metadata": {}
}
```

---

## 数据集总览

| # | 数据集 | 来源 | 论文 | 原始大小 | 原始条数 | 清洗后 | 主要语言 |
|---|---|---|---|---|---|---|---|
| 1 | Kaggle | kaggle.com/datasets/bulivington/code-review-data-v2 | — | 72.5 MB | 30,000 | 19,643 | Python/Java/Go/JS/C# |
| 2 | SeRe | github.com/caagc/Sere | ICSE 2026 | 272.5 MB | 6,732 | 6,507 | C/C#/Go/C++/Java |
| 3 | CRAVE | HF: TuringEnterprises/CRAVE | — | 37.5 MB | 1,174 | 587 | Python/TS/JS/Rust |
| 4 | CodeReviewQA | HF: Tomo-Melb/CodeReviewQA | ACL 2025 | 2.1 MB | 900 | 900 | 9种语言各100 |
| 5 | MS CodeReviewer | HF: fasterinnerlooper/codereviewer | FSE 2022 | 1,689 MB | 50,000* | 46,006 | Java/Go/Python/C# |
| 6 | SWE-bench Lite | HF: princeton-nlp/SWE-bench_Lite | arXiv 2310.06770 | 3.5 MB | 300 | 300 | Python |

> \* MS CodeReviewer 全量 150K，取前 50K。

### 关键字段映射

| 数据集 | code 字段 | review 字段 | language 来源 | 特殊处理 |
|---|---|---|---|---|
| Kaggle | `patch`（[KEEP]/[ADD]/[DEL] → unified diff） | `responce`（截断 `refinement:` 后缀） | `lang` + 语法推断 | reward 分存入 metadata |
| SeRe | `patch` | `comment`（多轮提取 reviewer 消息） | 原始 `language` 字段 | — |
| CRAVE | `patch` | `explanation` | 从 `diff --git a/*.ext` 推断 | 丢弃 APPROVE 条目（explanation 为合成文本） |
| CodeReviewQA | `old`（审查前代码） | `review` | `lang` 映射 | `new`（审查后代码）→ metadata |
| MS CodeReviewer | `old_hunk`（优先）→ `old` → `oldf` | `comment` | 原始 `lang` 字段 | 过滤 review ≤ 30 字符 |
| SWE-bench Lite | `patch`（fix diff） | `problem_statement` + `hints_text` | 全部 Python | — |

---

## 跨数据集语言分布

| 语言 | Kaggle | SeRe | CRAVE | CodeReviewQA | MS CR | SWE-bench | **合计** |
|---|---|---|---|---|---|---|---|
| python | 4,414 | — | 182 | 100 | 9,400 | 300 | **14,396** |
| java | 4,172 | 1,067 | 67 | 100 | 9,464 | — | **14,870** |
| go | 3,663 | 1,336 | 55 | 100 | 9,301 | — | **14,455** |
| c# | 1,733 | 1,427 | — | 100 | 4,819 | — | **8,079** |
| c++ | 1,318 | 1,220 | 45 | 100 | 4,119 | — | **6,802** |
| javascript | 1,761 | — | 48 | 100 | 3,785 | — | **5,694** |
| c | 391 | 1,457 | — | 100 | 895 | — | **2,843** |
| php | 1,116 | — | — | 100 | 2,399 | — | **3,615** |
| ruby | 1,075 | — | — | 100 | 1,824 | — | **2,999** |
| typescript | — | — | 79 | — | — | — | **79** |
| rust | — | — | 43 | — | — | — | **43** |
| 其他/unknown | — | — | 68 | — | — | — | **68** |
| **合计** | **19,643** | **6,507** | **587** | **900** | **46,006** | **300** | **73,943** |

---

## 输出文件

| 文件 | 行数 | 大小 | 说明 |
|---|---|---|---|
| `data/eval_set.jsonl` | 600 | ~1.7 MB | 评测集，每个数据集各 100 条，seed=42 |
| `data/rag_kb.jsonl` | 73,343 | ~80 MB | RAG 知识库，全部剩余条目 |
| `data/dataset_stats.json` | — | 3 KB | 完整 manifest |

重新生成：
```bash
python src/data/build_dataset.py          # N=100（默认）
python src/data/build_dataset.py --n 50   # 每个数据集取 50 条作评测
```

---

## 评估指标说明

- **BERTScore**（语义相似度）是评估 LLM 生成审查的推荐指标（SeRe 论文验证：GPT-4o ~39%，传统模型 ~22%）
- **BLEU 不适用**：审查用词多样，n-gram 匹配无区分度
- 当前 benchmark 使用 `review_score`（1-10 启发式评分），后续可引入 BERTScore
- eval 和 rag 通过 `split_and_tag()` 严格分离（seed=42），无数据泄露

---

## 调研但未使用的数据集

| 数据集 | 条数 | 放弃原因 |
|---|---|---|
| BugsInPy | 501 | review 为合成字符串（commit message），无真实人工意见 |
| SecurityEval | 121 | 太小，无 review 意见 |
| CROP | 50,959 | 2018 年数据，风格较旧 |
| Nutanix codereview-dataset | 68,572 | PostgreSQL dump，解析成本高 |
| PySecDB | — | 访问受限 |
| DiverseVul | — | C/C++ only，无 review |
| Tufano 系列（D-ACT/AUGER） | ~10K | Java only |
| SWR-Bench | 1,000 | 论文审稿中，数据未发布 |
| c-CRAB | 410 | 侧重可执行测试，场景不匹配 |
