# 执行与数据格式

## 输入和续跑

用 Python 3.11 或更新版本安装项目后运行。脚本用 openpyxl 读取和核对原表，通过局部更新 OOXML 保留项目模板的 Excel 表、筛选、颜色、冻结窗格和下拉验证。使用项目提供的三表 897 篇模板。

```powershell
$scriptDir = ".agents/skills/building-literature-r11/scripts"
$projectArgs = @("--config", "config/project.local.toml")
r11 @projectArgs plan
python "$scriptDir/extract_paper.py" @projectArgs
r11 @projectArgs save "<已填写的单篇草稿.json>"
python "$scriptDir/update_excel.py" @projectArgs export --batch 4 --snapshot
python "$scriptDir/validate_batch.py" @projectArgs --batch 4
python "$scriptDir/update_excel.py" @projectArgs export --batch 4
python "$scriptDir/update_excel.py" @projectArgs merge --through 4 --output "<新的汇总表.xlsx>"
```

以上是从仓库根目录调用的 PowerShell 示例。替换路径，第 4 批换成计划中显示的批次。`extract_paper.py` 将当前下一篇草稿打印为 JSON，核对全文后填写证据字段并另存为 UTF-8 JSON，再用 `save` 登记。`validate_batch.py` 可检查未交付批次的逐篇 JSON，也可核对已交付工作簿。

用 `r11 @projectArgs manifest` 可导出从 `03_说明` 派生的 ID 和批次映射，按需保存到本地 `data/manifests/`。主工作簿是批次依据。用 `r11 fetch-pdf "<授权访问的 HTTPS 直链>" --output "data/pdfs/<Record_ID>.pdf"` 可保存全文和获取文件哈希。脚本检查 PDF 文件头与文件尾。登记前还需打开原文核对身份、可读性和必要补充材料。

建议将 `--state` 放在项目 `AI全文预筛/r11_evidence`，`--deliveries` 指向实际批次文件所在目录。计划从第一批开始核对连续交付，即使总表已填也以实际交付文件复核进度。已交付批次按原副本保留，旧批次仍可用于合并。升级前只有旧进度文件时，先与旧证据和现有工作簿核对，再逐篇迁入 JSON，仅迁入当时实际核查过的内容。若原页查验未留下记录，将相关复核缺口保留；旧批次交付文件不需要因此重做。

小批次按实际篇数均分。可在单篇完成时立即保存，之后再生成小批快照。快照的 01/02/03 保留本批完整映射，未处理行显示待筛选。已经命名的独立批次文件和旧总表均作为源文件使用。中断后运行 `plan` 查看下一篇；已有待核记录也算已登记，缺口进入人工核查清单。

## 单篇 JSON

UTF-8。一个 Record_ID 对应一份 JSON。先编写草稿，通过 `save` 校验并写入进度目录。以下是字段说明，值均应来自实际处理。状态只能为符合、不符合、待核。

| 字段 | 值 |
|---|---|
| id, batch, title, doi | 依照计划保留原题录，DOI 缺失填 null |
| version | V2.1-r11 |
| access | complete、partial 或 unavailable |
| source, source_type, accessed_on, materials | 来源链接或本地文件名、版本、访问日期 YYYY-MM-DD、实际核查材料和附录 |
| identity_note | 原表与全文来源的差异，可选 |
| general, general_basis, exclusion | 通用资格状态及证据。general 为不符合时给出 EX01–EX07，其余填 null |
| rq | 长度 3 的状态数组，按 RQ1–RQ3 |
| rq_basis | 长度 3 的证据说明数组，逐项记录原文位置与理由。明确通用排除后未继续审查的 RQ 应在此注明 |
| gaps | 缺口字符串数组。材料不完整或有待核状态时至少一项 |
| review | 其他人工重点复核事项，可选字符串数组 |
| evidence | 参数证据对象，按下表字段逐项填写 |
| visuals | 涉及的图表核对记录数组。没有依赖图表的决策或数值时数组可为空 |

`evidence` 对应 `02_参数证据` 的列。B列 `short` 可省略，默认原题名；Z列由脚本写入来源、通用资格、RQ 依据、核对记录和缺口。列出的其余字段都要显式赋值。数字用 JSON 数字，分分析计数时带分析名分别记录。仅有局部材料时已核实字段仍可填写。

| 列 | 字段 |
|---|---|
| B | short |
| E–K | params, method, key, n_all, n, k, r |
| M–Q | identification, climate, quantitative, comparator, coverage |
| S–Y | a, b, optimizer, energy, comfort, o, o_all |

RQ2 有多条定量结果时，在 `quantitative` 分行记录，每行包含原文位置、参数或组、案例或气候、指标、数值或变化量、单位及适用的对照。M–Q 各列可用相同的案例或结果编号保持对应。按规则 §7.2 记录能耗和舒适类型及是否配对。对照确实不适用时，填 `NA` 并写明原因。RQ3 的 `a`、`b`、`energy`、`comfort` 均附证据位置，`b` 写清 A 的哪项识别结论怎样影响求优设置。

## PDF 原页证据

`visuals` 每项填写 `locator`（如 PDF p. 9 / 印刷页 183 / Fig. 6a）、`fields`（此图表支持的 evidence 字段或 RQ 名）、`status`（checked 或 pending）、`detail`（核对数值、行列/坐标轴、单位、图例和对应方案，或具体缺口）。已核对时再填 `view`（原页截图路径或可直接定位至原页的链接/本地文件及页码）。估读结果写明是估读，必要时记录区间。原始页与 OCR 读数不一致时回到原页。

专门检查：合并表头与单位倍率、对数轴和双纵轴、图例系列、上下标和负号、不同气候或样本、条形图参考基线。只有补充材料中的图表才能确定数值时，也要核对对应补充原页。任何待核图表涉及的决定性数值应在 evidence 中填待核，相关 RQ 依该证据是否决定判断记待核。能由正文独立支持的结果可以引用正文，记清证据位置。脚本校验结构和记录是否齐备，阅页真实性与取证结论由执行者核对。

## 已交付文件

完整批次文件名为 `V2.1-r11_AI初步提取_第XX批_N篇.xlsx`。脚本保留三表列序、人工字段、原分组和试筛记录。新结果写到 01 和 02，03 更新 D/E/O 的全文来源及访问记录。03 的 G:I 原始 AI 历史记录保留，当前结果可在 01 和 02 中查阅。合并旧批次时延用同一口径。最终统计和待核清单与工作簿一起输出。独立核对原文证据后再发布。连续批次项由 03 的交付批次字段推导。
