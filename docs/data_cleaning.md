# Dataset Cleaning Pipeline

> 实现代码：`src/data/build_dataset.py`（各 `load_<dataset>()` 函数）
> 最后更新：2026-04-30

---

## 通用清洗原则

| 原则 | 阈值/规则 | 说明 |
|---|---|---|
| code 字段 | 丢弃 ≤ 20 字符或纯空白 | 过短无审查价值 |
| review 字段 | 丢弃 ≤ 30 字符 | 过滤 LGTM、nit、单词短评等无意义内容 |
| language 字段 | 尽量补全；无法推断且确认为非代码时丢弃 | 两种推断方式：文件头扩展名 / 代码语法特征打分 |
| 重复数据 | 以 code 字段去重，保留首次出现 | — |
| 混合内容 | 截断 `refinement:` / 代码块标记之后的内容 | 只保留纯文本审查意见 |

---

## 各数据集问题与处理

### 问题总览

| 数据集 | 主要问题 | 严重程度 | 处理方式 |
|---|---|---|---|
| Kaggle | `[KEEP]/[ADD]/[DEL]` 非标准 diff 格式 | 中 | 正则转换为 unified diff（` `/`+`/`-`） |
| Kaggle | 34% review 含 `refinement:` 后缀夹带代码 | 高 | `split("refinement:")[0]` 截断 |
| Kaggle | 28% review 为 "LGTM" 等无意义内容 | 高 | 丢弃 review ≤ 30 字符 |
| Kaggle | 35% language 标注为 `none` | 中 | 语法特征打分推断，无法推断则丢弃 |
| SeRe | 65% comment 为 JSON 多轮对话列表 | 高 | 提取 `role=="reviewer"` 的消息并拼接 |
| SeRe | 3% review ≤ 30 字符 | 中 | 丢弃 |
| CRAVE | 50% 为 APPROVE 标签（explanation 100% 合成） | 高 | 仅保留 `REQUEST_CHANGES` |
| CRAVE | 无 language 字段 | 中 | 从 `diff --git a/*.ext` 头推断 |
| CRAVE | `diff` 字段为 JSON commit hash 对象，非 diff 文本 | 中 | 使用 `patch` 字段 |
| MS CodeReviewer | 8% review ≤ 30 字符（lint 提示） | 中 | 丢弃 |
| MS CodeReviewer | `old` 字段无 diff 格式，`oldf` 为完整文件 | 低 | 优先使用 `old_hunk`（含 @@ 上下文和 +/-） |
| CodeReviewQA | 无需清洗 | — | ACL 2025 级别，人工精选标注 |
| SWE-bench Lite | 无需清洗 | — | 字段格式标准 |

### 语言推断方式

| 方式 | 适用场景 | 函数 |
|---|---|---|
| 文件扩展名推断 | diff 含 `diff --git a/file.ext` 头（SeRe/CRAVE/MS CR/SWE-bench） | `_infer_lang_from_patch()` |
| 语法特征打分 | 无文件头（Kaggle [KEEP]/[ADD]/[DEL] 格式） | `_infer_lang_from_code_content()` |

语法打分依据：Go 的 `:=`/`import "`，Python 的 `elif`/`self.`/`from x import`，Java 的 `import java.`/`@Override`，C# 的 `namespace`/`using System`，JS 的 `require(`/`module.exports`，Ruby 的 `attr_accessor`/`def self.`，PHP 的 `<?php`/`$this->`，C++ 的 `std::`/`cout <<`，C 的 `malloc(`/`int main(`。

---

## 清洗漏斗

| 步骤 | Kaggle | SeRe | CRAVE | MS CodeReviewer | CodeReviewQA | SWE-bench |
|---|---|---|---|---|---|---|
| 原始数据 | 30,000 | 6,732 | 1,174 | 50,000 | 900 | 300 |
| 去空值 | 29,998 | 6,717 | — | — | — | — |
| 去重 | 29,796 | — | — | — | — | — |
| 过滤 APPROVE | — | — | 587 | — | — | — |
| 过滤过短 code/review | 29,788 → 20,532 | — | — | — | — | — |
| 过滤短 review (≤30 chars) | — | 6,507 | — | 46,006 | — | — |
| 丢弃 unknown 语言 | 19,643 | — | — | — | — | — |
| **最终** | **19,643** | **6,507** | **587** | **46,006** | **900** | **300** |

> CodeReviewQA 和 SWE-bench Lite 无需清洗，原始即最终。
> CRAVE 去空值后无变化（587 条均有 code 和 review）。
> MS CodeReviewer 仅过滤短 review，无其他步骤。

### 各数据集最终语言分布

| 语言 | Kaggle | SeRe | CRAVE | CodeReviewQA | MS CR | SWE-bench |
|---|---|---|---|---|---|---|
| python | 4,414 | — | 182 | 100 | 9,400 | 300 |
| java | 4,172 | 1,067 | 67 | 100 | 9,464 | — |
| go | 3,663 | 1,336 | 55 | 100 | 9,301 | — |
| c# | 1,733 | 1,427 | — | 100 | 4,819 | — |
| c++ | 1,318 | 1,220 | 45 | 100 | 4,119 | — |
| javascript | 1,761 | — | 48 | 100 | 3,785 | — |
| php | 1,116 | — | — | 100 | 2,399 | — |
| ruby | 1,075 | — | — | 100 | 1,824 | — |
| c | 391 | 1,457 | — | 100 | 895 | — |
| typescript | — | — | 79 | — | — | — |
| rust | — | — | 43 | — | — | — |
| unknown/其他 | — | — | 68 | — | — | — |

> SeRe 不含 Python，但安全审查模式（缓冲区溢出、注入等）具有跨语言迁移价值。
> CRAVE 中 68 条 unknown 是 diff 只含 yml/json/md 等配置文件的 PR，正常保留。
