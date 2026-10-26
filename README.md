# Orthogonal Review

**把仓库链接和交付路径给 Coding Agent：自动准备环境、独立完成任务，再检查真实产物，给你简洁结论和可执行修复单。**

这是甲方的正交审查 Pipeline。它验证任务能否被真实接手和完成，以及产物是否可用；独立于 Review Gate，不读取其结论、历史反馈或参考答案。

## 直接这样用

```text
请使用 https://github.com/sanjinlingyan/orthogonal-review 审查这份交付。
待审提交：<本机单题或批次路径>
读取 AGENTS.md、docs/workflow.md 和 docs/interfaces.md，完成全流程。
缺少环境请实际配置和排障，不要仅报告未检测到工具。
用全新会话 Agent 逐轮完成任务，再由另一位独立 Agent 检查原生产物。
最后给我 review.html 和 repair.md。
```

用户无需手写 JSON，调度 Agent 负责环境、运行及角色交接。平台应支持创建无历史继承的独立会话。核心工具使用 Python 3.10+ 标准库，专业依赖由调度者根据任务实际配置。

## 你会得到

| 文件 | 内容 |
|---|---|
| review.html | 页首结论、通过/不通过/未审查数量、逐轮简表、需处理事项及可展开证据 |
| repair.md | 责任方、精确位置、直接证据、修复动作和复验条件；环境责任单独列出 |

所有必要项目完成并通过才判**通过**；有确定失败即判**不通过**。只有真实配置、排障后仍被客观条件阻断，且没有确定失败时显示**未完成审查**，不作质量判定。部分未审查与确定失败并存时显示不通过，同时列出未审查项。一次 Agent 失败不自动证明任务材料有缺陷。

## 如何工作

1. 定位正式三轮 candidate，声明专业能力需求。
2. 实际配置环境并验证操作能力，不能仅检查命令存在或 import 成功。
3. 全新执行会话按 R1→R2→R3 继承自己的真实产物。
4. 另一个全新会话实际打开、重算、运行或测量产物，逐项判定。
5. 校验证据和冻结指纹，生成两份报告。

环境安装可按用户授权配置本机，不自动购买许可证。内置 environment 命令保存安装/修复/真实能力探针的命令、版本、来源、退出码和原始日志；需要调度者明确授权宿主执行。可选 Docker 工具仅执行既有固定镜像，不会悄悄回退到宿主。详见[工作流程](docs/workflow.md)及[接口](docs/interfaces.md)。

```sh
python run.py run --submission "<交付目录>"
# 调度者声明环境需求、执行准备及操作探针后交接独立角色
python run.py environment --run "<运行目录>" --case case-0001 --requirements "<能力需求.json>"
python run.py environment --run "<运行目录>" --case case-0001 --plan "<环境操作.json>" --allow-host
python run.py handoff --run "<运行目录>" --case case-0001 --role executor --actor "<实际平台会话记录.json>"
python run.py submit --packet "<角色目录>" --result "<实作结果.json>"
python run.py finalize --run "<运行目录>"
```

新运行使用 v2 协议；旧运行和报告原样保留，不原地升级。补材料或已冻结后重新实作使用 `run --previous-run <旧运行>` 建立关联。默认数据目录为仓库旁 `.orthogonal-review/runs/`，严禁真实数据进入公开仓库。

会话独立性依赖平台实际创建的无历史会话；哈希、目录和声明本身不能证明模型记忆或操作系统隔离。报告保留实际边界。

```sh
python -m unittest discover -s tests -v
python tools/check_public.py --tracked
python run.py demo --out "<仓库外的新目录>"
```

演示和测试案例全部虚构，模拟会话不代表真实独立实验。MIT License。

报告版面升级可使用 `python run.py report --run <已冻结v2运行> --out <新的报告目录>`。仅导出呈现，核对原证据与结论，旧报告和审查记录不变；证据链接指向原运行，两个目录须在同一盘符。
