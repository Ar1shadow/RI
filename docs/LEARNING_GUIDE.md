# RI 代码学习指南

按 IR 系统构建顺序 (对应原 LO17 TD1→TD6) 通读. 每文件标注作用、关键函数、依赖.

---

## 0. 全局基础设施 (先看, 30 分钟)

| 文件 | 作用 |
|---|---|
| `pyproject.toml` | 依赖 + entry point. `pip install -e ".[dev]"` 即装. |
| `ri/__init__.py` | 包元信息 (`__version__`). 1 行. |
| `ri/config.py` | 全局常量: `ROOT_DIR`, `DATA_DIR`, `DB_PATH`, `SPACY_MODEL`, 评分权重, BM25 参数. 看一遍知道项目布局. |
| `ri/cli.py` | argparse 入口. 4 个子命令: `scrape` / `build` / `query` / `eval`. CLI 只做路由, 无业务逻辑. 看完知道整条流水线的触发点. |

---

## TD1 — 爬取语料 (Corpus)

**目标:** HTML → `Document` 数据对象 → SQLite `documents` 表.

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/corpus/models.py` | `@dataclass Document` 定义. 9 个字段: `fichier, titre, date, auteur, rubrique, has_image, text, images, contact, bulletin`. **最先读** — 数据契约. | `Document` |
| `ri/corpus/scraper.py` | HTML 解析. 仅用 `lxml.html` (原 TD1 同时用 bs4+lxml, 已合并). 单文件解析 + 目录扫描. | `parse_html()`, `scrape_directory()` |
| `ri/corpus/xml_writer.py` | 可选 debug: 写 `corpus.xml` 供肉眼审阅. SQLite 才是正本. | `write_corpus_xml()` |

**读顺序:** `models.py` → `scraper.py::parse_html` → `scraper.py::scrape_directory` → (跳过 `xml_writer.py` 除非好奇).

---

## TD2 + TD3 — 预处理与索引 (Preprocessing + Indexing)

**目标:** Documents → 词项 → 倒排索引 + TF-IDF + 反字典, 全写入 SQLite.

### Preprocessing 层

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/preprocessing/normalize.py` | 单一来源的文本规范化: 去重音 + casefold + 折叠空白. 全项目所有"normalize" 走这里. | `normalize()`, `strip_accents()` |
| `ri/preprocessing/tokenizer.py` | spaCy fr_core_news_sm 封装. lazy load + lru_cache. 给出 `[lemma]` 或 `[(surface, lemma)]`. | `get_nlp()`, `lemmatize()`, `lemmatize_keep_text()` |
| `ri/preprocessing/antidict.py` | 反字典 (stopwords) 读写 + 过滤. 用 TF-IDF 阈值 OR 静态种子文件 (`data/anti_dict.txt`). | `select_anti_terms()`, `load_anti_dict()`, `filter_terms()` |

### Indexing 层

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/indexing/schema.sql` | **数据库结构** — 必看. 8 张表: documents, vocabulary, postings, doc_length, idf, corpus_stats, anti_dict, surface_forms. | (SQL DDL) |
| `ri/indexing/base.py` | `Index` ABC 接口. 未来可换后端 (内存/PostgreSQL). | `Index`, `Posting` |
| `ri/indexing/sqlite_index.py` | 默认实现. 所有 SQL 写在这, 参数化占位符防注入. 也是 DAO. | `SQLiteIndex`, `add_document`, `add_posting`, `add_surface_forms`, `get_postings`, `get_idf` |
| `ri/indexing/builder.py` | **端到端 build pipeline**. scrape → lemmatize → 算 df/idf/tfidf → 写 postings + idf + doc_length + corpus_stats + surface_forms + anti_dict. 一次 commit. | `build_index()` |
| `ri/indexing/ngram.py` | STUB. 未来 n-gram 索引. | `NgramIndex` |

**读顺序:** `schema.sql` (画图理解表关系) → `preprocessing/normalize.py` → `preprocessing/tokenizer.py` → `indexing/base.py` (接口) → `indexing/sqlite_index.py` (实现) → `preprocessing/antidict.py` → `indexing/builder.py` (**核心**: 看一遍 = 懂整条索引构建).

**关键公式:** `tfidf = (1 + log10(tf)) * log10(N/df)` 在 `builder.py:74-78`.

---

## TD4 — 拼写纠正 (Correction)

**目标:** 用户 query 输入前做 spell-correct + 状态诊断.

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/correction/base.py` | ABC + 4 个 dataclass: `Suggestion`, `Candidate`, `TokenAnalysis`, `CorrectionResult`. 5 种 status. **先读** — 数据契约. | `Corrector`, `Status` |
| `ri/correction/text.py` | 共享工具: tokenize (含 span 版), is_entity, common_prefix_length, levenshtein DP. | `tokenize()`, `levenshtein()` |
| `ri/correction/lexicon.py` | `SurfaceLexicon`: 归一 surface → lemma 映射 + O(1) `contains`. 从 SQLite `surface_forms` 表加载, 加 metadata 种子 (rubrique/auteur/QUERY_CONTROL_WORDS). | `SurfaceLexicon.from_index_with_metadata()` |
| `ri/correction/levenshtein.py` | 默认 corrector. TD4 忠实算法: 3 过滤 + `(distance, -prefix_len, word)` 排序. 含 spaCy fallback (surface 没见过但 lemma 在 vocab → valide). | `LevenshteinCorrector.correct()`, `_generate_candidates()`, `_pick()` |
| `ri/correction/{ngram,symspell,embedding}.py` | STUB. 未来策略. | (NotImplementedError) |

