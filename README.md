# 897 篇建筑文献全文筛选

本项目通过 [Codex skill](.agents/skills/building-literature-r11/SKILL.md) 按 V2.1-r11 对既有清单开展 AI 初步全文提取。Codex 阅读原文、识别参数并判断各 RQ。脚本读取批次映射、保存证据和生成 Excel。人工独立完成最终筛选。

## 开始使用

**首次使用或接手旧进度，请从 [快速上手](references/quick-start.md) 开始。** 里面有 Windows 命令、配置示例和可直接发给 Codex 的续跑指令。

先准备本地的 **897 篇主工作簿**、项目现行 **EX01–EX07 定义**和可访问的全文资料。续跑时还需要已有的逐篇 JSON 和批次工作簿。实际工作簿、PDF 和筛选结果保存在本地。

1. 在本仓库根目录用 Python 3.11 或更新版本运行 `python -m pip install -e .`。
2. 复制 [配置示例](config/project.example.toml) 为 `config/project.local.toml`。填写 `master`（主工作簿）、`state`（逐篇 JSON 目录）、`deliveries`（批次交付目录）。相对路径以配置文件所在目录为准。
3. 运行 `r11 --config config/project.local.toml plan`。查看「下一批」「下一篇」和「小批次」。已有项目续跑时，配置指向原证据和交付目录。
4. 在 Codex 中打开仓库并调用 `$building-literature-r11`，按 [r11 规则](references/r11-rules.md) 和 [执行说明](references/workflow.md) 处理计划中的第一个小批（通常 10–15 篇）。每篇保存一份 JSON，完成交付批次后生成 Excel 和待核清单。

## 双 Skill 协作（可选）

可另行安装 `literature-research`，辅助获取全文、核验 PDF 和定位文字片段。`building-literature-r11` 负责按原表批次逐篇取证、判定 RQ 和交付 Excel。[第三方 skill](https://github.com/itachwww/literature-research)

| 步骤 | 负责工具 | 结果 |
| --- | --- | --- |
| 读取主工作簿与确定 10–15 篇小批 | `building-literature-r11` | Record_ID、批次和下一篇 |
| 找到/检查 PDF、抽取文本、定位关键词片段 | 可选 `literature-research` | PDF 与辅助全文索引 |
| 回到原文阅读方法、结果、图表及必要补充材料 | Codex 按 r11 流程执行 | 可定位的证据 |
| 判定参数资格、n/k/r/o、RQ1–RQ3、整篇初步建议 | `building-literature-r11` | 单篇 JSON |
| 保存、校验并交付 Excel | `building-literature-r11` | 批次及总表副本 |

**当前通过 PDF 和原文位置交接。** 两个工具没有自动同步。Codex 根据 Excel 的 Record_ID、题名和 DOI 核对 PDF，查看原页后把证据写入 r11 JSON。第三方数据库的 ID、筛选状态和关键词命中只用于辅助查找。

完整安装、调用、PDF 导入、身份映射风险和样例指令见 **[双 Skill 协作指南](references/literature-research-integration.md)**。

## 项目文件

| 位置 | 内容 |
| --- | --- |
| `.agents/skills/` | Codex 全文取证和分项审查指令 |
| `references/` | 快速上手、r11 筛选条款、SOP、证据字段和双 Skill 协作指南 |
| `config/` | 项目路径示例与可选第三方文献库配置样例 |
| `src/r11_pipeline/` | 下载、草稿、结论汇总、证据、批次和 Excel 输出模块 |
| `tests/` | 使用合成记录的自动化测试，可运行 `python -m unittest discover -s tests` |
| `data/`、`progress/`、`outputs/` | 本地目录，用于原始模板、由 Excel 派生的清单、PDF、证据 JSON 和批次交付 |

中断后重新运行 `plan`，并从显示的下一篇 Record_ID 继续。
