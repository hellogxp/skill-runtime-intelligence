# Agent Skill Runtime Intelligence：产品定义与产品形态

Status: approved direction  
Date: 2026-07-28  
Working category: **Agent Skill Runtime Intelligence**

## 1. 产品定义

> **面向所有 Agent Skill 用户的运行时全景与诊断系统，既能诊断单个
> Agent 中的 Skill 执行，也能比较同一 Skill 在不同 Agent 中的运行差异。**

英文价值表达：

> **Understand and diagnose how Skills run—within one agent or across agents.**

用户继续正常使用 Codex、Claude Code、Gemini CLI、GitHub Copilot 等
Agent。产品运行在 Agent 旁边，采集并关联真实运行信号，
重建 Skill 从发现、激活、指令加载、资源使用、执行到结果之间的证据链。

产品不代理模型请求，不接管 Agent loop，不要求用户从本产品发起任务，也不在
默认模式下阻断或改变 Agent 行为。

## 2. 产品解决的问题

Agent Skills 采用渐进加载：

1. Agent 发现 Skill 的名称和描述；
2. Skill 被显式或自动激活；
3. 完整 `SKILL.md` 指令进入运行上下文；
4. references、scripts 和 assets 按需使用；
5. Agent 调用工具、子 Agent 或 MCP 完成工作；
6. 文件、测试、报告和最终回复构成可观察结果。

每个边界都可能静默失败。用户即使看到一个看似合理的最终回答，仍然可能无法
确定：

- Skill 是否已经安装并被当前 Agent 发现；
- Skill 是否被显式调用或自动触发；
- Skill 的完整指令是否真正加载；
- 所需 reference、script 或 asset 是否被使用；
- Skill 激活期间发生了哪些工具调用和文件变化；
- 第一个可观察的缺失或失败边界在哪里；
- 问题来自 Skill、Agent、模型、环境、任务还是观测能力不足；
- 同一个 Skill 为什么在不同 Agent、版本或入口中表现不同。

通用 Agent tracing 通常以 session、model span 和 tool span 为中心，不能把
Skill 生命周期作为主要诊断对象。本产品以 `SkillRun` 为核心实体，Agent
session 仅作为其运行上下文。

## 3. 面向所有用户

产品不把跨 Agent、团队部署或维护大量 Skills 作为使用前提。只要用户使用了
一个 Agent 中的一个 Skill，就应该能够获得完整的基础价值。

| 用户 | 核心价值 |
|---|---|
| 普通 Agent 用户 | 看清 Skill 是否运行、做了什么、为何失败 |
| Skill 作者 | 调试触发、资源加载、指令遵循和版本变化 |
| 跨 Agent 用户 | 比较同一 Skill 在不同 Agent 中的发现和执行差异 |
| 团队与平台用户 | 聚合运行，发现共性故障、环境漂移和兼容性问题 |
| 研究人员 | 获得证据分级的 Skill 运行数据和可复现实验基础 |

Skill 作者、重度用户和平台团队是高密度痛点来源，适合作为重点研究样本，但
不是产品受众边界。

## 4. 两种同等重要的使用模式

### 4.1 单 Agent 诊断

用户只使用 Codex、Claude Code、Gemini CLI 或其他任意一个 Agent，也可以：

- 查看已安装和已发现的 Skills；
- 查看 Skill 是否被激活以及激活方式；
- 查看实际加载的指令和资源；
- 查看 Skill 作用域内的工具、子 Agent、文件和产物；
- 定位第一个可观察异常边界；
- 对比同一 Agent 中的不同运行、模型或 Skill 版本。

单 Agent 是完整的产品模式，而不是跨 Agent 功能的简化版。

### 4.2 跨 Agent 对比

当用户使用多个 Agent 时，产品进一步提供：

- 同一 Skill 在不同 Agent 中的发现与安装状态；
- 显式调用、自动激活和嵌套激活差异；
- 指令和资源加载差异；
- 工具链、子 Agent 和产物差异；
- 模型、Agent 版本和运行入口造成的行为漂移；
- 各 Agent adapter 的可观察能力与盲区。

跨 Agent 是增强能力和长期壁垒，不是使用门槛。

## 5. 产品总体形态