**读顺序:** `base.py` → `text.py` → `lexicon.py` → `levenshtein.py::correct → _analyze → _generate_candidates → _pick`.

**核心算法 (`_analyze`):**
1. `is_entity` → entite
2. `lemma_for(token)` 命中 → valide
3. spaCy 单字 lemma 在 vocab → valide
4. `_generate_candidates` 出候选 → corrige-*
5. 否则 → introuvable

---

## TD5 — 查询解析 (Query Parser)

**目标:** 自然语言 query → DNF AST (groups + exclusions + filters).

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/query/ast_nodes.py` | AST dataclasses: `Term`, `KeywordGroup`, `DateFilter`, `FilterSet`, `ParsedQuery`. **先读** — 知道 parser 输出什么. | `ParsedQuery` |
| `ri/query/base.py` | `QueryParser` ABC. | `QueryParser.parse()` |
| `ri/query/patterns.py` | 所有正则: 日期 (dmy/my/y + 区间)、rubrique、image、title-contains、negative-theme、theme-trigger、logical-op. **字面照搬 TD5**. | (constants) |
| `ri/query/parser.py` | 主解析逻辑. 6 步流水线. 原 TD5 三个 100+ 行函数已拆开. | `FrenchQueryParser.parse()`, `extract_global_filters()`, `split_logical()`, `build_dnf()`, `finalize_groups()` |

**读顺序:** `ast_nodes.py` → `patterns.py` (扫一眼正则) → `parser.py::FrenchQueryParser.parse` 入口, 然后跟着调用链:
```
parse()
  └─ normalize_query()              # 提取大写缩略词
  └─ extract_global_filters()       # rubrique/date/image 一次过提取
  └─ _strip_articles_prefix()       # 去掉 "les articles ..."
  └─ split_logical()                # 递归切 et/ou/sans
  └─ build_dnf()                    # 11 分支分类: title/content/exclusion
  └─ finalize_groups()              # lemmatize content, 保留 title 原形
```

**核心规则:** `ou` 开新 group, `et` 同 group 内 AND, `sans/mais pas/non pas` → exclusion.

---

## TD6 — 排序 + 检索 + 评估 (Ranking + Retrieval + Evaluation)

**目标:** ParsedQuery → 排序结果 → 评估指标.

### Ranking 层

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/ranking/base.py` | `Scorer` ABC. `score(query, index) → [(doc_id, score), ...]`. | `Scorer`, `ScoredDoc` |
| `ri/ranking/vsm.py` | **默认评分器**. 频次加权 (非 cosine, 与 TD6 行为一致): title 词项 × 3 × tf_titre; content × (3·tf_titre + 1·tf_texte). AND 同组 (集合交+求和), OR 跨组 (求和). | `VSMScorer`, `_score_group`, `_and_combine` |
| `ri/ranking/{bm25,embeddings}.py` | STUB. 未来. | (NotImplementedError) |

