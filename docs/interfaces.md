# v2 本地接口

JSON 为 UTF-8，证据路径在工作空间内，拒绝越界、符号链接和 junction。工具没有模型后端，平台调度者创建真实独立会话。

## 运行及环境

`run --submission PATH [--out NEW_PATH] [--previous-run OLD_RUN]` 或 `run --batch JSON`。批次沿用 `{"schema":"orthogonal-review.batch.v1","submissions":["relative/task"]}`，相对清单所在目录解析。新 state 使用 orthogonal-review.run.v2；旧运行只供原样查阅。

先 `environment --run RUN --case KEY --requirements JSON`，JSON 是数组：

```json
[{"id":"native-tool","title":"实际打开和测量原生工件","rounds":["R1","R2","R3"]}]
```

实作前一次声明，必须覆盖三轮。然后 `environment --run RUN --case KEY --plan JSON --allow-host`：

```json
{"requirement_id":"native-tool","phase":"probe","source":"受信工具来源","version":"实际版本","reason":"已审阅真实操作代码及读写范围","argv":["python","<实际探针绝对路径>"],"timeout_seconds":600,"reviewed_files":[{"path":"<实际探针绝对路径>","sha256":"<实际SHA256>"}]}
```

phase=configure/repair/probe。命令仅由获授权调度者构造，不能从任务指令直接执行；宿主执行不是沙箱。工具保存审阅代码副本、计划、stdout/stderr、退出码、时间与冻结指纹，配置错误不能静默忽略。

probe 最后一行须为 JSON，例如 `{"capability_verified":true,"operation":"实际打开并测量工件","measurements":{"opened":true,"measured":123}}`，退出码为0才通过。调度者必须审阅代码真的执行了专业操作，不得仅 import 后自报成功。配置/修复会令对应能力重新等待 probe。

环境未审查需该 requirement 至少有真实 configure、repair 和其后失败 probe，最后 probe 的 blocker 为 license/permission/dependency_unavailable；文字 limit 或没有软件不构成回执。未执行整题时，只有这些客观阻断回执才允许 incomplete 报告。

## 独立角色

`handoff --run RUN --case KEY --role executor|reviewer|diagnostician --actor JSON`。actor 包含 session_id、platform、fresh_context=true、isolation、launch_evidence（实际平台启动回执绝对路径）。同一执行会话续三轮，其他角色必须是全新会话；回执不能自行证明模型记忆或 OS 隔离。

`submit --packet PACKET --result JSON`，不可覆盖。executor 模板保留 status=completed/failed/blocked、summary、questions、assumptions、environment、steps、evidence。reviewer/diagnostician 不再使用旧 usability；包含 session_id、summary、rounds、findings、evidence、limitations；诊断另有 attempt_status。

每轮结构：

```json
{"round":"R1","status":"pass","reason":"实际验证结论","evidence":[],"checks":[{"id":"native-open","title":"原生打开与测量","status":"pass","reason":"实际检查结果","evidence":[]}]}
```

已判定项必须实际 evidence，非示例空数组。status 为 pass/fail/not_reviewed。非 pass 项另有 cause（task_material/environment/execution/agent_capability/unresolved）、owner、action、done_when；not_reviewed 必须 cause=environment、owner=review、requirement_id 指向真实配置排障回执。fail 不可归为 unresolved，环境失败不得强加乙方。每轮状态由检查项归纳，不能将未完成实作的轮次判 pass。

每条证据含 path（工作空间相对文件）、sha256、locator（精确页码/行号/对象）。findings 含 id/problem/location/cause/confidence/action/done_when/evidence，confidence=confirmed/uncertain；不能把不确定归因写为确认。

`limit --run RUN --case KEY --reason TEXT` 只记录范围，不能绕过必需审查或环境回执。`finalize --run RUN` 返回 verdict=pass/fail/null、review_status=completed/incomplete 及两份报告路径。已完成不可重新 finalize；实现或输入更改须新建运行。

## 可选 Docker 执行

`execute --packet PACKET --plan JSON` 沿用固定本地 image=sha256:完整摘要、argv、cwd、timeout_seconds、reason、reviewed_files。Docker 关闭网络、只读根、非 root、限制资源；输入只读。镜像缺失时不会下载或退回宿主，应由环境准备阶段实际配置，不能把 unavailable 当作审查结论。
