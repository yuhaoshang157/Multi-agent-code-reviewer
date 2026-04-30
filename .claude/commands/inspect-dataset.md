对 `data/raw/` 中指定数据集执行系统性质量检查，并在 `src/data/build_dataset.py` 中实现对应的清洗逻辑。

用法：`/inspect-dataset <数据集名>`
示例：`/inspect-dataset sere`

参数：$ARGUMENTS

---

## Phase 1 — 自动检查（直接运行代码，不要询问）

读取 `data/raw/$ARGUMENTS.jsonl`（若不存在则尝试 `.csv`），依次执行：

**1.1 基础概览**
```python
# 打印：总行数、所有字段名、每字段空值数、前3条原始记录
```

**1.2 code 字段**
```python
# 长度分布（describe）
# 过短条目数（< 20 字符）+ 样本
# 重复条目数（以 code 字段去重）
# 格式检测：
#   - 含 "diff --git a/" → 标准 unified diff，可用 _infer_lang_from_patch()
#   - 含 "[ADD]/[DEL]/[KEEP]" → Kaggle 非标准格式，需转换
#   - 均不含 → 纯代码，无 diff 格式
```

**1.3 review 字段**
```python
# 长度分布
# 无意义内容（长度 ≤ 30 字符）数量 + 高频样本
# 混合内容检测：含 "refinement:" / 含代码块标记（```）的条目数
# 随机抽取 8 条样本，展示 code 前200字符 + review 前150字符
```

**1.4 language 字段**
```python
# 若字段存在：值分布（value_counts）+ 缺失数
# 若字段不存在：尝试从 code 字段用 _infer_lang_from_patch() 推断，展示分布
# 对 unknown/缺失条目抽取 5 条，判断是否为真实代码
```

---

## Phase 2 — 问题诊断

根据 Phase 1 结果，对照以下清单逐条判断并标注 ✅ / ⚠️ / ❌：

| 检查项 | 判断标准 | 清洗优先级 |
|---|---|---|
| code 过短 | 有条目 < 20 字符 | 必须过滤 |
| code 重复 | 重复数 > 0 | 必须去重 |
| code 格式非标准 | 含 [ADD]/[DEL] | 必须转换 |
| review 无意义 | 大量 ≤ 30 字符 | 必须过滤 |
| review 混入代码 | 含 refinement: 或代码块 | 必须截断 |
| language 缺失 | unknown > 10% | 建议推断补全 |
| language 不可推断 | 推断后仍有大量 unknown | 若为非代码则删除 |

---

## Phase 3 — 清洗实现

根据诊断结果，在 `src/data/build_dataset.py` 对应的 `load_<dataset>()` 函数中实现清洗逻辑，遵循以下顺序：

```python
def load_<dataset>() -> list[dict]:
    # 1. 加载原始文件
    # 2. dropna(subset=["code字段", "review字段"])
    # 3. drop_duplicates(subset=["code字段"])
    # 4. 格式转换（如需要）
    # 5. review 清洗（截断混合内容）
    # 6. 过滤过短 code / review
    # 7. language 推断（lang=unknown 时调用 _infer_lang_from_code_content()）
    # 8. 丢弃仍为 unknown 的条目
    # 9. make_item() 构建统一 schema
```

可复用的已有工具函数：
- `_infer_lang_from_patch(patch)` — 从 `diff --git a/file.ext` 头推断语言
- `_infer_lang_from_code_content(code)` — 从代码语法特征推断语言（无文件头时）
- `_kaggle_normalize_patch(patch)` — `[KEEP]/[ADD]/[DEL]` → unified diff（其他数据集若有类似格式可参考）
- `_kaggle_clean_review(review)` — 截断 `refinement:` 后缀（可参考实现类似逻辑）

---

## Phase 4 — 验证 & 记录

**验证**：运行清洗后的 `load_<dataset>()` 函数，打印：
- 清洗漏斗（每步过滤后的条数）
- 最终语言分布
- 抽取 3 条最终条目确认 code / review 字段质量

**记录**：在 `docs/data_cleaning.md` 中为该数据集补充：
- 发现的问题列表（同 Kaggle 格式）
- 每步清洗的理由
- 清洗漏斗数字
- 最终语言分布

---

## 参考

- Kaggle 完整清洗案例：`docs/data_cleaning.md`
- 数据集字段说明：`docs/datasets.md`
- 所有工具函数：`src/data/build_dataset.py` 第 100-260 行