产品由轻量采集层、运行时证据引擎和专业可视化界面组成：

```text
Codex / Claude / Gemini / Copilot 正常运行
                       │
                       ▼
          Agent Adapter 与被动信号采集
                       │
Skill 静态文件 ────────┼────── 文件 / Git / 测试 / 产物
                       │
                       ▼
              Runtime Evidence Engine
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   Run Panorama    Diagnostics    Compare
                                      │
                                      ▼
                        可选团队服务与标准化导出
```

用户不需要改变原有 Agent 工作流。产品持续构建 Skill 运行证据，并通过全景、
诊断和对比回答：

1. Skill 是否运行；
2. Skill 如何运行；
3. 第一个可观察异常点在哪里；
4. 当前判断依据哪些证据；
5. 哪些信息因为 Agent 或 adapter 限制仍然未知。

## 6. 用户可见的产品界面

### 6.1 Runtime Overview

首页回答“现在有哪些 Skill 值得关注”，而不是罗列所有 Agent session：

- 最近运行或尝试运行的 Skills；
- 未触发、运行异常或证据不完整的 SkillRuns；
- 当前已安装和已发现的 Skills；
- Agent adapter 状态与数据新鲜度；
- 需要用户关注的诊断 Findings；
- 单 Agent 与跨 Agent 的近期行为变化。

### 6.2 Skills

以 Skill 为主体展示：

- 名称、描述、来源、路径、版本和内容摘要；
- 安装在哪些 Agent、项目和作用域；
- 声明的触发条件和调用限制；
- scripts、references 和 assets；
- 最近运行与异常；
- 不同 Agent 的兼容性和可观察能力。

### 6.3 SkillRuns

列表的主要实体是 Skill 的一次运行，而不是整个 Agent session。每条记录至少
包含：

- Skill、Agent、模型、项目和时间；
- 显式、自动、嵌套、派生或未知的激活方式；
- 运行状态、耗时和证据完整度；
- 第一个可观察异常边界；
- 所属 session 和 turn 上下文。

没有观察到 Skill 激活的 session 可以作为上下文记录存在，但不能伪装成
SkillRun。

### 6.4 Skill Run Panorama

全景图是单次 Skill 运行的核心解释界面：

```text
Request
   ↓
Discovery
   ↓
Activation
   ↓
Instructions
   ↓
Resources
   ↓
Execution
   ↓
Artifacts
   ↓
Outcome
```

每个阶段展示：

- 是否观察到；
- 来自哪个数据源；
- 发生了什么；
- 是否存在异常；
- 缺失是未发生、未观察到还是 adapter 不支持；
- 与其他事件的关系和证据等级。

大规模运行默认折叠重复事件，展示关键路径；用户可以继续下钻到完整时间线。

### 6.5 Evidence Inspector

点击任何节点或诊断结论后展示：

- 人类可读的说明；
- 原始来源和 source locator；
- 证据等级、置信度和判断依据；
- 相关父子事件、文件和产物；
- 脱敏后的输入与输出；
- 缺失的 telemetry；
- adapter 的已知限制。

Raw JSON 只在用户显式展开时显示。

### 6.6 Diagnostics

诊断系统输出可行动、可验证而且不过度断言的结论：

```text
Finding: Skill 未运行

第一个可观察异常点：Discovery

Observed:
- Skill 文件存在并且静态格式有效
- Codex App 的 Skill 列表能够扫描到该 Skill
- 当前 CLI runtime 的 available skills 中不存在它

Possible causes:
- 当前 Agent 版本不支持该 Skill 路径
- 项目 trust 状态可能阻止项目级 Skill 加载

Evidence grade: Derived
Missing signal: 官方 runtime discovery event
```

诊断必须回答：

1. 发生了什么；
2. 第一个可观察异常点在哪里；
3. 为什么得出这个判断；
4. 还有什么无法确定。

### 6.7 Compare

Compare 同时支持：

- 同一 Agent 的不同运行；
- 同一 Agent 的不同 Skill 版本；
- 同一 Skill 的不同模型或 Agent 版本；
- 同一 Skill 的不同 Agent；
- 修改前和修改后；
- 单次运行与历史基线。

