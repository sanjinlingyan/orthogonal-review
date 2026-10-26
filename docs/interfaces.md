# 本地接口

所有 JSON 使用 UTF-8。路径参数支持平台原生路径；证据相对路径支持正反斜杠，拒绝越界、链接和 junction。Python 工具没有自动启动模型的后端；平台主 Agent 负责真正创建独立会话并保留回执。

## 运行与会话

`run --submission PATH [--out NEW_PATH]` 或 `run --batch JSON`。批次格式：

```json
{"schema":"orthogonal-review.batch.v1","submissions":["relative/task-one","relative/task-two"]}
```

批次相对路径以清单目录为基准，每题保留独立结果。run 输出运行目录；调度者读取 `_internal/state.json` 的 cases/key。

`handoff --run RUN --case case-0001 --role executor|reviewer|diagnostician --actor JSON`。

```json
{"session_id":"actual-platform-session","platform":"actual-platform","fresh_context":true,"isolation":"实际的平台上下文及文件访问约束","launch_evidence":"<平台真实启动回执文件的绝对路径>"}
```

actor 中的回执须实际存在。它是来源证明索引，工具不能认证平台或模型记忆。executor 三轮续用同一 session_id；reviewer 和 diagnostician 必须是不同新会话。handoff 返回工作空间，该空间仅含允许材料和结果模板。不得把运行 state.json 交给角色。

`submit --packet PACKET --result JSON` 保存不可覆盖结果并冻结工件。executor 结构见 packet 模板；reviewer/diagnostician 的每轮结果结构为：

```json
{"round":"R1","status":"unknown","reason":"具体原因","evidence":[]}
```

每条 evidence：

```json
{"path":"chain/R1/output/result.csv","sha256":"<实际SHA256>","locator":"第2行 quantity 单元格"}
```

发现结构：

```json
{"id":"OBS-1","problem":"具体可复查问题","location":"任务或产物位置","cause":"unresolved","confidence":"uncertain","action":"定位原因并补证","done_when":"明确可验证的完成条件","evidence":[]}
```

cause 可为 task_material、environment、execution、agent_capability、unresolved。确认的 task_material 才支持整体 defect；实际三轮完成且独立审查全部 usable 才支持 verified。其他情况 unknown。unusable 描述产物状态，不能单独证明任务缺陷。诊断不替换首次角色结果。

`limit --run RUN --case KEY --reason TEXT` 追加环境或独立会话等限制。`finalize --run RUN` 核冻结指纹并输出两份报告；未执行项不能变成 verified。修改输入、实现、协议或补作者说明时须新建 run。已 finalize 的运行不能追加角色或限制。

## 受控执行

`execute --packet PACKET --plan JSON` 只在尚未提交的角色工作空间执行。执行计划：

```json
{"image":"sha256:<本地镜像64位摘要>","argv":["python","checks/probe.py"],"cwd":".","timeout_seconds":180,"reason":"已审阅入口和读写范围","reviewed_files":[{"path":"checks/probe.py","sha256":"<实际SHA256>"}]}
```

Docker 关闭网络、只读系统、移除 capabilities、非 root、限制内存/CPU/PID；仅挂载本 packet，input/parent/chain 只读。日志在 logs，保留命令、计划、退出码、stdout/stderr 与耗时。镜像不存在或 Docker 不可用时记录 unavailable。不会自动下载、安装或在宿主机执行。

平台已授权的其他专业隔离环境可直接使用，须把真实命令、环境、输入指纹、原生产物与日志放在 packet 的 logs/checks，供证据引用；实际运行方式必须如实说明。只复制目录不能宣称安全沙箱。外部运行的真实性依赖平台原始回执，不能把手写说明当实测日志。
