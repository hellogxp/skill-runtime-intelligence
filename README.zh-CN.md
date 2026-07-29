# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · **简体中文** · [繁體中文](README.zh-TW.md) ·
[Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) ·
[Español](README.es.md) · [日本語](README.ja.md) · [한국어](README.ko.md) ·
[Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) ·
[Türkçe](README.tr.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) ·
[Magyar](README.hu.md)
<!-- locale-switcher:end -->

> 定位 Agent Skill 执行最早发生偏差的位置，并检查每项结论背后的证据。

Agent Skill Runtime Intelligence 是面向 Agent Skills 的只读运行时证据与诊断系统。
它将 Skill 定义、Agent 官方运行事件、导入的 Trace、会话回退数据和可观察的工作区
结果，重建为证据分级的 Skill Run Panorama。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## 快速开始

使用已登录的 GitHub CLI，从私有仓库安装独立发行版：

```bash
install_tmp="$(mktemp -d)"
gh release download --repo hellogxp/skill-runtime-intelligence \
  --pattern install.sh --dir "$install_tmp"
sh "$install_tmp/install.sh"
skill-runtime start
```

或者从源码运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

打开 [http://127.0.0.1:4317](http://127.0.0.1:4317)。使用 Codex 时，请在
`/hooks` 中核对并信任由 Skill Runtime 管理的命令，开始一个新的 Agent 回合，然后执行：

```bash
.venv/bin/skill-runtime doctor
```

只有收到真实的官方 Hook 事件后，集成状态才会变为 **Verified**。仅完成 Hook 配置时
显示为 **Pending**，不会冒充实时证据。

| 产品界面 | 回答的问题 |
|---|---|
| Runtime Overview | 哪些 SkillRun 值得关注？ |
| First Observable Boundary | 证据最早从哪个边界开始缺失或失败？ |
| Skill Run Panorama | 请求、激活、资源、工具、产物与结果如何连接？ |
| Evidence Inspector | 哪个来源、证据等级、判断依据和适配器能力支持这项结论？ |
| Compare | 差异来自行为本身，还是仅来自可观测能力不同？ |
| Settings / Doctor | 系统读取、存储和导出了什么，哪些连接待验证？ |

## 要解决的问题

安装了 Skill，不代表 Agent 发现了它；发现不代表激活；激活不代表完整指令和资源
已加载；执行完成也不代表 Skill 改善了结果。

这些问题通常静默发生，开发者只能反复猜测：

- Agent 当时能否发现这个 Skill？
- 它是否针对该请求被激活？
- 哪些指令、references、scripts 和 assets 被加载？
- 哪些工具、MCP 调用、子 Agent、文件和产物参与了执行？
- 执行在哪一步失败、重试或丢失上下文？
- Skill 真正产生了帮助，还是只增加了成本和延迟？

## 产品形态

核心产品是 **Skill Run Panorama**：

```text
User request
    ↓
Skills discovered
    ↓
Skill selected / not selected
    ↓
SKILL.md activated
    ↓
References and scripts loaded
    ↓
Tools / MCP / subagents executed
    ↓
Files and artifacts produced
    ↓
Observable outcome
```

全景图由真实信号拼接，而不是依赖模型自述：

| 来源 | 示例 | 证据性质 |
|---|---|---|
| Skill 文件 | 元数据、指令、scripts、references、assets | Observed |
| 运行事件 | Skill 调用、工具调用、子 Agent、失败、耗时 | Observed |
| 会话记录 | 请求、消息、工具输入输出和顺序 | Observed |
| 工作区结果 | 文件变更、Git diff、报告和生成产物 | Observed |
| 关联分析 | 事件、资源与结果之间的关系 | Derived 或 Inferred |

## 证据纪律

UI 绝不能把推断伪装成运行事实：

- **Observed**：明确存在于来源事件或文件中。
- **Derived**：可由已观察证据确定性连接得到。
- **Inferred**：带有不确定性的合理解释。
- **Experimental**：通过受控配对实验测量得到的效果。

单条 Trace 可以支持执行归因，但不能证明因果有效性。“这个 Skill 提高了成功率”
一类结论，必须来自多次有 Skill／无 Skill 的配对实验。

## 产品原则

- 默认保护隐私，同时支持本地、混合和团队连接部署。
- 只读观察，不接管 Agent loop。
- 不代理模型请求，也不强制依赖云服务。
- 默认产品不阻断、不审批、不执行策略。
- 所有结论都带来源与证据等级。
- 渐进披露：先给简洁叙事，再按需展示脱敏事件。
- 每个 Agent 集成均由独立、版本化的 adapter 承担。

## 当前能力范围

当前支持 Codex 与 Claude Code，并提供：

- 已安装 Skill 的发现、解析与完整性检查；
- 历史会话导入，以及 Agent 支持时的实时本地观测；
- Skill 激活、资源加载和工具调用时间线；
- 子 Agent、MCP、文件和产物关系；
- 来源提供时的耗时、token、错误、重试和状态摘要；
- 运行列表、全景 DAG、事件时间线、证据检查器与能力感知对比。

当前不做 Skill 市场、通用 Agent Runtime、安全执法、企业治理或单次运行因果结论。

## 安装与生命周期

基础运行时仅要求 Python 3.9+。在仓库根目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

随后打开 [http://127.0.0.1:4317](http://127.0.0.1:4317)。

一次性的 `install` 会：

1. 扫描用户、项目和插件缓存中的 Skill；
2. 检测 Codex 与 Claude Code，但不擅自修改其配置；
3. 明确列出将读取的 Agent 与 Skill 路径；
4. 优先下载带校验和的低启动开销原生 sender；不可用时回退到本地 C 编译，
   最后回退到 Python sender，并在安装阶段完成一次预热；
5. 创建 `~/.skill-runtime/config.json` 与本地 SQLite 索引。

交互安装会在添加 fail-open Hook 前征求一次同意。`--no-hooks` 会将会话导入保留为
明确标注的 fallback；`--enable-hooks` 会记录用户授权，并只安装带管理标记的条目。

对于 Codex，安装后请打开 `/hooks`，核对命令并授予信任。完成一个新的 Agent 回合后执行：

```bash
.venv/bin/skill-runtime doctor
```

数据库只有在收到真实 `official_hook` 事件后才会把集成显示为 **Live**。仅写入
`~/.codex/hooks.json` 时显示 **Pending**。`start` 会以受管理的后台进程启动
Collector、会话 fallback watcher、保留策略 worker、SQLite 和实时 UI；整个过程
不代理任何模型请求。

常用生命周期命令：

```bash
skill-runtime status
skill-runtime doctor
skill-runtime restart
skill-runtime stop
skill-runtime config --set retention_days=30
skill-runtime config --set network_export.endpoint=https://collector.example/v1/traces
skill-runtime config --set network_export.enabled=true
skill-runtime uninstall --keep-data
```

`uninstall` 只删除本次安装明确拥有的 Hook 条目和 Skill Runtime 文件。未使用
`--keep-data` 时，删除 `~/.skill-runtime` 前需要交互确认或 `--yes`。Agent 会话和
Skill 源文件永远不会被删除。

如需分别执行索引和服务：

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

导入主流可观测系统导出的 Trace：

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

版本化导入 profile 当前识别 OTLP/Phoenix、Langfuse、LangSmith、W&B Weave 和
Datadog JSON 形态。只有来源明确携带 Skill 语义时才创建 SkillRun；通用 span 名称
不会被当作激活证据。

将标准化的 Skill 运行证据实时导出到任意 OTLP/HTTP Trace 端点：

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

没有显式配置端点时，网络导出保持关闭。Settings 会展示 checkpoint、重试状态和
目标健康度。原始提示词、工具 payload、凭据和 Skill 资源内容不会被导出。

后台认证导出应在启动前通过标准环境变量 `OTEL_EXPORTER_OTLP_HEADERS` 提供 Header；
Header 不会写入 Skill Runtime 配置或进程参数。

## 发送实时运行证据

`skill-runtime start` 内置本地 Collector。原生 telemetry adapter、官方 Hook、
轻量 fail-open Hook 和 SDK 集成都可以向 `POST /api/events` 发送单个事件或有界批次：

```bash
curl -X POST http://127.0.0.1:4317/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "evt-example-activation",
    "event_type": "skill.activated",
    "occurred_at": "2026-07-29T05:00:00Z",
    "session_id": "agent-session-example",
    "turn_id": "turn-1",
    "activation_mode": "explicit_tool",
    "skill": {"name": "pdf"},
    "source": {
      "adapter": "example-agent",
      "adapter_version": "1.0",
      "collection_mode": "official_hook",
      "source_event_id": "source-event-1"
    },
    "evidence": {
      "grade": "observed",
      "confidence": 1.0,
      "basis": "Official runtime hook"
    },
    "payload": {"tool_name": "Skill"}
  }'
```

Collector 会在持久化前脱敏常见凭据，通过 `event_id` 去重，单独保存脱敏后的原始
envelope，并返回生成的 `skill_run_ids`。`GET /api/collector/schema` 会列出支持的
事件词汇和采集方式。UI 通过 `/api/stream` 使用 SSE 接收更新，只在重连时回退轮询。

来源指示器会区分主要运行证据、`Transcript fallback` 与导入 Trace。仅有 Collector
端点不代表具备原生 telemetry；每个生产者必须声明其事件来自原生 telemetry、
官方 Hook、轻量 Hook 还是 SDK。

### 可选 Agent Hook

先用只读命令查看将涉及的路径和事件：

```bash
.venv/bin/skill-runtime setup
```

只有显式指定参数才会安装 Hook：

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

安装器会备份 Agent 配置、保留原有 Hook，并且只添加带 Skill Runtime 管理标记的条目。
Hook adapter 仅保存最小生命周期字段，不复制完整提示词或工具 payload。

Runtime 运行时，权限受限的 Unix socket 是低延迟路径；可选原生 sender 避免 Python
冷启动。Runtime 不在线时，独立的 fail-open 路径把脱敏证据追加到
`~/.skill-runtime/queue/events.jsonl`，随后由 `skill-runtime start` 按事件 ID
去重回放。

Codex 使用官方 Hook API：`SessionStart`、`SessionEnd`、`UserPromptSubmit`、
`PreToolUse`、`PostToolUse`、`PreCompact`、`PostCompact`、`SubagentStart`、
`SubagentStop` 和 `Stop`。Codex 当前同步执行命令 Hook，因此 Skill Runtime 使用
本地 Unix socket／原生 sender 和有界超时。任何投递失败都会被吞掉并进入队列，
不会改变 Agent 的决定。参见
[Codex Hook 官方文档](https://developers.openai.com/codex/config-advanced#hooks)。

仅移除由本产品管理的条目：

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

服务默认绑定 `127.0.0.1`。完整会话消息和工具 payload 不会复制进索引，常见敏感
信息在标准化摘要持久化前完成脱敏。

运行无额外依赖的测试套件：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 发布工程

GitHub Actions 会验证 Python 3.9–3.13、JavaScript、原生 sender 编译，以及真实的
install/start/doctor/stop/uninstall 生命周期。`v*` tag 会构建 wheel、sdist、
独立 zipapp，以及带校验和的 Linux/macOS 原生 sender。CLI 安装器下载匹配的发布
制品，终端用户不需要本地编译器。

运行首个与产品诊断直接关联的实验：

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

该实验注入生命周期证据缺口、显式失败、不完整运行和未验证结果，并评估 API 与 UI
共用的确定性诊断引擎。实验阶梯、无干扰测试和复现要求见
[PAI-DSW 实验计划](docs/pai-dsw-experiment-plan.md)。

构建 wheel 后，运行隔离的产品生命周期测试：

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

测试会在临时虚拟环境和临时 HOME 中完成整个本地生命周期，不启用 Hook，并验证项目
与 Agent 配置没有被修改。

## 实验驱动的产品设计

产品行为受[实验驱动的产品设计哲学](docs/experiment-driven-product-philosophy.md)
约束：证据先于结论，最早可观察边界先于严重度，类型化关系先于平面日志，确定性
重建先于概率性辅助。

当前可复现的本地证据包括：

- 7/7 本地实验门禁通过；
- Collector 接收 2,400/2,400 个事件，未修改输入或输出；
- 确定性诊断在 14/14 个故障语料案例上正确，且没有不受支持的因果断言；
- 关系诊断表示达到 13/14 exact、F1 0.963；平面生命周期检索仅为
  1/14 exact、F1 0.080；
- 11/11 个学习材料案例将最早可观察边界置于首位。

这些结果验证的是机制与表示选择，不是部署泛化能力或总体用户收益。真实第二 Agent、
跨平台尾延迟、真实故障校准和参与者诊断研究仍是明确的证据缺口。

研究方向同时参考相邻的一手工作：
[SkillsBench](https://arxiv.org/abs/2602.12670) 与
[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) 表明 Skill 效果存在差异并可能
回归；[Harness-Bench](https://arxiv.org/abs/2605.27922) 支持能力感知的跨 Agent
比较；[执行溯源综述](https://arxiv.org/abs/2606.04990) 支持类型化证据关系、Trace
溯源和隐私感知审计基础设施。

## 文档

- [产品定义](docs/product-definition.md)
- [MVP 规格](docs/mvp-specification.md)
- [运行时事件模型](docs/runtime-event-model.md)
- [UI 信息架构](docs/ui-information-architecture.md)
- [适配器能力矩阵](docs/adapter-capability-matrix.md)
- [可观测互操作](docs/observability-interoperability.md)
- [可观测平台接入](docs/observability-platform-setup.md)
- [研究与竞品格局](docs/research-and-competitive-landscape.md)
- [研究论文议程](docs/research-paper-agenda.md)
- [实验驱动的产品设计哲学](docs/experiment-driven-product-philosophy.md)
- [实验结果](docs/experiment-results-2026-07-29.md)
- [PAI-DSW 实验计划](docs/pai-dsw-experiment-plan.md)

## 路线

1. **v0.1 — 运行证据与诊断：** 实时采集、Skill Run Panorama、首边界诊断、
   证据检查、运行对比与 OTLP 互操作。
2. **v0.2 — Adapter 广度与诊断研究：** 更多 Agent、真实跨 Agent 实验和参与者评估。
3. **v0.3 — 效果评估：** 受控的有 Skill／无 Skill 配对实验，与单次运行诊断严格分离。

## 项目状态

SkillRun-first Runtime 已可运行：已安装定义清单、Codex 会话 fallback、经用户同意的
Codex 和 Claude Code 官方 Hook adapter、active-scope 归因、精确文件／产物路径、
脱敏、独立 source／relationship／inference 数据层、SQLite、保留策略、跨运行和
跨 Agent 对比、确定性诊断与实时 Panorama UI。

系统可导入 OTLP/Phoenix、Langfuse、LangSmith、W&B Weave 和 Datadog 导出，并可
通过主动启用的 OTLP/HTTP 实时导出标准化证据。当前可复现实验套件有七个通过的门禁。
候选发现、模型内部选择原因、语义有效性和因果结果结论仍明确标为不支持。