对比按统一生命周期阶段对齐，同时显示数据源和 adapter 能力差异，避免把
“无法观察”误判为“没有发生”。

### 6.8 Settings

设置界面包括：

- Agent adapters；
- 纳入和排除的项目；
- Hook 与原生 telemetry 状态；
- 隐私、脱敏和数据保留；
- 本地、混合或团队连接；
- 导入、导出和数据删除。

## 7. 数据来源与采集优先级

全景和诊断不能只依靠本地 session。产品按以下优先级组合多种真实信号：

| 优先级 | 数据来源 | 可提供的信息 |
|---|---|---|
| A | Agent 原生 Skill telemetry / OTel | 激活、触发方式、Skill scope、耗时 |
| B | 官方 hooks 与稳定 runtime API | 生命周期、工具、子 Agent、错误、文件事件 |
| C | Session transcript | 消息、tool call/result、顺序和兼容性回退 |
| D | Skill 静态文件 | 声明、指令、资源、版本、安装位置 |
| E | Workspace、Git、测试与产物 | 文件变化、命令结果、测试和独立结果证据 |
| F | 显式 evaluation | 重复对照运行和可测量效果 |

不同 Agent 的可见信号并不相同。每个版本化 adapter 必须声明：

- 支持的 Agent 和版本；
- 能直接观察的生命周期阶段；
- 使用的原生事件、Hook、API 或 transcript；
- 哪些关系需要派生或推断；
- 已知 schema、隐私和兼容性限制。

### 7.1 原生信号优先

当 Agent 提供原生 Skill activation、tool span 或 OTel 事件时优先使用，减少
对不稳定 transcript schema 的依赖。

### 7.2 Hook 模式

当原生信号不足时，可以安装 fail-open hook。同步路径只做最小事件写入，
关联、诊断和上传异步执行。Hook 失败不能阻止 Agent 继续运行。

“非干预”指产品不改变 Agent 的决策和结果，不代表 Hook 绝对没有延迟。产品
必须测量并展示采集延迟、事件丢失和 adapter 健康状态。

### 7.3 无 Hook 模式

用户不安装 Hook 时，产品仍可扫描 Skill、导入或监听 session、关联文件与
产物并生成事后全景。缺少直接证据的阶段必须标注为 Derived、Inferred、
Not observed 或 Unsupported。

## 8. 证据等级

### Observed

来源事件或文件直接编码的事实，例如：

- 原生事件报告某个 Skill 被激活；
- `SKILL.md` 被读取；
- 某工具调用及其返回结果；
- 命令退出码；
- 文件创建事件。

### Derived

从 Observed 证据确定性关联的关系，例如：

- source parent ID 连接的父子调用；
- 工具结果明确报告其创建的文件；
- 匹配的 start/end 事件计算出的耗时。

### Inferred

存在不确定性的解释，例如：

- Skill 描述与请求可能匹配；
- 缺少某个资源可能解释不完整输出；
- 两个 Skill 的触发描述可能冲突。

每个推断必须显示 basis 和 confidence。Unknown 优于没有证据的确定性结论。

### Experimental

通过受控重复实验得到的效果估计，例如：

- 使用与不使用 Skill 的 pass-rate delta；
- 匹配任务中的 token 或 latency overhead；
- 置信区间和配对检验结果。

单次运行中的事件关联不能升级为 Skill 因果有效性的证明。

## 9. 安装与首次使用

目标体验：

```bash
skill-runtime install
skill-runtime start
```

产品随后：

1. 检测本机已安装的 Agent；
2. 扫描用户、项目和插件中的 Skills；
3. 解释将读取哪些本地路径；
4. 允许用户排除项目和目录；
5. 检测可用的原生 telemetry、hooks 和 transcript；
6. 优先使用已有原生信号；只有用户明确同意时才增量安装 fail-open hook；
7. 导入已有记录并监听新事件；
8. 打开 Runtime Overview。

用户无需创建云账号，也无需在产品中重新发起 Agent 任务。
安装器会在本机编译器可用时构建一个极小的 Unix-socket sender，以降低实时
hook 的进程启动成本；没有编译器时自动回退，不影响基础产品可用性。

## 10. 部署形态

本地、中心化和混合是交付选择，不是产品定位和市场边界。

