# 快速上手

打开 `building-literature-r11` 仓库，首次填好配置。以后每次在 Codex 里发送本页的续跑指令，就从该项目的下一篇开始。

## 首次配置

准备 897 篇的原始三表工作簿、可访问的 PDF 或全文来源，以及项目现行 EX01–EX07 定义。若接手已有进度，同时找到保存逐篇 JSON 和批次 Excel 的两个目录。

在已下载的仓库根目录打开 PowerShell。用 Python 3.11 或更新版本安装依赖并创建本地配置。

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -e .
if (-not (Test-Path config/project.local.toml)) {
    Copy-Item config/project.example.toml config/project.local.toml
}
```

打开 `config/project.local.toml`，把三个路径换成实际位置。下面是写法示例。

```toml
[paths]
master = "C:/review/V2.1-r11_Full_Text_Screening_897.xlsx"
state = "C:/review/r11_evidence"
deliveries = "C:/review/AI全文预筛"
```

| 字段 | 填写内容 |
| --- | --- |
| `master` | 原始 897 篇主工作簿。批次和 Record_ID 从 `03_说明` 读取。 |
| `state` | 逐篇 JSON 目录。续跑时填已有 `batch-XX` 子目录的上一级。新项目可用配置示例中的 `../progress`。 |
| `deliveries` | 已交付批次 Excel 所在目录。续跑时填原目录；新项目可用 `../outputs`。 |

首次接手时，先查看脚本找到的批次和下一篇。若显示的进度和预期不同，先检查上面的目录。

```powershell
& ./.venv/Scripts/r11.exe --config config/project.local.toml plan
```

## 每次开始或续跑

在 Codex 中打开这个仓库。提供 PDF 目录和 EX01–EX07 定义的位置，或沿用本会话已经确认的路径。复制下面的指令。

```text
$building-literature-r11
用 config/project.local.toml 运行 plan。Windows 下使用仓库 .venv 中的 r11.exe。
从计划显示的下一篇 Record_ID 开始，只处理“小批次”里的第一组。
优先使用已有 PDF。若缺全文且已安装 literature-research，用它辅助查找和核验。
逐篇核对原文并保存证据 JSON，记录页码、图表和待核缺口。
完成小批后生成进度快照。若整批齐全，校验后生成正式批次 Excel 和待核清单。
报告已登记的 Record_ID、待核事项、输出文件路径，以及下一批、下一篇。
```

有全文时直接使用 r11。需要补全文、核验 PDF 或定位文字片段时，可按 [双 Skill 协作指南](literature-research-integration.md) 另行安装 `literature-research`。核对过的证据仍逐篇登记到 r11 JSON。

## 停止后看哪里

- `state` 目录保存已登记的逐篇 JSON。即使 Excel 导出失败，下次也可用 `plan` 找回进度。
- `deliveries` 目录保存进度快照。整批完成后生成批次 Excel 和 Markdown 待核清单。
- 已经登记为「待核」的文献进入补证清单。若本批已全部登记但还未正式导出，先完成校验和交付，再开始下一批。

证据字段及逐条命令见 [执行与数据格式](workflow.md)。
