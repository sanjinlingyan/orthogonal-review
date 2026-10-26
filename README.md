# Orthogonal Review

**把仓库链接和交付路径给 Coding Agent，独立实作三轮任务，再检查产物能否真正使用。**

这是甲方的正交审查 Pipeline。新的执行 Agent 从实际下发材料开始完成工作，另一位新的 Agent 直接检查原生产物。实作失败要区分任务缺陷、环境问题、执行问题、能力限制和原因未明。

## 直接这样用

```text
请使用 https://github.com/sanjinlingyan/orthogonal-review 审查这份交付。
待审提交：<本机单题或批次路径>

读取 README.md、AGENTS.md、docs/workflow.md，完成独立冷启动实作和产物审查。
使用全新上下文的执行 Agent，按 R1→R2→R3 继承本次真实产物；
再交给另一位全新 Agent 深入检查。最后给我 review.html 和 repair.md。
```

用户无需手工写 JSON。主 Agent 负责定位材料、整理批次清单、调度新会话、记录环境和调用工具。流程不要求真人参与，也无需为本仓库另配模型 API Key。平台必须能创建无继承对话的新 Agent 会话；做不到时出具“尚无法确定”及具体原因。

## 得到什么

| 文件 | 用途 |
|---|---|
| `review.html` | 甲方看大结论、关键发现、三轮实际完成情况、产物可用性及证据 |
| `repair.md` | 乙方 Agent 看问题位置、现场证据、归因、修复动作和验证条件 |

整体结论为“已验证可完成且可用”“已确认存在任务或交付缺陷”或“尚无法确定”。某个 Agent 做不出来，不自动判任务有问题；冷启动成功也不替代合同符合性验收。诊断结果保留单独记录，不能覆盖首次失败。

## 如何独立

执行者只收到当前轮 `candidate/` 的副本和自己上一轮真实产物。审查者只收到已开放轮次的任务材料、本次原生产物和执行日志；不收到执行者的判断摘要。两者都不读 Review Gate 报告、修复单、历史判定、乙方参考答案或评分结果。

调度者负责审阅下发边界并用平台创建全新上下文。工具拒绝相同会话兼任独立审查、伪造父态跳轮、覆盖已冻结结果和证据哈希不符。**文件夹与哈希不等于操作系统权限隔离，也不能自行证明模型记忆独立。** 报告披露平台回执和实际隔离方式；应把角色工作空间设置为平台允许访问的范围。

## 运行条件与命令

Python 3.10+，核心工具仅使用标准库，支持 Windows/Linux。原生软件、插件和许可证按任务实际提供。内置命令执行器需要 Docker 和已安装的固定镜像；也可由平台已有的获授权隔离环境运行，保存等价的完整命令、输入、环境和输出记录。缺环境时保留现场并出具未确定结论。

```sh
python run.py run --submission "<交付目录>"
python run.py handoff --run "<运行目录>" --case case-0001 --role executor --actor "<平台会话记录.json>"
python run.py submit --packet "<角色工作空间>" --result "<实作结果.json>"
# 同一执行会话逐轮 handoff / submit，之后用新会话 --role reviewer
python run.py finalize --run "<运行目录>"
```

可选受控执行、批次和环境限制记录见 [接口](docs/interfaces.md)。完整调度顺序见 [工作流程](docs/workflow.md)。退出码 0 表示命令成功，业务结论看报告；操作错误返回 2。

默认输出在仓库旁 `.orthogonal-review/runs/<编号>/`。也可指定 `run --out` 到仓库外新目录。真实数据、运行副本、报告及日志不得进入公开仓库。公开仓库只有流程、工具、测试及明确虚构的示例；不公开甲方需求或真实案例。

```sh
python run.py demo --out "<仓库外的新目录>"
python -m unittest discover -s tests -v
python tools/check_public.py --tracked
```

演示文件全部虚构。测试中的模拟会话只测试协议，不代表真实独立 Agent 实验。MIT License。
