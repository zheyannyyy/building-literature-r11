# 897 篇建筑文献全文筛选

- 处理全文筛选时，先读取 [building-literature-r11](.agents/skills/building-literature-r11/SKILL.md)。
- 以项目指定的 V2.1-r11 规则判断通用资格和各 RQ。用用户提供的主工作簿和 `03_说明` 确定 Record_ID、批次和表格结构。
- 用逐篇证据 JSON 保存 AI 初步提取及来源位置。对图表中的关键数字查看 PDF 原页。历史记录只用于定位证据。
- 使用脚本管理批次和生成副本。保留主表的人工判断、原始题录和历史试筛记录。
- Git 提交使用公开版规则、技能、脚本、示例配置和合成测试。工作簿、PDF、逐篇证据和批次交付放在已忽略的本地数据目录或仓库外。

## 可选第三方 literature-research 协作约束

- 当已安装 `$literature-research` 且本批需要 PDF 获取、完整性检查或全文检索时，按 [双 Skill 协作指南](references/literature-research-integration.md) 使用；未安装时仍按本仓库 r11 流程执行，不应将其视为必需依赖。
- 从原 Excel 的固定 897 篇清单确定工作范围。以 Excel 的 Record_ID 配对文献，用 r11 规则判断纳排。
- 对取得的 PDF 必须按 Record_ID、题名、DOI 逐篇复核映射，涉及图表的关键数字核对 PDF 原页，必要时查附录与补充材料；全文文本解析或关键词片段不足以支持 r11 的最终 AI 初步判断。
- 两个工具当前通过 PDF 和原文位置交接。使用 `r11 save` 登记逐篇证据，Excel 由本项目脚本生成。
- 无法获得决定性证据时写明待核缺口；全程保持 AI 初步建议与人工最终裁决的区别。
