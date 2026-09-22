---
name: search-hub
description: 在此 Windows 主机上复用 F 盘搜索工具，进行跨平台检索、最近几小时的信息筛选、网页原文提取和来源核验。适用于搜索 X、Reddit、YouTube、GitHub，或明确要求使用已配置的搜索工具。单纯改代码、处理已提供内容或生成 3D 资产不触发。
---

# 搜索调度

复用本机已配置的后端，不创建新的搜索服务。固定运行根目录为 `F:\搜索`。当前任务的输出目录、项目规则和用户指定的平台仍按当前任务执行；不要把搜索项目的 Tripo 背景或其他历史偏好引入无关任务。

## 入口与范围

- 先确认 `F:\搜索\scripts\search.mjs` 和 `F:\搜索\Use-SearchTools.ps1` 可读。文件或工具不可用时报告实际缺口，使用当前会话已提供的搜索能力补充；不要自动重装或迁移工具。
- 针对需要的平台参考 `F:\搜索\SEARCH-CHANNELS.md`，其中是带日期的验收记录，不是持续在线保证。简单查询不必读取整个历史清单。
- Agent Reach 提供平台操作规则：需要平台检索时读取 `C:\Users\爵士\.agents\skills\agent-reach\SKILL.md`，再按需读同目录 `references/social.md`、`dev.md` 或 `video.md`。搜索调度负责跨平台筛选，不复制或替换这些上游技能。
- 网页提取前读 `F:\搜索\.agents\skills\scrapling-official\SKILL.md`。该项目技能即使不在其他对话的初始列表里，仍可通过绝对路径读取。
- 新增依赖、浏览器、缓存、临时文件继续放在 F 盘；不要将账号 Cookie、令牌写入请求、结果或 skill。已配置的平台会话可按用户当前搜索请求只读使用；此 skill 不授权发帖、关注、点赞、私信或账号登录。

## 根据任务选择渠道

| 目标 | 方法 |
| --- | --- |
| 通用网页、新闻、官方资料发现 | 宿主原生 Web，Exa 补充；没有宿主 Web 时明确说明 |
| X / Reddit 搜索、YouTube 近期视频、GitHub 新 Issue | 下述 JSON 搜索入口 |
| GitHub 仓库、代码、PR、具体 Issue | gh，只读命令依 Agent Reach dev reference |
| X 原帖与回复 | Node 直接调用 OpenCLI `twitter thread ID --limit 5 -f json` |
| Reddit 正文与有限评论 | Node 直接调用 OpenCLI `reddit read ID --limit 5 --depth 1 --max-length 20000 -f json` |
| YouTube 字幕 | yt-dlp，具体视频 URL；失败按 video reference 重试 |
| 已知网页、批量 URL 的正文与字段 | Scrapling make_request / bulk_get；动态内容再用 fetch / bulk_fetch |

无需为普通问题强制遍历每个平台。用户要求完整渠道验收时才逐项测试。独立 CLI/网页读取可以并行；共享 OpenCLI 浏览器会话顺序调用。

## 跨项目的稳定搜索入口

将请求 JSON 写入 `F:\搜索\.runtime\tmp` 下的任务专用文件（唯一名称），以绝对路径传入，不通过 shell 字符串拼接复杂查询。脚本使用 Node 标准库，自动设置 F 盘运行环境：

```powershell
node 'F:\搜索\scripts\search.mjs' 'F:\搜索\.runtime\tmp\本次唯一请求.json'
```

请求示例（不是固定搜索主题）：

```json
{"platform":"x","query":"\"vibe coding\" OR vibecoding","hours":3,"limit":10}
```

