# Agent Skill Runtime Intelligence

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)

<!-- locale-switcher:start -->
[English](README.md) · **简体中文** · [繁體中文](README.zh-TW.md) ·
[Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) ·
[Español](README.es.md) · [日本語](README.ja.md) · [한국어](README.ko.md) ·
[Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) ·
[Türkçe](README.tr.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) ·
[Magyar](README.hu.md)
<!-- locale-switcher:end -->

> 将 `SKILL.md` 转化为可检查的运行预期：看清实际发生了什么、行为从哪里开始
> 偏离，以及判断所依据的证据。

Agent Skill Runtime Intelligence 是面向 Agent Skills 的只读运行时证据与诊断系统。
它从当前 Skill 定义中提取保守、可检查的行为约束，与真实运行活动进行匹配，再将
Agent 官方事件、导入 Trace、明确标识的 session fallback 和可观察工作区结果重建为
证据分级的 Skill Run Panorama。它不代理模型请求，也不接管 Agent loop。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## 快速开始

在 macOS 或 Linux 上安装最新公开版本并启动：

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

不需要克隆仓库、`sudo` 或 GitHub CLI。安装器会自动选择当前系统和架构，并在启用
fail-open 只观测 Hook 前请求一次明确授权。本地 UI 地址为
[http://127.0.0.1:4317](http://127.0.0.1:4317)。除非显式配置导出，否则所有
运行数据都保存在 `~/.skill-runtime`。


### 查看第一个实时 SkillRun

1. 安装器询问时，同意启用可选的 fail-open Hook。
2. 重启 Agent 并新建任务。使用 Codex 时，先在 `/hooks` 中核对并信任受管理的
   命令；已经打开的任务不会热加载新 Hook。
3. 正常使用一个 Skill，然后确认集成状态：

```bash
skill-runtime doctor
skill-runtime status
```

只有 Collector 收到真实运行事件后，集成才是 **Live**。已配置但尚未观察到事件的
Hook 只会显示为 **Pending**，不会冒充实时证据。打开
[http://127.0.0.1:4317](http://127.0.0.1:4317)，或阅读
[Getting Started](docs/getting-started.md) 了解各 Agent 的操作与排障方法。

从源码运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| 产品界面 | 回答的问题 |
|---|---|
| Runtime Overview | 哪些 SkillRun 值得关注？ |
| Skill 行为检查 | 哪些可检查指令已经满足、需要复核或无法评估？ |
| 实际发生了什么 | 观察到了哪些指令、资源、工具、产物和结果？ |
| First Observable Boundary | 单次运行的证据最早从哪个边界开始缺失或失败？ |
| Skill Run Panorama | 请求、激活、资源、工具、产物与结果如何连接？ |
| Evidence Inspector | 哪个来源、证据等级、判断依据和适配器能力支持这项结论？ |
| Compare | 差异来自行为本身，还是仅来自可观测能力不同？ |
| Inferred Analysis | 哪种证据约束下的解释或下一步调查方向是合理的？ |
| Settings / Doctor | 系统读取、存储和导出了什么，哪些连接待验证？ |

## 工作原理

![运行时架构](docs/assets/runtime-architecture.svg)

Skill Runtime 伴随观察用户原有的 Agent 工作流。版本化 adapter 将 Agent
原生事件转换为稳定的 Skill 生命周期，同时把来源事件、标准化事件、关系与推断
分别保存。诊断引擎用这些证据检查 Skill 的显式行为约束，定位最早可观察偏离，
并将系统性 adapter 盲区与单次运行问题分开。它不编造模型意图，也不从单次运行
推断因果有效性。

| 数据来源 | 作用 | 时效性 | UI 标识 |
|---|---|---|---|
| Agent 官方 Hook／插件／SDK 事件 | 主要的生命周期、工具、子 Agent 与终态证据 | 实时 | `Official hook` / `Native telemetry` |
| Skill 文件与可观察工作区结果 | 定义、资源、文件、产物与测试证据 | 实时快照／索引 | `Observed` |
| Session 记录 | Agent 没有充分 Runtime API 时的兼容回退 | 准实时或历史 | `Transcript fallback` |
| OTLP 与支持的 Trace 导出 | 可观测互操作与历史导入 | 实时导出／批量导入 | 显示来源 profile |
| 确定性关联 | 在不改写来源事实的前提下把事件连接到 SkillRun | 采集时 | `Derived` |
| 语义助手 | 只提供解释与调查建议 | 按需 | `Inferred` |

当前第一方 adapter 独立版本化：

| Agent | 主要集成 | 回退 | 激活可见性 |
|---|---|---|---|
| Codex | 官方 command Hooks | Session 导入 | Hook 事件暴露时可观察显式激活 |
| Claude Code | 官方 Hooks | Session 导入 | 来源暴露时可观察 Skill tool 与 slash command |
| Qoder | 官方 command Hooks | 本地记录 | Skill tool 暴露时可观察显式激活 |
| OpenCode | 只观测全局插件 | 本地记录 | 来源暴露时可观察 Skill tool callback |

每个版本的精确能力边界见
[adapter capability matrix](docs/adapter-capability-matrix.md)。不支持与未观察到的
阶段会保持可见，不会被转化成失败。

## 要解决的问题

安装了 Skill，不代表 Agent 发现了它；发现不代表激活；激活不代表完整指令和资源
已加载；加载指令也不代表 Agent 遵守了指令；执行完成更不代表 Skill 改善了结果。

这些问题通常静默发生，开发者只能反复猜测：

- Agent 当时能否发现这个 Skill？
- 它是否针对该请求被激活？
- 哪些指令、references、scripts 和 assets 被加载？
- 哪些明确的 Skill 要求被遵守、遗漏，或因为证据不足无法评估？
- 哪些工具、MCP 调用、子 Agent、文件和产物参与了执行？
- 执行在哪一步失败、重试或丢失上下文？
- Skill 真正产生了帮助，还是只增加了成本和延迟？

## Skill 专属诊断

核心诊断对象是 `SkillRun`，不是整个 Agent session：

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

UI 以有序、类型化、证据分级的方式展示生命周期。缺少激活 telemetry 只代表
“未观察到”或“来源不支持”，不代表 Agent 一定跳过了 Skill。

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

## 当前范围

当前通过独立、版本化的 adapter 支持 Codex、Claude Code、Qoder 与 OpenCode，
并提供：

- 已安装 Skill 的发现、解析与完整性检查；
- 实时官方 Hook／插件采集，以及明确标识的 session fallback；
- Skill 激活、资源加载和工具调用时间线；
- 子 Agent、MCP、文件和产物关系；
- 来源提供时的耗时、token、错误、重试和状态摘要；
- 从当前 `SKILL.md` 提取的保守、可检查行为约束；
- 证据边界内的符合性、结果验证与运行失败检查；
- 具体的指令、资源、工具、产物与结果清单；
- 将系统性采集限制与单次运行问题分开的 Runtime Overview；
- First Observable Boundary 诊断；
- 全景 DAG、事件时间线与 Evidence Inspector；
- 能力感知的同 Agent 与跨 Agent 对比；
- 不能改写运行事实的独立 Inferred Analysis；
- 可选 OTLP/HTTP 实时导出与支持的可观测 Trace 导入。

当前不做 Skill 市场、通用 Agent Runtime、安全执法、企业治理或单次运行因果结论。

## 安装与生命周期

最短路径请使用[快速开始](#快速开始)中的一行发行版安装命令。完整首次使用流程、
各 Agent 的重启／信任操作、隐私行为与排障方法见
[Getting Started](docs/getting-started.md)。

开发模式仅要求 Python 3.9+。在仓库根目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

随后打开 [http://127.0.0.1:4317](http://127.0.0.1:4317)。

一次性的 `install` 会：

1. 扫描用户、项目和插件缓存中的 Skill；
2. 检测 Codex、Claude Code、Qoder 与 OpenCode，但不擅自修改其配置；
3. 明确列出将读取的 Agent 与 Skill 路径；
4. 优先下载带校验和的低启动开销原生 sender；不可用时回退到本地 C 编译，
   最后回退到 Python sender，并在安装阶段完成一次预热；
5. 创建 `~/.skill-runtime/config.json` 与本地 SQLite 索引。

首次索引会导入已有的兼容 Agent 会话。长期使用的工作站可能比全新环境耗时更长；
后续启动采用增量刷新，UI 会先就绪，后台再继续更新索引。

交互安装会在添加 fail-open Hook 前征求一次同意。`--no-hooks` 会将会话导入保留为
明确标注的 fallback；`--enable-hooks` 会记录用户授权，并只安装带管理标记的条目。

对于 Codex，安装后请打开 `/hooks`，核对命令并授予信任；随后新建一个
Codex 任务/会话，再执行：

```bash
.venv/bin/skill-runtime doctor
```

Qoder 在启动时加载 Hook 配置，因此首次安装后需要重启 Qoder。OpenCode 从全局
插件目录加载本产品管理的只观测插件；若当前 OpenCode 进程早于安装启动，也请
重启一次。两个集成都不读取或修改模型请求。

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

产品行为遵循四条实验驱动约束：证据先于结论，最早可观察边界先于严重度，类型化
关系先于平面日志，确定性重建先于概率性辅助。

可复现实验及其限制统一维护在
[实验报告](docs/experiment-results-2026-07-29.md)中。目前有边界的结果包括：

- Collector 接收 2,400/2,400 个事件，未修改输入或输出；
- 确定性诊断在 14/14 个故障语料案例上正确，且没有不受支持的因果断言；
- 关系诊断表示达到 13/14 exact、F1 0.963；平面生命周期检索仅为
  1/14 exact、F1 0.080；
- 隐私安全的真实运行审计明确显示：因为缺少已验证结果、均衡的跨 Agent 覆盖和
  人工标签，当前数据不能支持产品效果的确认性结论。

这些结果验证的是机制与表示选择，不是部署泛化能力或总体用户收益。真实第二 Agent、
跨平台尾延迟、真实故障校准和参与者诊断研究仍是明确的证据缺口。

研究方向同时参考相邻的一手工作：
[SkillsBench](https://arxiv.org/abs/2602.12670) 与
[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) 表明 Skill 效果存在差异并可能
回归；[Harness-Bench](https://arxiv.org/abs/2605.27922) 支持能力感知的跨 Agent
比较；[执行溯源综述](https://arxiv.org/abs/2606.04990) 支持类型化证据关系、Trace
溯源和隐私感知审计基础设施。

## 文档

| 建议入口 | 作用 |
|---|---|
| [Getting Started](docs/getting-started.md) | 安装、连接 Agent、验证实时证据和排障 |
| [Architecture](docs/architecture.md) | 采集链路、存储边界、证据引擎与信任模型 |
| [Adapter 能力矩阵](docs/adapter-capability-matrix.md) | 各 Agent／版本的精确信号与限制 |
| [可观测平台接入](docs/observability-platform-setup.md) | 连接 OTLP 平台并导入支持的 Trace |
| [运行时事件模型](docs/runtime-event-model.md) | 稳定事件词表、溯源、关系与证据等级 |
| [UI 信息架构](docs/ui-information-architecture.md) | Overview、首边界、Panorama、Inspector、Compare 与 Inferred Analysis |
| [变更记录](CHANGELOG.md) | 按版本整理的用户可见变化 |
| [v0.3.0 发行说明](docs/releases/v0.3.0.md) | 升级方法、核心变化与已知限制 |

产品与研究资料包括：[产品定义](docs/product-definition.md)、
[MVP 规格](docs/mvp-specification.md)、
[可观测互操作](docs/observability-interoperability.md)、
[实验结果](docs/experiment-results-2026-07-29.md)和
[研究论文议程](docs/research-paper-agenda.md)。

## 社区与治理

- 修改证据语义、adapter 或产品行为前，请先阅读[贡献指南](CONTRIBUTING.md)。
- 在所有项目空间遵守[行为准则](CODE_OF_CONDUCT.md)。
- 安全问题请按[安全策略](SECURITY.md)私下报告，不要创建公开 issue。
- 可复现缺陷和范围明确的功能建议请使用结构化的
  [issue tracker](https://github.com/hellogxp/skill-runtime-intelligence/issues)。
  不要上传私有运行数据库或 session 记录。

## 路线

1. **v0.3.0 — 下一发行版：** 可检查的 Skill 行为约束、具体运行活动、证据边界内的
   判断、系统性采集限制诊断，以及既有的实时 Panorama 与 Compare 工作流。
2. **下一步 — Adapter 与诊断加固：** 扩展 Agent／版本覆盖，开展真实故障校准、
   跨平台尾延迟验证与参与者诊断研究。
3. **后续 — 效果评估：** 受控的有 Skill／无 Skill 配对实验，并与单次运行诊断
   明确分离。

## 项目状态

当前源码以 `v0.3.0` 为发行目标；最新公开构建请以页面顶部的 release badge 为准。
Runtime 包含可检查的 Skill 行为约束、具体活动摘要、
已安装定义清单、经用户同意的 Codex、Claude Code 与 Qoder 官方 Hook adapter、
只观测 OpenCode 插件、明确标识的 session fallback、active-scope 归因、精确
文件／产物路径、脱敏、独立
source／relationship／inference 数据层、SQLite、保留策略、确定性诊断、实时 UI
以及跨运行和跨 Agent 对比。

系统可导入 OTLP/Phoenix、Langfuse、LangSmith、W&B Weave 和 Datadog 导出，并可
通过主动启用的 OTLP/HTTP 实时导出标准化证据。模型内部的候选发现与选择原因、
语义有效性和因果结果结论，除非来源或受控实验提供证据，否则仍明确标为不支持。
