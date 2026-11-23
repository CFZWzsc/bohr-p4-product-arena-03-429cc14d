---
name: bohr-writing-references-citations
description: 当需要完成参考文献与引用管理并产出可复核结果时使用。本题范围：写作04｜参考文献与引用管理。题目家族：学术写作（academic-writing）。任务要求：围绕引用插入位置、编号更新、文献去重、格式转换、来源核验与正文—参考文献一致性开展整理，每条引用落到真实文献条目，编号连续且正文与文末列表同步，去重给出可解释判据；材料未报告时明确说明，不能联网补写。输出可编辑的目标产物、事实/证据映射、修改或生成记录和人工确认项；不得虚构材料外事实。产出 result.json，其中包含运行时 output_contract 要求的全部字段与 case_id，每条结论附带原文证据（段落定位 + 短引），无法从材料判断的部分如实写入 uncertainty 而非编造。
---

# 写作04｜参考文献与引用管理

## 用途

本题属于 **academic-writing / writing** 赛道，聚焦参考文献与引用管理。目标能力：从一份真实稿件与一份真实文献库出发，整理引用插入位置、编号与交叉引用、条目去重、格式与字段，并给出逐条可核验的匹配依据与改动记录。

本题重点关注四个问题：**挂得对**（引用是否插到真正需要来源支撑的那句话，而不是整段末尾或图表注附近）、**编得顺**（插入、删除、调序后正文编号与文末列表能否同步更新，编号连续、样式一致）、**收得净**（同一文献的预印本与正式版、不同数据库导出等重复形式能否合并成一条并说明依据）、**对得上**（每条引用是否真实存在、元数据准确，正文论断与所引文献是否匹配）。

本 Skill 只做确定性的文本取证与结构化整理：不联网核验 DOI、不检索数据库、不补造条目。

## 任务要求（来自题面）

本案例用于“写作 04｜参考文献与引用管理”。依据固定科研材料完成指定的引用/格式结果或结构化写作产物，保持事实和来源一致；对材料不足、冲突和需要人工确认的内容明确标注。

可选择的方向包括：引用插入与定位（识别需要来源支撑的论断句，选择引用位置与形式，处理一句多引、多句一引）；编号更新与交叉引用（插入、删除、调序后重排编号，同步正文标记、文末列表序号、图表注与附录引用）；文献去重与条目归并（处理中英文题名、预印本与正式版、期刊与会议版本、不同数据库字段差异，给出合并判据）；格式转换与字段补齐（在 BibTeX、RIS、EndNote、CNKI 导出与目标规范之间转换，保留 DOI、卷期页、文献类型标识）；来源核验与一致性检查（通过 DOI、数据库检索或原文比对核验条目真实性，检出编造条目与元数据错配，标记证据不足的句子）。

本题可预知的契约键（**实际以运行时 `/input/case.json` 为准**，下表仅供预热）：

- `case_id`
- `deliverable`
- `evidence_map`
- `change_log`
- `preserved_facts`

## 交付物

result.json（契约齐全）、可编辑稿件与同步参考文献表、evidence_map、change_log、格式与引用核对清单、材料缺口自报。

交付物的**内容契约**由运行时 `output_contract` 决定（见下）；下面「交付物落盘要求」给出的是必须真实存在的**文件**。

## 执行方式

入口脚本：`scripts/sk_entry.py`。它会读取 `/input`，产出 `/app/output/result.json`。

```bash
# 在案例环境中执行（Harbor 会自动调用；手动复现同一条命令）
python /skills/weekly-skill/scripts/sk_entry.py \
  --input /input --work /app/work --out /app/output
```

执行结束后必须存在且可解析：

- `/app/output/result.json` —— 契约字段齐全的最终结果
- `/app/output/run-review.md` —— 人类可读的证据索引与不确定性清单（复核用）

### 两阶段工作流（重要：脚本只做取证，判断由你做）

脚本是**确定性**的：它读材料、切段落、建证据索引、按契约键名填字段。它**不做**
领域判断 —— 哪几条陈述才是结论、答案该怎么组织、交付物该说什么，这些必须由你
（执行 Agent）来做。所以本 Skill 的完整用法是**跑两次**：

```bash
# 阶段 A：脚本取证，产出结果骨架 + 任务单
python /skills/weekly-skill/scripts/sk_entry.py \
  --input /input --work /app/work --out /app/output

# 阶段 B：你读 /app/work/agent_tasks.json，写 /app/work/agent_judgement.json

# 阶段 C：脚本再跑一次，把你的判断校验后合并进 result.json
python /skills/weekly-skill/scripts/sk_entry.py \
  --input /input --work /app/work --out /app/output
```

**阶段 A 之后**，`/app/work/agent_tasks.json` 会告诉你：