### Retrieval 层

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/retrieval/engine.py` | **`SearchService` — 整条搜索流程粘合**. 调 corrector → parser → scorer → 应用 filters → 减 exclusions → 排序 → 返回 docs. 也含 CLI helpers (`run_single_query`, `run_query_repl`). | `SearchService.run()`, `_docs_for_rubric`, `_docs_for_date`, `_docs_for_image`, `_docs_matching_exclusions`, `_correction_hint` |

### Evaluation 层

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `ri/evaluation/golden_set.py` | 10 条手标 query + `relevant_articles` 集合 (从 TD6 原样搬). | `GROUND_TRUTH` |
| `ri/evaluation/metrics.py` | precision / recall / F1 / timing 计算 + `run_eval()` 入口. 打印表格 + 可选 JSON 报告. | `precision_recall_f1()`, `time_query()`, `run_eval()` |
| `ri/evaluation/plot.py` | matplotlib 柱状图 (P/R/F1, 时延). 数值/绘图拆开方便测试. | `plot_metrics()` |

**读顺序:** `ranking/base.py` → `ranking/vsm.py` (盯紧 `_and_combine` + `_score_group`) → `retrieval/engine.py::SearchService.run` (**全系统主流程**) → `evaluation/golden_set.py` (理解评测对象) → `evaluation/metrics.py::run_eval`.

---

## 预留扩展 (浏览即可)

| 文件 | 作用 |
|---|---|
| `ri/compression/base.py` | STUB. `PostingCodec` ABC (gamma/vbyte 等). |
| `ri/web/app.py` | STUB. 未来 FastAPI / Streamlit. |

---

## 测试 (作为代码理解的"反向阅读")

读完每层代码, **跑一次对应测试** 验证理解:

| 测试文件 | 验证什么 | 配合哪层 |
|---|---|---|
| `tests/conftest.py` | session-scoped `built_index` fixture | 基础 |
| `tests/test_scraper.py` | parse_html 字段填充 | TD1 |
| `tests/test_preprocessing.py` | normalize / strip_accents | TD2 |
| `tests/test_indexing.py` | 326 docs, 8773 vocab, 34 anti-dict | TD3 |
| `tests/test_query_parser.py` | 5 种 query 形态 → AST | TD5 |
| `tests/test_correction.py` | 25 个 corrector 测试 | TD4 |
| `tests/test_ranking_vsm.py` | Q01 排第一名 | TD6 ranking |
| `tests/test_engine_end_to_end.py` | Q01 端到端 | TD6 retrieval |
| `tests/test_golden_set.py` | 平均 F1 ≥ 0.70 (实际 0.910) | TD6 eval |

**跑:** `source .venv/bin/activate && pytest tests/ -v`

---

## 推荐学习路径 (3 阶段)

### 阶段 1 — 跑通 + 鸟瞰 (1 小时)

```bash
source .venv/bin/activate
ri build                # 看 builder 打印的阶段输出
ri query "Je veux les articles sur l'enseignement"
ri eval                 # 看 10 条 golden 的 P/R/F1
pytest tests/ -v        # 39 testes
```

读: `cli.py` → `config.py` → `README.md`. 知道入口和数据流向.

### 阶段 2 — 数据管道 (3-4 小时, TD1+TD2+TD3)

读: `corpus/models.py` → `corpus/scraper.py` → `indexing/schema.sql` → `preprocessing/normalize.py` + `tokenizer.py` → `indexing/sqlite_index.py` → `indexing/builder.py` → `preprocessing/antidict.py`.

**自测:** `sqlite3 data/index.sqlite` 进 REPL, `SELECT term, df FROM vocabulary ORDER BY df DESC LIMIT 20;` 看高频词.

### 阶段 3 — 查询/排序/纠正 (4-5 小时, TD4+TD5+TD6)

读: `correction/{base,text,lexicon,levenshtein}.py` → `query/{ast_nodes,patterns,parser}.py` → `ranking/{base,vsm}.py` → `retrieval/engine.py` → `evaluation/{golden_set,metrics}.py`.

**自测:** 改 `ri/config.py:25-27` 三个 SCORE_WEIGHT_* 常量, 重跑 `ri eval`, 观察 F1 变化. 体会评分超参敏感度.

---

## 调试与探索建议

- **SQLite 内容查看:** VS Code "SQLite Viewer" 插件 / DBeaver / `sqlite3 data/index.sqlite`
- **看 parser 输出:** `python -c "from ri.indexing.sqlite_index import SQLiteIndex; from ri.query.parser import FrenchQueryParser; p = FrenchQueryParser(SQLiteIndex()); print(p.parse('你的 query'))"`
- **逐步调试 build:** 在 `builder.py:60` 处加 breakpoint, IDE 断点跑 `python -m ri build`
- **golden-set 排查:** `ri eval --report /tmp/report.json` 看每条 query 的 `retrieved` vs `relevant` 差集

---

## 关键设计决策 (理解为啥这么写)

1. **per-article 索引** (TD3 是 per-bulletin): 消除 bulletin→article 解析步骤, 精确率显著提升 (TD6=0.71 → RI=1.0).
2. **SQLite 替换 .txt/.pkl**: 单一存储, 原子 commit, BM25-ready (预留 doc_length/corpus_stats 列).
3. **ABC + 默认实现 + STUB 模式**: 每层 (Index/Scorer/QueryParser/Corrector/PostingCodec) 都有 ABC, 未来插拔.
4. **正则字面照搬 TD5**: 保 golden-set parity 关键. 不要"优化"正则.
5. **Corrector 在 parser 之前 + surface 保留渲染**: 只替换被 `corrige-*` 标记的 token, 其余原样输出. 否则 spaCy 处理被剥音的字符串会拿错 lemma.

---

## 一句话总览

```
HTML  →  Document  →  SQLite (vocab/postings/idf/surface_forms/anti_dict)
                          ↑
                       builder.py
                          ↓
query → corrector → parser → scorer → engine → ranked docs → metrics
```

每个 `→` 对应一个模块. 看代码就是看这条链.
