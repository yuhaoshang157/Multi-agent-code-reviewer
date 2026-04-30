# Web Sources Log

> 记录所有访问过的网站，注明访问原因和获取内容。
> 最后更新：2026-04-30

---

## 数据集获取（2026-04-29 ~ 2026-04-30）

> 目的：为 RAG 知识库搜集代码审查数据集，目标覆盖多语言、真实人工标注。

### 第一轮：初步调研

| 网站 | URL | 访问原因 | 获取内容 | 结果 |
|---|---|---|---|---|
| HuggingFace | huggingface.co/datasets/princeton-nlp/SWE-bench | 搜索 code review 数据集 | SWE-bench Lite：300 条 Python issue + fix patch | ✅ 采用 |
| HuggingFace | huggingface.co/datasets/fasterinnerlooper/codereviewer | 搜索 code review 数据集 | CodeReviewer HuggingFace 镜像，确认字段 lang/patch/msg | ✅ 采用 |
| HuggingFace | huggingface.co/datasets/s2e-lab/SecurityEval | 搜索安全代码数据集 | SecurityEval：121 条 Python CWE 漏洞代码 | ⚠️ 太小未用 |
| HuggingFace | huggingface.co/datasets/sunlab/PySecDB | 搜索 Python 安全数据 | 需申请表单 | ❌ 访问受限 |
| GitHub | github.com/soarsmu/BugsInPy | 搜索 Python bug 数据集 | 501 个真实 Python bug，diff 直接可读 | ⚠️ review 为合成文本，未用 |
| GitHub | github.com/SWE-bench/SWE-bench | 核实 SWE-bench 格式 | 官方 repo，确认数据字段 | ✅ |
| GitHub | github.com/microsoft/CodeBERT/tree/master/CodeReviewer | 查找 CodeReviewer 原始数据 | Zenodo 下载链接 | ✅ |
| GitHub | github.com/s2e-lab/SecurityEval | 核实 SecurityEval | 121 条 CWE 漏洞代码 | ⚠️ |
| GitHub | github.com/SunLab-GMU/PySecDB | 搜索 Python 安全数据 | 需申请表单 | ❌ |
| GitHub | github.com/wagner-group/diversevul | 搜索漏洞数据集 | C/C++ only | ❌ 非 Python |
| GitHub | github.com/RosaliaTufano/code_review | 搜索 Java code review | Tufano Java 数据集 | ⚠️ Java only |
| GitHub | crop-repo.github.io | 搜索 code review 数据 | CROP 数据集主页（MSR 2018） | ⚠️ 数据较旧 |
| GitHub | naist-se.github.io | 搜索 code review 工作 | NAIST 软工研究组，无独立数据集 | ⚠️ |
| GitHub | github.com/RosaliaTufano/code_review_automation | 搜索 code review 自动化 | Tufano code review 自动化 repo | ⚠️ Java only |
| arXiv | arxiv.org/pdf/2310.06770 | 了解 SWE-bench 论文 | SWE-bench 论文全文 | ✅ 参考 |
| arXiv | arxiv.org/abs/2203.09095 | 了解 CodeReviewer 论文 | Microsoft CodeReviewer 论文 | ✅ 参考 |
| arXiv | arxiv.org/pdf/2101.02518 | 了解 Tufano 方法 | Tufano 2021 Java code review 论文 | ⚠️ Java only |
| Kaggle | kaggle.com | 通用搜索 code review 数据集 | 找到 bulivington/code-review-data-v2 (30K 条) | ✅ 采用 |
| ResearchGate | researchgate.net/publication/367075263 | 了解 D-ACT 方法 | D-ACT 论文摘要 | ⚠️ Java only |
| 项目主页 | kin-y.github.io/miningReviewRepo | 搜索 Gerrit 数据 | MSR 2016，需自行 SQL 提取 | ❌ |

### 第二轮：格式/大小核实

| 网站 | URL | 访问原因 | 获取内容 | 结果 |
|---|---|---|---|---|
| HuggingFace API | huggingface.co/api/datasets/s2e-lab/SecurityEval | 核实 SecurityEval 大小 | 87.2KB，121条，字段：ID/Prompt/Insecure_code | ⚠️ |
| HuggingFace API | huggingface.co/api/datasets/fasterinnerlooper/codereviewer | 核实 CodeReviewer 大小 | 6 个子集，317K 行，3.6GB Parquet | ✅ |
| HuggingFace API | huggingface.co/api/datasets/princeton-nlp/SWE-bench_Lite | 核实 SWE-bench Lite 大小 | 300 test + 23 dev，3.66MB | ✅ |
| GitHub API | api.github.com/repos/soarsmu/BugsInPy/git/trees | 核实 BugsInPy 结构 | 501 个 bug 目录，diff 无需 checkout | ⚠️ |
| Zenodo | zenodo.org/record/6900648 | 下载 CodeReviewer 原始数据 | Quality 2.8GB + Refinement 1.2GB + Generation 847MB | ✅ |