| 字段 | 内容 |
|---|---|
| `contract_keys` / `contract_semantics` | 本案例的契约键，以及每个键该装什么 |
| `evidence_anchors` | 全部段落 id + 原文短引（你的证据只能从这里取） |
| `draft_claims` / `open_questions` | 脚本机械抽到的候选论断与待答问题 |
| `what_to_judge` | 本题需要你判断的四件事 |
| `how_to_write_the_judgement` | 判断文件的结构与规则 |

**阶段 B** —— 有两种写法，**任选其一**：

**(a) 写判断文件**（推荐，校验最严格）—— `/app/work/agent_judgement.json`：

```json
{
  "case_id": "必须与 case.json 一致",
  "claims": [
    {"text": "你判断为结论的陈述",
     "evidence": [{"paragraph_id": "P002", "quote": "原文里逐字出现的片段"}]}
  ],
  "answers": [
    {"question": "被问的问题", "answer": "你的回答",
     "evidence": [{"paragraph_id": "P002", "quote": "原文里逐字出现的片段"}]}
  ],
  "deliverable": "本题最终交付物的正文",
  "contract_fields": {"契约键名": "该键的内容（可选，直接填契约键）"},
  "uncertainties": [
    {"kind": "machine_readable_category", "item": "具体对象",
     "detail": "客观描述", "resolution": "你做了什么或为何无法继续"}
  ]
}
```

**(b) 直接写 `/app/output/result.json`** —— 也支持，脚本会把你写进去的契约键
**取出来**（先留底，再合并），同样过引文校验。你的 `result.json` 不会被覆盖。

> 两种写法都会被采纳；**不要**两个都不做 —— 那就只剩机械抽取，`status` 停在 `partial`。

**阶段 C 的校验闸门（脚本强制执行）**：

- 每条 `quote` 必须能在材料原文里**逐字找回**（允许空白差异）—— 找不到就**退回**，
  并把退回理由写进 `uncertainty`；
- 每条 claim / answer 必须至少有一个证据锚点 —— 没有锚点的条目被退回；
- `contract_fields` 的值不能是 `null` 或空容器 —— 空值被退回；
- 被退回的条目**不会**进入最终结果，脚本保留自己的确定性抽取作为兜底。

> 判断可以自由，**证据不可以自由**。这条闸门是本 Skill 的可信度基础。

只有完成阶段 B，脚本才会把 `status` 从 `partial` 升到 `answered`；否则结果里的
`uncertainty` 会保留一条 `judgement_pending`，如实说明"只做了机械抽取，尚未判断"。

### 脚本职责

| 脚本 | 职责 |
|---|---|
| `scripts/sk_entry.py` | 入口：定位输入、发现材料、执行 `topic.run()`、装配 `result.json`、自检并写复核产物 |
| `scripts/sk_base.py` | 公共库：契约解析、材料发现、证据构造、结果装配、自检工具 |
| `scripts/topic.py` | 题目逻辑：读材料 → 建证据索引 → 按契约键名语义产出字段 → 校验并合并你的判断 |
| `scripts/specialize.py` | reading / writing 引擎：逐 `field_id` 抽取（四态状态）；可编辑稿件 + 改动记录 + 来源映射 |
| `scripts/artifacts.py` | graphics 引擎：实体—连接—步骤 IR → 分层 SVG → 渲染 PNG + 来源记录 |
| `scripts/pptxgen.py` | slides 引擎：stdlib-only 真实 PPTX + 逐页 SVG/PNG + 独立讲稿备注 |

**这些引擎会真的写文件。** 每条赛道具体落盘哪些文件、每个文件里有什么、
如何回挂到契约键，见 `references/artifact-pipeline.md`。

### 运行时契约是唯一权威

`output_contract` **只在运行时可见**（`/input/case.json`）。
不要硬编码任何字段名，也不要凭题面示例臆造字段：

1. 读取 `/input/case.json` 的 `output_contract`；
2. 对每个契约键，按**键名语义**判断它应该承载什么（证据 / 结论 / 不确定性 /
   交付物 / 覆盖度 / 变更记录 …）；
3. 产出对应内容，**不允许**留下 `null` 或"未产出"占位；
4. 若该键确实无法从材料得出，填入结构化的"无法判断"条目（带 `kind`、`item`、
   `detail`、`resolution`），而不是留空。

## 交付物落盘要求

除 `result.json` 外，**可编辑的交付物源文件与其渲染预览必须真实存在**：

