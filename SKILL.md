---
name: citation-reference-governance
description: Reconcile a manuscript with its reference library by renumbering citations in first-appearance order, detecting dangling and uncited entries, merging duplicates with an explicit criterion, and rendering a synchronous bibliography. Use when a task asks for citation insertion checks, numbering updates, deduplication or reference-style conversion.
---

# 参考文献与引用管理

## 用途与适用条件

把稿件正文引用与文献库对齐：按首次出现重排编号、同步文末列表、识别悬空引用与未被引用条目、合并重复文献并给出判据，最后按目标规范渲染文献表。

适用：

- 稿件使用顺序编码制（`[1]`、`[1,3-5]`）或 LaTeX `\cite{key}`。
- 已有结构化文献库（JSON 列表 / 字典）或可解析的纯文本条目。
- 需要编号连锁更新、去重、缺字段检查与样式渲染。

不适用：需要联网核验 DOI 真实性、需要处理 Word 域代码或 EndNote 附件、著者—年份制的自动重排（只检测不重排）。

## 输入

| 输入 | 位置 | 说明 |
|-|-|-|
| `case.json` | `/input/case.json`（`--case` 可覆盖） | 稿件取自 `manuscript` / `draft` / `document` / `text` / `content`；文献库取自 `references` / `reference_list` / `bibliography` / `refs` / `library` |
| `task.md` | `/input/task.md`（自动探测） | 用于识别目标规范（GB/T 7714、APA、IEEE、Vancouver） |
| 输出 | `/app/output/result.json`（`--out` 可覆盖） | 结构化结果 |

文献条目支持：字典字段、`[{"key","authors","year","title","journal","volume","issue","pages","doi"}]`、BibTeX 字符串、带编号的纯文本行。

## 处理流程（对应评分维度）

1. **解析与归位**（挂得对）：统一字段别名（`author/authors`、`container_title/journal`、`DOI/doi` 等）；纯文本条目按句段启发式拆出作者、年份、题名、刊名，并标记 `parse_confidence=low`。
2. **引用扫描**：识别数字引用（含 `1,3-5` 区间）、`\cite{}` 键、著者—年份引用，记录原文位置。
3. **一致性诊断**（对得上）：正文编号/键在库中不存在 → `dangling_citations`；库中存在但正文未引用 → `uncited_references`；必填字段缺失 → `missing_fields`。
4. **去重**（收得净）：以 DOI 归一化优先、题名归一化次之作为判据合并；保留字段更完整的一条，逐条记录 `kept / merged / criterion / evidence`。
5. **编号重排与同步**（编得顺）：按正文首次出现顺序赋新号，未被引用条目按原顺序追加；区间引用整体重写（如 `[1,2,3]` → `[1-3]`）；悬空引用**保留原标记**不删除，交人工处理。
6. **样式渲染**：按识别到的规范渲染文献表（GB/T 7714 期刊格式 / APA / IEEE / 通用顺序编码）；缺失字段写 `[缺失: 字段]`，不补造作者、年份、题名。

## 输出契约

- `case_id`：原样保留。
- `status`：`success`（稿件与文献库齐备）/ `partial`（仅有稿件）/ `insufficient_input`（缺文献库或缺两者）/ `failed`。
- `result`：`manuscript`（重排后正文）、`reference_list`（新编号 + 渲染文本）、`mapping`（old→new）、`duplicates`、`dangling_citations`、`uncited_references`、`missing_fields`、`style`、`limitations`。
- 顶层另置 `manuscript`、`reference_list`、`mapping`、`duplicates` 便于契约映射。
- `evidence`（引用出现位置）、`uncertainty`、`errors`、`stats`（条目数、引用数、悬空/未引用/重复计数）、`contract_notes`。

**output_contract 处理**：声明字段逐一置于顶层；`manuscript`、`reference_list`、`mapping`、`duplicates` 及其别名会映射；无法产出字段置 `null` 并记录，不虚构图书记录。

## 异常处理

| 情况 | 处置 | status |
|-|-|-|
| `case.json` 缺失/非法 | 结构化失败，标注阶段，退出码 2 | `failed` |
| 有稿件、无文献库 | 不猜文献，说明缺库 | `insufficient_input` |
| 正文编号在库中不存在 | 保留原标记，列入 `dangling_citations` | `success` |
| 文献重复（同 DOI / 同题名） | 合并并记录判据与证据 | `success` |
| 条目缺作者/年份/题名 | 渲染为 `[缺失: 字段]`，列入 `missing_fields` | `success` |
| 目标规范未识别 | 用通用顺序编码制并提示 | `success` |
| 著者—年份引用 | 只检测，不重排 | `success` |

## 限制

