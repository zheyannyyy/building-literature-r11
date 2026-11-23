# 897 篇建筑文献全文筛选

本项目通过 [Codex skill](.agents/skills/building-literature-r11/SKILL.md) 按 V2.1-r11 对既有清单开展 AI 初步全文提取。Codex 阅读原文、识别参数并判断各 RQ。脚本读取批次映射、保存证据和生成 Excel。人工独立完成最终筛选。

## 开始使用

1. 在本仓库根目录用 Python 3.11 或更新版本运行 `python -m pip install -e .`。
2. 复制 `config/project.example.toml` 为 `config/project.local.toml`，填写主工作簿、已有逐篇证据和批次交付的实际路径。配置中的相对路径基于配置文件所在目录。
3. 在 Codex 中打开仓库并调用 `$building-literature-r11`，提供正式 r11 规则、现行 EX01–EX07 定义和全文资料。
4. 先运行 `r11 --config config/project.local.toml plan`，再按 [执行说明](references/workflow.md) 处理当前 10–15 篇小批。

## 项目文件

| 位置 | 内容 |
| --- | --- |
| `.agents/skills/` | Codex 全文取证和分项审查指令 |
| `references/` | r11 筛选条款、SOP 和证据字段说明 |
| `config/` | 项目路径示例 |
| `src/r11_pipeline/` | 下载、草稿、结论汇总、证据、批次和 Excel 输出模块 |
| `tests/` | 使用合成记录的自动化测试，可运行 `python -m unittest discover -s tests` |
| `data/`、`progress/`、`outputs/` | 本地目录，用于原始模板、由 Excel 派生的清单、PDF、证据 JSON 和批次交付 |

项目数据保存在本地。可直接复用旧版的证据和交付目录。中断后重新运行 `plan`，并从显示的下一篇 Record_ID 继续。