| 赛道 | 必须落到 `/app/output` 的文件 |
|---|---|
| writing | `result.json`（契约齐全的结构化结果） |
| writing | `manuscript.md` —— 真实可编辑稿件，章节结构取自材料自身标题 |
| writing | `change-log.md` —— 逐条 before/after 改动记录 + 锚点守恒检查 |
| writing | `evidence-map.json` —— 章节 → 段落 / 锚点的来源映射，含**逐条锚点定位**（文件 + 行号 + 段落 id + 原文短引）与关键论断清单 |
| writing | `edit-targets.json` —— 逐条编辑目标回执（若提供 workorder） |
| writing | `qa-report.json` —— 逐节锚点守恒统计 + edit-target 状态 + 人工待核清单 |
| writing | `format-spec-checklist.json` —— 格式规格逐项核对清单：栏数 / 字号 / 行距 / 页边距 / 标题层级 / 图表题注 / 参考文献样式 / 导出格式等，附出处文件、行号与原文短引；材料未写明的记为缺失 |
| writing | `anomaly-report.json` —— 材料缺口与异常自报：格式规格缺失 / 冲突、锚点守恒异常、待人工确认项 |

平台提供的 `office-renderer` / `pdf-render-tool` / `latex-compiler` 可用来渲染预览。
**只有规格描述、没有真实文件，等于没交付** —— 评审要打开文件看。

### 导出前合规检查（pre-export compliance）

导出件落盘后，本 Skill 会**自动核对**并在 `*-export-checks.json` 里留档，
让评审不必逐个打开文件猜：

| 检查维度 | 记什么 |
|---|---|
| 目标格式 | 期望的 SVG / PNG / PDF 是否齐全、各自字节数、是否是**真矢量** |
| 画布与分辨率 | 像素尺寸 → pt → mm 换算，实测 dpi，目标 dpi |
| 字体 | 字体清单、嵌入情况、中文回退策略、是否存在方框/缺字风险 |
| 色彩空间 | 色彩空间标注（sRGB 等）与是否有嵌入配置 |
| 线宽 / 分层 | 线宽是否过细、图层是否可拆、图层清单 |
| 数据一致性 | 图上出现的数值与源数据表的比对结果 |
| 讲稿隔离 | 备注文字是否混进页面文字（逐页最大重叠片段） |
| 人工确认 | 需人眼确认的项一律标 `pending_human_review`，**不代签** |

失败的检查项会**原样保留为 fail**，不会被改写成通过；不可用的工具（如运行时
没有矢量转换器或 LibreOffice）也如实记为 `unavailable`，不做假成功。

## 质量红线

- 每条引用都要落到文献库中的具体条目，并给出正文位置与匹配依据；找不到条目的引用不静默删除
- 编号插入、删除、调序后必须保持连续，正文标记、文末列表与图表注同步
- DOI、卷期页、文献类型标识、作者与年份在整理后**逐字保持**；不编造缺失字段
- 去重合并必须给出可解释判据；同名作者的不同文献不得误合并
- 正文论断与所引文献是否匹配要逐句说明；证据不足的句子显式标注，而不是维持原引用

通用红线（违反即失分）：

- **不编造**：材料没有的数字、引用、图表、方法、结论，一律不写。写不出来就进
  `uncertainty`，并在 `status_reason` 里说明。
- **可回溯**：每条结论必须能指回原文的段落 id 与短引；引文必须是原文片段，
  不做改写、不做拼接。
- **不提前交卷**：材料可能读不全。若只读到部分文件，`status` 应为 `partial`，
  并在 `coverage.not_read` 写明未读的部分。
- **不自评**：不要在结果里写"质量良好""得分很高"这类自评语句。

## 失败与边界

| 情况 | 正确处理 |
|---|---|
| 材料是扫描件、无文本层 | 用 `scripts/sk_base.py` 的 PDF 解析；仍无文本则 `status=unsupported` 并在 `uncertainty` 写明"无文本层" |
| 材料是图片/图表 | 用平台提供的 `pdf-render-tool` / `ocr-tool`；OCR 结果标注为推断 |
| 材料格式未知 | 记录文件路径与可读性，不猜测内容 |
| 契约键无法解读 | 产出该键的结构化说明而非空值，并记录在 `uncertainty` |

详见 `references/failure-modes.md` 与 `references/evidence-discipline.md`。

## 自检

`result.json` 写完后由 `scripts/sk_entry.py` 自动自检（结构、契约覆盖、
证据完整性）。自检失败时以 `partial` 提交并在 `status_reason` 写明原因，
不要伪造 `answered`。

```bash
python /skills/weekly-skill/scripts/sk_selftest.py --input /input
```

## 参考

- `references/evidence-discipline.md` —— 证据与不确定性纪律
- `references/contract-handling.md` —— 运行时契约的读法与字段语义表
- `references/two-phase-workflow.md` —— 两阶段工作流协议与校验闸门
- `references/failure-modes.md` —— 常见失败模式与正确退路
- `references/artifact-pipeline.md` —— 每条赛道真实落盘哪些文件、怎么回挂契约键
- `assets/result-schema.md` —— `result.json` 的字段说明
- `assets/policy.json` —— 不编造承诺与来源声明
- `examples/demo-case/` —— 一个可离线复现的最小案例