### 第三轮：SeRe 开源 + 补充检索

| 网站 | URL | 访问原因 | 获取内容 | 结果 |
|---|---|---|---|---|
| ICSE 2026 | conf.researchr.org/details/icse-2026/.../SeRe... | 查找 SeRe 论文 | SeRe 论文主页，作者和摘要 | ✅ |
| arXiv | arxiv.org/abs/2601.01042 | 阅读 SeRe 论文 | 全文 + HTML 版（数据格式、实验） | ✅ |
| **GitHub** | **github.com/caagc/Sere** | **获取 SeRe 数据** | **完整开源：sere.jsonl + splits + 脚本** | ✅ **重要** |
| 作者主页 | jiangyanjie.github.io/index.html | 确认 SeRe 项目链接 | Yanjie Jiang 个人页 | ✅ |
| HuggingFace | huggingface.co/datasets/Tomo-Melb/CodeReviewQA | 搜索 code review QA 数据 | 900条，9语言×100，ACL 2025 | ✅ 采用 |
| HuggingFace | huggingface.co/datasets/TuringEnterprises/CRAVE | 搜索 code review 数据 | 1200条 PR，approve/reject 标签 | ✅ 采用 |
| HuggingFace | huggingface.co/datasets/Nutanix/codereview-dataset | 搜索工业 code review | 68572条，PostgreSQL dump 格式 | ⚠️ 格式复杂 |
| HuggingFace | huggingface.co/papers/2509.14856 | 了解 CR-Bench | CodeFuse-CR-Bench 论文 | ✅ 参考 |
| GitHub | github.com/awsm-research/CommentFinder | 搜索 code review 数据 | 151K changed methods | ✅ 参考 |
| GitHub | github.com/c-CRAB-Benchmark/dataset | 搜索可执行测试数据 | 410实例，Python | ✅ 参考 |
| GitLab | gitlab.com/ai-for-se-public-data/auger-fse-2022 | 搜索 Java code review | AUGER：10882条 Java | ⚠️ Java only |
| arXiv | arxiv.org/abs/2602.13377 | 了解领域全貌 | Code Review Benchmarks Survey 2015-2025（99篇综述） | ✅ 重要 |
| arXiv | arxiv.org/abs/2503.16167 | 了解 CodeReviewQA | CodeReviewQA 论文 | ✅ |
| arXiv | arxiv.org/abs/2509.14856 | 了解 CodeFuse-CR-Bench | 论文全文 | ✅ |
| arXiv HTML | arxiv.org/html/2509.01494v1 | 了解 SWR-Bench | 1000条 Python PR（审稿中） | ⚠️ 未发布 |
| arXiv HTML | arxiv.org/html/2603.23448 | 了解 c-CRAB | 论文全文 | ✅ |
| arXiv | arxiv.org/abs/2504.16310 | 搜索安全 review 数据 | 合成数据（LLM生成，非人工） | ❌ 非真实标注 |
| Zenodo | zenodo.org/record/3599150 | 下载 CROP 数据 | 50959 reviews | ⚠️ 数据较旧 |
| Zenodo | zenodo.org/records/10155869 | 搜索工业 code review | OpenStack+Qt，127182 comments | ✅ 参考 |
| Zenodo | zenodo.org/records/11546859 | 搜索 code review 复现包 | LLM code review 复现包，含 D-ACT | ✅ |
| Kaggle | kaggle.com/datasets/bulivington/code-review-data-v2 | 下载 Kaggle 数据集 | 30000条，多语言，RLHF reward | ✅ 已下载 |

### 未覆盖来源

| 来源 | 说明 |
|---|---|
| Google Dataset Search | 未专门搜索 |
| ACM DL / IEEE Xplore | 未系统检索 |
| Huawei / JetBrains 内部数据 | 未公开 |

---

## 后续访问（按需添加）

> 每次访问新网站时，在下方新增对应标题和表格行。
