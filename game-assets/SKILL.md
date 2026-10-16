---
name: game-assets
description: 使用本机公共 GPT Image MCP、Tripo 直接 API 与 Blender 制作和检查游戏参考图、贴图候选及 3D 素材。适用于现有工具的素材任务与续接；不负责安装引擎、分发技能或视频制作。
---

# 游戏资产制作

工具路径针对当前 Mac；迁移后先重新配置路径与凭据引用。生产主控可直接调用这些入口，不需要由 Codex 转发。

## 开始任务

- 从用户当前任务取得已存在的绝对 `project_root`，不要把本工具安装目录当默认输出项目。选定资产用途、源图、预设与版本；已明确的信息直接采用。
- 为一次生成保存稳定的 `operation_id`。跨图片与 Tripo 共用命名约定时使用 ASCII 字母、数字、横线、下划线，最长 128 字符，首字符用字母或数字。
- 每个真实生成都应属于用户已授权的素材任务。只核查接入时用能力查询、已有任务和已有文件；不要为诊断自动付费生成、安装依赖或改客户端配置。
- 凭据由工具读取进程环境或明确的 Keychain 引用。不要把真实 key 写入提示词、参数、日志、项目文件或报告。具体入口见 [本机调用参考](references/local-tools.md)。

## 图片

**出图优先用公司素材中台**（`vast-material` skill，命令 `vmc`）：模型更多，支持透明底、图生图、批量，结果可转存公司素材库。下面的本机生图工具在中台不可用或用户点名时使用。无论用哪条路，**生成前都先问用户用哪个模型、什么参数、出几张**，不要自己决定；问法见 `vast-material` skill 的"第一步"。Tripo 生模型同样先问清贴图、PBR 等选项。

先调用 `asset_image_capabilities()` 查看当前工具限制；该调用只查本地配置，不证明供应商认证成功。实际 MCP 名称可能带客户端命名空间，以工具发现结果为准。

| 工具 | 参数与用途 |
|---|---|
| `asset_image_generate` | 必填 `project_root`、`operation_id`、`prompt`；可选 `preset`、`size`；返回 `run_id` |
| `asset_image_job` | 用原 `project_root`、`run_id` 查询本地任务，不重新生成 |

| preset | 用途 |
|---|---|
| `generic` | 通用生图，完全由调用方组织提示词 |
| `material_base_color` | Base Color 候选；不是完整 PBR 套图 |
| `prop_reference` | 道具参考图，可交给 Tripo 图生模型 |
| `ui_icon` | UI 图标候选；透明通道仍需实际检查 |

默认 `size=1024x1024` 是已实测尺寸。其他支持值与精确字段见本机参考中的 schema。

同 ID、同参数复用旧任务，不同参数会冲突。客户端断线时用原 ID/参数取回任务或查询原 `run_id`。遇到 `unknown`、`output_error` 或已提交但未明确完成的记录，停止自动提交，核对供应商历史；不换 ID 绕过去重，也不删除账本重试。

产物位于当前项目 `assets/generated/images/<run_id>/`。`saved` 仅表示保存了识别出的图片字节。当前没有图片编辑 MCP；此前编辑请求超时且结果未知，不重发它，也不承诺编辑已可用。

## Tripo 模型

按 [本机调用参考](references/local-tools.md#tripo-直接-api) 调用自有 `tools/tripo_api.py` 的 `plan` / `run` / `resume`。这是标准库直接 V3 HTTP，实现不调用第三方 Tripo CLI；当前没有 Tripo MCP 工具。

先用 `plan` 本地验证源图、参数及预计目录。源图支持 PNG/JPEG，最大 20 MiB。默认 `texture=false,pbr=false` 为裸模型；需要 Tripo 自带材质时显式选择 `texture=true,pbr=true`。只在已授权生成任务中使用 `run --execute`。

保存返回的 `task_id` 和 `operation_id`。已取得任务 ID 后，使用 `resume --execute` 查询及下载原任务；`submission_unknown` 先对账，不自动重提。下载写入当前项目 `assets/generated/models/tripo-<operation_id哈希前24位>/`；`downloaded_pending_review`、`usable=false` 表示仍需资产验收。

## 检查与 Blender 交接

先保存输入/输出路径、SHA-256、来源 run/task 和实际参数，再做检查。Grok 的 `inspect_asset.py` 是独立只读 CLI，5 项复核问题已修复，33 项离线测试及实际样例检查通过；调用及状态解释见参考。结构报告不能替代美术或 Blender 检查。

保留生成的原图、原始 GLB 和原材质。Blender 母版、渲染、优化与导出写到当前项目的独立派生目录，并记录来源。明确贴图用途、材质槽、UV 集、颜色空间；GPT 颜色图不能自动充当 normal/roughness，也不能直接认为适配了 Tripo UV。

验收按实际需要检查导入、材质绑定、图片解码、保存 `.blend`、独立进程重开、渲染、导出及空场景再导入。记录未检查的物理尺寸、拓扑、UV 接缝、目标面数、美术和引擎性能。引擎按具体项目选择，不把某个引擎设为本流程的前置条件。

交付时分开报告：文件已生成、结构已检查、Blender 已验证、目标引擎已验证。只引用本次任务证据；历史小样通过不能自动赋给新资产。