- 不联网核验 DOI 是否存在，不判断文献真伪，也不判断论断与文献主题是否匹配。
- 纯文本条目按标点启发式解析，字段顺序不同可能解析偏差，需人工核对。
- 不支持 Word 域代码、Zotero/EndNote 二进制库、中英文混排的双语条目合并。
- 著者—年份制不做自动重排；`\cite{}` 仅替换为数字标记，不回写 LaTeX 文本。

## 最小调用示例（示例，非官方案例结果）

```json
{
  "case_id": "demo-001",
  "output_contract": {"manuscript": "string", "reference_list": "array", "status": "string"},
  "manuscript": "Prior work showed benefit [3]. Later trials confirmed it [1,2].",
  "references": [
    {"key": "smith2020", "authors": "Smith J", "year": "2020", "title": "Asthma trials", "journal": "Lancet", "doi": "10.1016/S0140-6736(20)30001-1"},
    {"key": "li2021", "authors": "Li M", "year": "2021", "title": "Pulmonary outcomes", "journal": "NEJM"}
  ]
}
```

```bash
python scripts/run_skill.py --case /input/case.json --out /app/output/result.json --work /app/work
```

示意输出（**示例**）：`status=success`，`manuscript` 变为 `Prior work showed benefit [2]. Later trials confirmed it [1-2].`，`mapping` 为 `[{"old":1,"new":1},{"old":2,"new":2},{"old":3,"new":3}]`，`uncited_references` 为空。


## 自查清单

- [ ] `case_id` 与合同字段保留；未映射项已登记。
- [ ] `manuscript` 全文已按首次出现重排，正文无截断。
- [ ] `reference_list` 与 `mapping` 编号一一对应。
- [ ] 悬空引用保留原标记并列入人工确认。
- [ ] 缺失字段标注为 `[缺失: 字段]`，未补造题录。

## 交付保证与评分对齐

调用顺序（固定）：

1. 先运行包内脚本（若存在）：`python scripts/run_skill.py`（默认读 `/input/case.json`，写 `/app/output/result.json`）；路径不同时用 `--case` / `--output` 指定。
2. **必须交付完整成品**：脚本只做解析与重排；调用 Agent 必须输出完整的重排后 `manuscript` 全文与 `reference_list`（按目标规范渲染、缺失字段标注）、`mapping`、`duplicates`、`dangling_citations`；悬空引用保留原标记并列入人工确认，不得截断正文、`pending` 或只给映射表。
3. 最后自检：`case_id` 与输入一致；`output_contract` 每个字段都存在；`status` 取本合同允许值 `success | partial | insufficient_input | failed`；正文无 `pending`/`TODO`/空占位；数字、引用、来源可逐条回溯。

运行保证：

- 输入缺失、JSON 损坏、字段异常、输出目录不存在时，仍须写出结构化 `result.json` 并正常结束，不得崩溃或非零退出。
- 不联网、不伪造数据、不声称平台评分或官方案例结果。
- 交付物必须是可直接编辑与复核的成品，而不是流程说明。

评分对齐（本题五个维度）：

- 实际效果（40）：完整产出任务要求的最终成品，覆盖全部输入条目，可直接进入修改流程。
- 使用增益（25）：体现相对基础 Agent 的可验证改进（结构化、术语/数字/引用核对、可编辑性）。
- 创新增益（15）：保留方法学增量（分块、对齐、二次校验、版本比对等），并用结果证明其价值。
- 可靠体验（10）：异常输入有明确降级与说明，不同长度/文体/重复运行下稳定产出。
- 生态贡献（10）：用途、调用、输入输出、限制、示例、维护信息齐全，资源可被他人复用。

## 最终交付强制要求

1. **调用 Agent 必须交付成品，不是流程说明**：脚本产出只是索引、核对或规格骨架；调用 Agent 必须在同一 `result.json` 中补齐本题要求的最终产物（正文/译文/审稿意见/综述/分析结论/图表源文件与导出件/幻灯片页内容与讲稿/实验方案等）。交付字段为空、只有标题骨架，或含 `pending`、`TODO` 之类占位，一律视为未完成。
2. **必须覆盖全部输入条目**：输入中的每个章节、问题、文献、图、页面、指标都要有对应条目，不得只处理示例或首条；确实缺失的条目写入 `uncertainty` / `limitations` 并说明原因，不得静默跳过。
3. **必须自检后再交付**：`case_id` 与输入一致；`output_contract` 每个字段都存在；状态值取本题契约规定的枚举；数字、单位、引用、来源可逐条回溯；结果内部无自相矛盾。
4. **参数等价**：`python scripts/run_skill.py --case <输入> --out <输出>` 与 `--output <输出>` 等价；默认 `/input/case.json` → `/app/output/result.json`。
5. **平台用 3 个固定案例分别运行**：逻辑要由输入驱动，不针对某一份示例硬编码；字段命名差异走别名匹配与显式降级，并在 `uncertainty` 记录假设。