- `platform`：`x`、`reddit`、`youtube`、`github`。`github` 仅此入口是 Issue 搜索，不是全 GitHub 搜索。
- `query` 按平台语法构造，不把 X 的 OR 或时间运算符照搬给 YouTube。
- 跨平台或多轮搜索，先固定同一个截止时间；为所有请求显式设置带时区的 `since` 和 `until`。未提供时默认该次调用开始往前 3 小时。其他时效要求按用户请求设置，不强加三小时窗口。
- `limit` 为 1–20 个候选，不是保证交付条数。该入口不做全站分页或完整历史抓取；少量候选不足时有界扩大或调整查询，必要时说明未覆盖范围。
- YouTube 按上传时间宽筛，再逐视频查精确时间；描述不算字幕，未知时间不能算窗口内视频。

输出读取：`results` 是窗口内候选；`undated` 时间未知；`outside_window` 窗口外；`rejected` 无效结果；`duplicates` 同来源重复数量。`status=ok` 只表示调用与解析成功，`partial` 要检查 warnings，`error` 与非零退出码要报告，不能当空搜索成功。

每条结果保留 URL、作者、原始和 UTC 发布时间、抓取时间、text、read_status。`body_returned` 不保证全文，`truncated` 需扩大读取或注明，`metadata_only` 和 `description_only` 不能作为已读全文证据。

## 跨项目的其他调用

仅修改工具子进程的工作目录和环境，不改当前项目的全局配置。PowerShell 子进程中用下面的工作目录模式定位 mcporter 项目配置：

```powershell
Push-Location 'F:\搜索'
try {
    . 'F:\搜索\Use-SearchTools.ps1'
    mcporter call exa.web_search_exa query='用户检索词' numResults=5
    # 已知网页例：mcporter call scrapling.make_request url=https://example.com extraction_type=markdown --output json
} finally {
    Pop-Location
}
```

Exa 当前继承该用户的 mcporter 系统配置；Scrapling 来自 F 盘项目配置。不能假定其他项目原生 MCP 已注册。确需复杂 JSON 参数时沿用 mcporter 的结构化参数机制，避免嵌套 shell 引号。

OpenCLI 的真实入口是 `C:\Users\爵士\.local\node_modules\@jackwener\opencli\dist\src\main.js`，用 `node` 加参数数组启动，避开两层 `.cmd`。新写脚本可复用 `F:\搜索\scripts\search.mjs` 导出的 `run(command,args)`；它设置 F 盘环境并且不启用 shell。简单只读详情命令在 dot-source 环境后直接调用 Node 即可。

现有 gh：`C:\Users\爵士\.local\bin\gh.exe`；yt-dlp：`C:\Users\爵士\AppData\Local\hermes\hermes-agent\venv\Scripts\yt-dlp.exe`。这些是本机位置，不承诺云端或其他电脑可用。不要调用旧 twitter-cli 作为自动认证回退，它仍有 404 和浏览器 Cookie 自动提取问题。

## 筛选与交付

- 原始发布时间、更新时间、活动时间、搜索引擎收录时间分开判断。新发布的聚合帖不代表其引用消息都是新的。
- 阅读正文后判断相关性；教程、实作、观点、推广、自荐、构想按内容标注。不要以热度代替价值，不为了凑数混入旧内容、重复或弱相关项。
- 同来源 ID/URL 由脚本保守去重；跨平台转载需人工判断，保留原始来源，不能仅以相似标题合并独立观点。
- Scrapling 必须检查响应状态、非空目标正文和验证/登录页；不要将 HTTP 200 当作访问成功。Reddit 的截断与更多评论占位行不算完整正文或已读回复。
- 给出符合当前任务需要的摘要、链接和时间；分别说明作者自述、已核实信息及推断。无法读取全文时直接说明读取程度，失败渠道只在影响结论或用户要求验收时展开。
- 保存用户要求的成果到当前任务目录。清理本次唯一命名的临时文件，保留必要证据，不删除其他任务文件或整个缓存。

高级参数、维护和回归测试见 `F:\搜索\SEARCH-QUICKSTART.md`；不需要为每次搜索重新运行安装、更新或整套回归测试。
