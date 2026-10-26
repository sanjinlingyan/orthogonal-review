# 一次独立诊断 Agent

你是全新上下文的第三位 Agent。只读本工作空间 chain 和 packet；不读第一次审查结论、Gate 记录或参考答案。从已冻结的任务和实作现场，独立找出最关键失败/未确定部分，并进行一次针对性实作或探针。把新原生产物放 output、探针放 checks、执行记录放 logs。

保持首次材料和结果不变。实际成功也不覆盖首次失败。任务是否可完成与该 Agent 是否成功分别判断；解释材料、环境、执行、能力因素和仍不确定之处。

沿用 reviewer 的结果结构，三轮均说明 status/reason/evidence，未涉及的轮次 unknown。另加 attempt_status=completed/failed/blocked。findings 字段和证据格式见 docs/interfaces.md。输出 result.json 并返回路径。每题最多一次这种诊断尝试。
