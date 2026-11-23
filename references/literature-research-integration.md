# 可选 literature-research 与本项目的协作指南

## 当前实现状态

- 本项目已经有 `$building-literature-r11`、批次规划、证据 JSON、Excel 导出/合并代码。
- [itachwww/literature-research](https://github.com/itachwww/literature-research) 是一个**需要单独安装**的第三方 Codex Skill，具备合法获取 PDF、检查 PDF、解析文字、维护 SQLite 索引及本地证据片段检索等功能。
- 两个工具通过 PDF 和原文位置交接。Codex 逐篇核对并把证据写入 r11 JSON 草稿。当前没有 SQLite 与 r11 JSON 或 Excel 的自动同步。

## 分工

| 任务 | 主控 | 核对要求 |
| --- | --- | --- |
| 读取 897 篇的现行主 Excel 与 `03_说明` 的分工 | building-literature-r11 | 保留不连续的 Record_ID，按已有 18 批推进 |
| 获取、导入与验证合法 PDF、抽取可检索全文 | 可选 literature-research | 每篇核对 PDF 的题名和 DOI；记录来源与访问状态 |
| 读取方法、结果、讨论及必要的补充材料 | Codex 依 r11 工作流 | 不能以摘要或关键词片段替代全文；涉及数字时核对图表原页 |
| 识别 D/P-V/P-L/P-T/D-I/S、提取 n_all/n/k/r/o/o_all | building-literature-r11 | 遵守 r11 参数资格与计数规则 |
| 分别判断 RQ1、RQ2、RQ3 和整篇建议 | building-literature-r11 | RQ2 要参数—气候—定量结果—对照；RQ3 要 A/B/C |
| 保存 JSON、校验并交付 Excel | building-literature-r11 | 保留原表头、列序、人工记录和原始映射 |

本项目 897 篇的筛选集合**已经固定**。不要默认重跑第三方 `search`、`screen`、`summarize` 并将其结果当作本项目纳排意见；第三方的通用 `screen` 基于关键词，不执行 r11 全部语义细则。

## 安装

在终端安装第三方 Skill（示例为 macOS/Linux）：

```bash
git clone https://github.com/itachwww/literature-research.git ~/.codex/skills/literature-research
cd ~/.codex/skills/literature-research
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows PowerShell 可使用以下命令。

```powershell
$skillDir = Join-Path $env:USERPROFILE '.codex/skills/literature-research'
git clone https://github.com/itachwww/literature-research.git $skillDir
Set-Location $skillDir
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

打开新的 Codex 会话加载已安装的 skill。以下命令中的 `python` 指第三方虚拟环境的 Python，例如 Windows 的 `./.venv/Scripts/python.exe` 或 macOS/Linux 的 `.venv/bin/python`。需要用机构账号获取全文时，请参考上游的机构访问说明。[机构访问配置](https://github.com/itachwww/literature-research/blob/main/references/institutional_access.md)

## 配置辅助全文库

复制 [辅助配置示例](../config/literature-research.example.yaml) 为 `config/literature-research.local.yaml`。建议将 `data_root` 设为本机绝对路径，或留空使用第三方默认路径。示例的 `project` 名称为 `r11-support`。Excel、逐篇证据和批次交付仍由 `config/project.local.toml` 指定。[上游配置字段](https://github.com/itachwww/literature-research/blob/main/references/configuration.md)

在 **literature-research skill 目录**运行以下命令，将 `<PROFILE>` 替换为 `config/literature-research.local.yaml` 的绝对路径。

```bash
python scripts/lit.py doctor --profile "<PROFILE>"
python scripts/lit.py init --name r11-support --profile "<PROFILE>"
```

## 获取或导入当前小批的 PDF

先按本项目 `plan` 选出当前小批。已有 PDF 可直接核对并阅读。已有授权直链时，可在 r11 仓库使用 `r11 fetch-pdf`，命令见 [执行说明](workflow.md)。第三方库已包含本批对应题录时，也可用第三方 `fetch` 补取。该命令按第三方库的记录范围运行，调用前确认库内待下载条目对应本批。[上游下载说明](https://github.com/itachwww/literature-research#quick-start)

需要建立可检索索引时，把本次要导入的 PDF 放在一个独立目录中。上游会递归扫描目录。库里已有对应题录时，使用下方的 `import-pdfs` 命令，去掉 `--add-unmatched`，并检查未匹配清单。

新建空库时，默认导入会把 PDF 列为未匹配。若想从本地 PDF 建立索引，可先用少量已核对的 PDF 按下列示例建记录。导入后逐篇核对第三方工具推测的题名和 DOI，再建立与 Excel Record_ID 的对应。[上游导入实现](https://github.com/itachwww/literature-research/blob/72eaaed6a3d713892f405c232050a2e56c49988f/scripts/lit.py#L2715-L2814)

```bash
python scripts/lit.py import-pdfs --profile "<PROFILE>" --pdf-dir "<PDF_DIRECTORY>" --verify-pdf --add-unmatched
python scripts/lit.py audit-pdfs --profile "<PROFILE>"
```

若已有解析过的全文记录，可使用：

```bash
python scripts/lit.py ask --profile "<PROFILE>" --question "building energy sensitivity analysis" --evidence
```

该命令根据英文关键词返回局部片段。回到 PDF 原页确认页码、图表数值和适用条件。检索未命中时，仍应按 r11 流程核对正文和补充材料。[上游片段检索实现](https://github.com/itachwww/literature-research/blob/72eaaed6a3d713892f405c232050a2e56c49988f/scripts/lit.py#L5306-L5364)

## Codex 使用示例

在 `building-literature-r11` 仓库根目录打开 Codex，使用：

```text
$building-literature-r11
$literature-research

按现行 r11 规则处理当前小批。先运行 r11 --config config/project.local.toml plan，根据 03_说明 获取下一批和下一篇 Record_ID。
每次选取10–15篇：优先检查已有PDF；缺失时在授权范围内用 literature-research 辅助查找、核验和解析全文。
每篇都要核对 Excel 的题名与 DOI；按全文分别判定通用资格、RQ1、RQ2、RQ3；检查图表原页和必要补充材料。
提取合格设计输入、n_all/n/k/r/o/o_all、识别来源、气候、定量结果及其对照、RQ3 A/B/C，并保留原文页码/章节/图表位置。
来源不足则标记待核并写明缺失材料。使用本项目 r11 save 保存逐篇 JSON，小批结束后创建进度快照。不得使用第三方关键词筛选状态代替 r11 判断。
不覆盖主工作簿、历史人工判断或已经交付的批次。
```

如果第三方 Skill 尚未安装，删去 `$literature-research` 一行，仍可执行原 r11 全文处理工作流（但需自行提供 PDF 或合法可用来源）。

## 证据交接和逐篇核对

- Record_ID、题名、DOI 与 PDF 身份一致，记录出版商/仓储/本地来源。
- 在 r11 草稿的 `source`、`source_type`、`accessed_on` 和 `materials` 记录实际使用的资料。身份差异填 `identity_note`。把核实后的证据写入 `evidence`、`rq_basis` 和 `visuals`，证据缺口填 `gaps`。字段说明见 [执行说明](workflow.md#单篇-json)。
- 正文和必要补充材料可用；无法取得完整材料时保留具体待核缺口。
- 参数资格依据 r11 分类、四项识别证据、参数数量定义和独立 RQ 判断。
- RQ2 的性能数值、单位、对照与气候相互对应；RQ3 A/B/C 可定位。
- 图表数值经过 PDF 原页核查；文字片段不是最终证据。
- JSON 按本项目 `save` 登记，10–15 篇保存小批快照，按已有批次交付完整 Excel。
- 未经人工复核不得把 AI 初步判断当作 PRISMA 最终纳排。