### 10.1 个人本地模式

- 本机采集、存储和 UI；
- 不要求账号；
- 支持一个或多个 Agent；
- 原始敏感证据不离开设备。

### 10.2 个人混合模式

- 原始敏感证据保留在本机；
- 可选同步脱敏后的 SkillRun、诊断和兼容性摘要；
- 支持多设备历史和备份。

### 10.3 团队模式

- 每位成员运行本地 collector；
- 团队服务聚合标准化事件和诊断；
- 支持跨成员、环境、版本和 Agent 分析；
- prompt、文件内容和工具参数可以根据策略不上传。

Local-first 可以是隐私和低门槛特性，但不是产品核心卖点。核心卖点始终是：
**Skill 运行时可理解、可诊断、可比较。**

## 11. 内部产品架构

### 11.1 Agent Adapters

按 Agent 和版本接入原生 telemetry、hooks、runtime API 与 transcript。

### 11.2 Skill Inventory

解析 Skill 定义、来源、版本、内容摘要、资源和安装位置。

### 11.3 Evidence Store

分离保存：

```text
raw_source_records
        ↓
normalized_events
        ↓
derived_relationships
        ↓
inferences
        ↓
experimental_results
```

### 11.4 Reconstruction and Diagnosis Engine

- 识别真实 SkillRun；
- 重建生命周期；
- 关联资源、工具、子 Agent、文件和结果；
- 定位第一个可观察异常边界；
- 生成 evidence-graded Findings；
- 维护 adapter capability-aware missingness。

### 11.5 Panorama and Compare UI

面向普通用户提供可理解的全景和诊断，面向专业用户提供完整证据下钻和对比。

### 11.6 Optional Sync and Export

以标准化、可插拔方式同步团队服务或导出到外部系统，不绑定任何单一可观测
产品。

## 12. MVP 产品形态

第一版不要求立即覆盖所有 Agent，但产品模型从一开始面向所有 Agent Skill
用户，并通过版本化 adapter 持续扩展支持范围。

### 第一版应包含

- Codex adapter；
- Claude Code adapter；
- Qoder adapter；
- OpenCode adapter；
- 自动发现本机 Agent 和 Skills；
- 原生信号优先的实时采集；
- 历史 session 导入；
- 真正的 SkillRun 识别；
- 八阶段 Run Panorama；
- Evidence Inspector；
- 基础异常 Findings；
- 同 Agent 运行与版本对比；
- 跨 Agent 对比；
- 隐私、脱敏和 adapter capability 设置。
- 标准 OTLP/HTTP 实时导出（显式 opt-in）；
- Indexed SkillRun 删除和可执行的数据保留策略。

### 第一版可以暂缓

- 通用 Agent session observability；
- Skill marketplace 或 package registry；
- Skill 发布、promotion、canary 和流量控制；
- 自动修改 Skill；
- 自动重跑、恢复和自愈；
- 安全策略阻断；
- 模型请求代理；
- 从单次运行声明 Skill 的因果有效性。

## 13. 成功标准

新用户安装后五分钟内，应能够回答：

1. 当前 Agent 能看到哪些 Skills？
2. 这次任务是否运行了 Skill？
3. Skill 实际加载和执行了什么？
4. Skill 产生了哪些文件、产物和结果？
5. 第一个可观察的缺失或失败边界在哪里？
6. 哪些结论是事实、派生关系、推断或实验结果？

对于跨 Agent 用户，还应能够回答：

7. 同一个 Skill 在不同 Agent 中哪一个生命周期阶段开始出现差异？
8. 差异来自真实行为，还是来自 adapter 观测能力不同？

## 14. 产品纪律

- Observe agent runs; do not orchestrate them.
- 默认只读采集和本地可用。
- 不代理模型请求。
- 默认不阻断 Agent 行为。
- 不存储不必要的 secrets 和原始敏感内容。
- 所有判断标记为 Observed、Derived、Inferred 或 Experimental。
- 不从一次运行宣称 Skill 的因果效果。
- 原始来源、标准化事件、派生关系和推断分离保存。
- 每个 Agent 集成位于独立的版本化 adapter 后面。
- 缺失证据不等于执行失败。
- UI 必须同时展示结论、证据与观测盲区。
