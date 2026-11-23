# 全文来源发现（候选清单，不是全文筛选）

本模块在原项目中新增一个独立命令：`python -m r11_pipeline.fulltext_discovery`。
它**只用于查找合法开放获取全文的候选网址**，不下载学校订阅PDF、不使用登录凭据、不更改既有r11 JSON、Excel或`plan`结果。OpenAlex 与可选的 Unpaywall 返回的URL必须再次核对。

## 运行方式（Windows PowerShell）

请先让本地仓库使用本分支，并确保 `pip install -e .` 已安装。继续使用原来的 `config/project.local.toml`，其中 `master` 为真实897篇Excel。以下示例先处理3篇，**不要直接处理897篇**。

```powershell
& .\.venv\Scripts\python.exe -m r11_pipeline.fulltext_discovery `
  --config config/project.local.toml `
  --ids "1,12,256" `
  --pdf-dir "C:/Users/fzzzy_/Desktop/review/r11_pdfs" `
  --output "C:/Users/fzzzy_/Desktop/review/r11_discovery/first-three.json"
```

运行后会得到同名 `first-three.json` 和 `first-three.csv`，有Record_ID、DOI、候选PDF链接、候选出版社/仓储页、错误及待核提示。报告已存在时不会覆盖。

如果有真实联系邮箱并希望增加Unpaywall结果，可添加 `--email "你的联系邮箱"`；该邮箱只用于API请求，不保存到报告文件。

按Excel的交付批次查询：

```powershell
& .\.venv\Scripts\python.exe -m r11_pipeline.fulltext_discovery `
  --config config/project.local.toml --batch 4 `
  --pdf-dir "C:/Users/fzzzy_/Desktop/review/r11_pdfs" `
  --output "C:/Users/fzzzy_/Desktop/review/r11_discovery/batch04-first20.json" --limit 20
```

也可用 `--ids-file` 传入 **每行一个整数Record_ID的文本文件**，或JSON数组如 `[1, 12, 256]`。如果现有补证队列JSON属于复杂嵌套结构，应先从中导出ID列表，不应直接假设模块已理解当前队列格式。

## 状态解释

| status | 含义 |
| --- | --- |
| `local_pdf_pending_identity_check` | 已发现对应命名的本地PDF且结构头尾基本正常，但未核实论文身份、正文和附录 |
| `oa_candidate_pending_verification` | API找到可能的开放获取全文链接，尚未访问验证 |
| `manual_access_needed` | 无候选全文，或API失败，需人工/学校授权渠道补证 |

**上述状态均不等于“已完成全文初筛”。** 完成r11判断必须依据正文及必要原页证据，并由既有r11证据流程保存。OpenAlex/Unpaywall结果可能存在过时链接、仓储作者稿、不同版本或题录差异；由人员或后续可信过程核验。

## ChatGPT 与 Codex 分工

1. 可以在 ChatGPT / Work 中根据候选CSV逐篇判断优先获取渠道，必要时由用户亲自登录学校NUsearch。
2. 把确认可用的PDF保存到本地 `r11_pdfs/0012.pdf` 等位置，避免把有版权限制的全文提交到公开GitHub。
3. 原有Codex `$building-literature-r11` 只读取核对过的PDF，执行正式r11全文取证、RQ1–RQ3初步判断和Excel导出。
4. 对未取得全文的条目继续标记“待核”，不能因为HTTP 403、摘要或仅有网页片段作出纳排结论。
5. 保留既有独立补证队列；本模块不改写其状态，也不把访问成功等同于筛选完成。

## 范围与限制

- 默认最多20篇，防止无意间大量请求；每个API请求之间默认间隔0.5秒，HTTP 403/429等不在同一次任务中自动重复。
- `--batch` 按主Excel的 `03_说明` 映射取ID；不是现有“补证队列”。
- 依据本地文件名识别 `0012.pdf`、`Record_ID_12.pdf`、`12.pdf` 等候选PDF；只检查PDF文件头尾，不读取身份和实际内容。
- DOI规范化仅清理网址前缀，不自动合并可能有误的DOI，例如 `IMECE201550999` 和 `IMECE2015-50999`；若来源出现不同DOI，报告提示人工确认。
- 模块没有下载功能；候选链接合法性、机构访问许可和是否有权自动下载仍须另行核实。
- 现有 `plan` 对“待核已登记”的逻辑未改变；这个问题需要独立维护队列或后续兼容性改造。
