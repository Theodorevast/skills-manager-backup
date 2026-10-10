# 本机调用参考

路径及验收快照日期：2026-10-10。下列安装根为 `/Users/wenbin/Desktop/游戏产线配置`，不是调用方的默认项目根。路径不存在时先定位或重新配置，不自动下载软件、全局安装技能或重写客户端设置。

## 图片 MCP

现有注册启动入口：

```text
command: /Users/wenbin/Desktop/游戏产线配置/tools/asset-pipeline/.venv/bin/python
args: ["/Users/wenbin/Desktop/游戏产线配置/tools/asset-pipeline/server.py"]
ASSET_LUMINA_KEYCHAIN_SERVICE=game-assets.lumina
ASSET_LUMINA_KEYCHAIN_ACCOUNT=default
```

服务优先读取已存在的 `LUMINA_API_KEY`，否则读取上述两个明确引用。不要打印环境值或 `security` 的凭据输出。

调用参数示例，其中项目路径和操作标识应替换为本次已确定的值：

```json
{
  "project_root": "/当前项目的绝对路径",
  "operation_id": "blue-metal-v1",
  "prompt": "蓝色喷漆金属，轻微磨损，均匀照明",
  "preset": "material_base_color",
  "size": "1024x1024"
}
```

返回的 `run_id` 用于 `asset_image_job`。任务去重依赖项目内 `.asset-jobs.sqlite3`；旧图片 CLI 是另一提交边界，不作为 MCP 超时后的自动备选入口。

精确契约与限制：

- [MCP README](/Users/wenbin/Desktop/游戏产线配置/tools/asset-pipeline/README.md)
- [工具 schema](/Users/wenbin/Desktop/游戏产线配置/tools/asset-pipeline/tool-schemas.json)

当前配置启动的 stdio 协议与真实小样已验证；各客户端实际 agent/UI 的工具发现、调用及预览仍需分别确认，不把“已注册”写成“所有界面可用”。纯本地无付费协议诊断：

```bash
'/Users/wenbin/Desktop/游戏产线配置/tools/asset-pipeline/.venv/bin/python' \
  '/Users/wenbin/Desktop/游戏产线配置/tools/asset-pipeline/diagnose.py'
```

## Tripo 直接 API

以下示例的 `asset_project` 和 `asset_source` 必须来自本次任务；不将安装路径填成输出根。先规划，不读取 key、不联网、不创建资产目录：

```bash
asset_project='/当前项目的绝对路径'
asset_source='/参考图的绝对路径.png'
asset_operation='toolbox-v1'
python3 '/Users/wenbin/Desktop/游戏产线配置/tools/tripo_api.py' plan \
  --project "$asset_project" --image "$asset_source" \
  --model v3.1-20260211 --operation-id "$asset_operation" \
  --params '{"texture":true,"pbr":true}'
```

确认这些变量、源图与参数仍为同一任务后，真实提交使用相同参数：

```bash
ASSET_TRIPO_KEYCHAIN_SERVICE='game-assets.tripo' \
ASSET_TRIPO_KEYCHAIN_ACCOUNT='default' \
python3 '/Users/wenbin/Desktop/游戏产线配置/tools/tripo_api.py' run \
  --project "$asset_project" --image "$asset_source" \
  --model v3.1-20260211 --operation-id "$asset_operation" \
  --params '{"texture":true,"pbr":true}' --execute --wait-seconds 0
```

`--wait-seconds 0` 仍允许首次付费提交，只把后续查询等待限制为一次。这里的两个环境变量仅为 Keychain 条目引用；已有 `TRIPO_API_KEY` 环境值的优先级更高。

续接已有操作无需再次指定图片或模型。一次查询示例：

```bash
ASSET_TRIPO_KEYCHAIN_SERVICE='game-assets.tripo' \
ASSET_TRIPO_KEYCHAIN_ACCOUNT='default' \
python3 '/Users/wenbin/Desktop/游戏产线配置/tools/tripo_api.py' resume \
  --project "$asset_project" --operation-id "$asset_operation" \
  --execute --wait-seconds 0
```

`submitted` / `waiting` / `query_error` / `download_error` 且有已保存任务 ID，可续接原任务；`submitting` / `submission_unknown` 不重发生成；`failed` / `cancelled` / `banned` / `expired` 是服务端终态。不要给付费创建请求套通用重试循环。进程退出码 0 也不代表模型已下载，必须读取 JSON 的 `status`、`task_id` 与文件结果。

参数、模型版本和完整状态机见 [Tripo 实现说明](/Users/wenbin/Desktop/游戏产线配置/docs/tripo-api-implementation-notes.md)。命令中的版本是当前已列支持的实例，不承诺以后仍为最佳模型。

## Grok 只读 QA

检查器已完成复核修复，33 项离线测试与本次四份样例检查通过；使用前读 [当前 QA README](/Users/wenbin/Desktop/游戏产线配置/grok-deliverables/asset-qa/README.md) 和主交接状态。报告选新的项目内路径，不能等于源资产或生成记录：

```bash
python3 '/Users/wenbin/Desktop/游戏产线配置/grok-deliverables/asset-qa/inspect_asset.py' \
  --input '/当前项目/资产的绝对路径.glb' \
  --report '/当前项目/新的qa报告.json'
```

退出码 `0` 仍可能是 `warning`，需读 `warnings` / `not_checked`；`1` 为资产结构问题；`2` 为调用或环境问题。不得以这些错误为理由自动重新计费生成。报告 `schema_version` 为字符串 `"1.0"`，与图片任务的整数 `1` 区分。一般保留旧报告，只有明确要替换同一报告时使用 `--overwrite-report`。

## Blender

本机命令为 `/Applications/Blender.app/Contents/MacOS/Blender`，验收版本 5.2.0 LTS。现有两个 probe 只读源文件，并创建独立派生目录；**输出固定在配置工作区的 artifacts 中**，不是任意当前项目的通用制作命令：

```bash
python3 '/Users/wenbin/Desktop/游戏产线配置/artifacts/blender-material-probe/run_probe.py' \
  --image '/待检查base-color的绝对路径.png'
python3 '/Users/wenbin/Desktop/游戏产线配置/artifacts/blender-material-probe/tripo-original/run_tripo_probe.py' \
  --source '/待检查原始model的绝对路径.glb'
```

仅在需要复现本机互通验收时运行这些 probe。日常制作应在当前项目中准备 Blender 脚本和派生输出路径；不要默默使用固定 artifacts 目录作为项目资产交付。原材质 probe 会把最长边归一化到 2 米用于预览，不代表已确认物理尺寸。

已有证据可直接阅读，无需再付费生成：

- [Base Color 样例报告](/Users/wenbin/Desktop/游戏产线配置/artifacts/blender-material-probe/README.md)：平面与球体绑定、保存重开、渲染与 GLB 再导入通过；roughness/metallic 为常量。
- [Tripo 原材质样例报告](/Users/wenbin/Desktop/游戏产线配置/artifacts/blender-material-probe/tripo-original/README.md)：1 个网格、8,628 三角面、1 套 UV、3 张 2048×2048 Color/ORM/NormalGL；保存重开及派生 GLB 再导入通过。再导入顶点数有变化，物理尺寸、拓扑、美术和引擎尚未验收。

两份样例分别验证 GPT Base Color 与 Tripo 原材质。它们没有验证 GPT 图已贴到 Tripo 网格，也不证明无缝或最终生产 PBR。
