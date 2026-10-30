# 对 `positioning-research-2026-07.md` 的评审与事实核验

- 评审时间：2026-07-28 19:29:22（Asia/Shanghai）
- 评审者：Codex
- 原始文档：`docs/positioning-research-2026-07.md`
- 文档性质：产品定位评审与研究核验，不直接修改既有产品定义

## 总体判断

Qoder 的报告主方向有道理，尤其是产品锐化、价值表达和论文主线方面；但事实严谨性、可观测能力边界和实验设计仍需修订。

综合判断：

- 约 70% 可以吸收；
- 约 20% 需要改写后吸收；
- 约 10% 应暂缓。

这份报告更适合作为“定位与传播提案”，不能未经核验直接升级为批准后的产品方向。

一句话评价：

> 它对产品应该怎样讲、怎样传播判断得很好；对我们实际上能观察什么，以及论文可以严格证明什么，略显乐观。

## 一、最有价值的产品判断

### 1. 从“展示全景图”转向“定位第一个断点”

报告提出的表达：

> Your Skill didn't fire. Or did it?

抓住了用户真正关心的问题。用户不是为了看一张漂亮的生命周期图，而是想知道：

- Skill 为什么没有触发；
- Skill 是否触发但没有按预期执行；
- 执行链最早在哪个阶段缺失或失败；
- 当前结论依赖哪些真实证据。

这与项目现有产品定义中的“first observable lifecycle boundary”是一致的。建议将核心价值表达统一为：

> Find the first observable broken boundary—and inspect the evidence.

其中必须保留 **observable**。不同 Agent adapter 的可见范围不同，产品只能定位“第一个可观察断点”，不能声称发现了模型内部真实发生的第一个因果断点。

### 2. 生命周期价值层次是成立的

建议把能力分成三层：

```text
L1 Reconstruct  发生了什么
L2 Diagnose     第一个可观察断点在哪里
L3 Evaluate     这个 Skill 是否产生可测量价值
```

Qoder 使用了 `Reconstruct → Diagnose → Attribute`。前两层准确，第三层建议改为 `Evaluate`：

- `Attribute` 更适合描述单次运行内的事件与 Skill 关联；
- “Skill 是否有效、是否值得使用”属于跨运行、对照或配对实验意义上的 `Evaluate`；
- 归因记录不能自然升级为因果效果判断。

### 3. “Why not” 诊断值得尽早进入产品

MVP 可以先支持少量、证据边界清晰的诊断规则：

| 诊断结论 | 建议证据等级 |
|---|---|
| Skill 未安装或静态格式无效 | Observed |
| 当前 adapter 不支持观察某阶段 | Observed |
| 未观察到显式 Skill 激活 | Observed |
| Skill 描述与请求语义相似度较低 | Inferred |
| 同一时间窗口内另一个 Skill 被显式激活 | Observed |

Qoder 提出的三类判断需要更谨慎：

1. “Discovery 通过”必须拆成“本地已安装”和“已被 Agent 暴露或发现”，两者不是一回事。
2. 描述与请求的语义相似度可以作为推断证据，但不能证明模型没有选择 Skill 的真实原因。
3. “更高优先级 Skill 抢占”通常不是可观察事实。最多只能观察另一个 Skill 被调用，不能把竞争关系和优先级当作事实。

## 二、必须修正的研究事实

### 1. SkillsBench 数字不准确

当前公开版本报告的是：

- 87 个任务；
- 8 个领域；
- 18 种配置；
- 使用 Skill 后平均成功率从 33.9% 提升到 50.5%；
- 绝对提升 16.6 个百分点。

原报告中的“86 × 11”和“提升 16.2”需要修正。  
来源：[SkillsBench](https://arxiv.org/abs/2602.12670)

### 2. 恶意 Skill 研究的论文与数字混用了

`arXiv:2603.00195` 是 SkillFortify 相关研究，包含一个 540 项的 benchmark，并不是报告中所写的 98,380 个 Skill、157 个恶意 Skill 的统计来源。  
来源：[SkillFortify](https://arxiv.org/abs/2603.00195)

“98,380 个 Skill、157 个恶意 Skill”来自另一篇研究。  
来源：[Skills Are All You Need?](https://arxiv.org/abs/2602.06547)

报告需要把论文、数据集和统计结论一一对应，避免将不同研究拼接成单一证据。

### 3. 部分产业安全数字缺少一手来源

Koi、CERT、Mitiga 等案例中的具体百分比和数量，如果不能找到：

- 原始研究报告；
- 厂商正式公告；
- 漏洞披露；
- 可复核的数据集或论文；

就不应作为论文或产品定义中的确定性数字。可以保留为背景线索，但应标记为待核验，或者删除具体数字。

### 4. Who & When 支持“归因困难”，但不能支撑过强结论

该研究可以支持多 Agent 系统中的来源识别和步骤归因仍然困难。公开摘要报告：

- 最佳 Agent identification 为 53.5%；
- 最佳 step attribution 为 14.2%。

来源：[Who & When](https://arxiv.org/abs/2505.00212)

但“158+ citations”“184 tasks”等表述不能仅依赖摘要得到稳定支持。摘要中提到的是 127 个系统。建议删除不稳定的引用数，并按论文正文核对任务规模。

此外，“没有任何人做 Skill-level attribution”属于 novelty claim。更严谨的写法应是：

> 在本次系统检索覆盖的公开研究和工具中，尚未发现以证据分级方式重建跨 Agent Skill 生命周期的同类工作。

### 5. OpenTelemetry 只能证明标准缺口，不能证明标准已经成熟

OpenTelemetry Semantic Conventions 的相关 issue 确实存在，但截至评审时：

- issue 仍开放；
- 状态为 Need triage；
- 没有 assignee；
- 没有 milestone；
- 没有关联的已合并 PR。

来源：[OpenTelemetry issue #86](https://github.com/open-telemetry/semantic-conventions-genai/issues/86)

因此它能支持“社区已经意识到 Skill 遥测缺口”，不能支持“Skill 遥测标准化已经成熟”。

该提案使用 `gen_ai.skill.*` 命名，而本项目当前事件模型使用 `skill.runtime.*`。产品应维护清晰的映射层：

```text
内部稳定事件模型
        ↓
版本化 exporter mapping
        ↓
OTel / Rapid / 其他可观测系统
```

不要把内部 schema 直接宣传成行业标准。

## 三、Behavior Profile 的价值与边界

Behavior Profile 是一个有价值的方向，但不能将其中所有信息都标记为 Observed。

例如，观察到：

```text
Skill(pdf)
  ↓
Bash: python scripts/render.py
```

只能证明 Agent 启动了该命令。仅依靠 Agent 工具事件，通常无法完整观察脚本内部：

- 读取了哪些文件；
- 派生了哪些子进程；
- 访问了哪些网络地址；
- 读取了哪些环境变量；
- 使用了哪些系统调用。

要观察这些内部行为，需要更深层的 OS instrumentation、eBPF、DTrace、sandbox audit 或语言运行时探针。

因此 UI 应明确展示：

- Tool-layer behavior；
- 归因证据等级；
- 当前采集覆盖范围；
- `Internal behavior unknown`；
- 未观察到不等于没有发生。

“自动在沙箱中运行第三方 Skill”会让产品从 observer 漂移成 runner 或 orchestrator，不符合当前产品边界。更合适的方式是：

> 用户在自己的沙箱或测试环境中运行，Skill Runtime Intelligence 被动采集和分析。

## 四、与 SkillScope 的竞品关系

原报告把 SkillScope 简化为“触发次数统计”，这个描述不准确。

SkillScope 已经覆盖：

- transcript 解析；
- triggers；
- subagents 与 hooks；
- per-skill token 和成本；
- active attribution；
- dead weight；
- SVG 报告。

来源：[SkillScope](https://github.com/notsointresting/skillscope)

本项目真正可以形成差异化的部分应是：

- Skill 生命周期重建，而不只是调用统计；
- 多源证据合并；
- Observed、Derived、Inferred、Experimental 分级；
- 跨 Agent、版本化 adapter；
- resources、scripts、artifacts 的链路归因；
- first observable gap 诊断；
- 原始事件、标准化事件和推断记录分层保存；
- 标准化导出到 Rapid、OpenTelemetry 和其他可观测系统。

README 必须直接回答：

> 为什么用户不用 SkillScope，而使用 Skill Runtime Intelligence？

UI 更美观不构成可靠的长期差异化。

## 五、实时上报与零配置传播

“一条命令看到昨天的运行”是很强的产品入口，但必须区分两种模式。

### Historical Replay

- 默认零配置；
- 读取已有 session、transcript 和本地文件；
- 低侵入；
- 能力不完整；
- 适合快速体验和事后分析。

### Live Instrumented

- 使用 Agent hooks、原生事件或 OTLP；
- 支持接近实时的事件上报；
- 覆盖率更高；
- 需要显式配置；
- 适合持续可观测和专业环境。

建议将 Rapid 看成一个 exporter，而不是产品主语：

```text
Agent adapters
      ↓
Canonical Skill Runtime Event Model
      ↓
Local evidence store
      ↓
Analysis / diagnosis
      ↓
Rapid | OTLP | JSONL | other observability systems
```

论文或产品传播中如果要使用数千条真实运行数据，数据来源必须明确区分：

- 用户主动 opt-in 的匿名数据；
- 公开 transcript；
- 受控实验；
- 合成 fixture；
- 单独授权的企业数据。

产品绝不能默认静默上传本地运行数据。

## 六、论文路线评估

### Paper 1：Skill Runtime Observability

这是当前最强、最可执行的论文方向。建议贡献聚焦于：

- 跨 harness 的 Skill lifecycle；
- capability-aware reconstruction；
- evidence-grade attribution；
- transcript-only、hooks-only、combined 三类采集模式；
- event recall；
- relationship precision；
- evidence calibration；
- runtime overhead；
- adapter 兼容性和缺失证据表达。

“首个数据集”只能在完成系统性文献检索后使用。更稳妥的初始表述是：

> A cross-harness evidence-graded dataset for Agent Skill runtime analysis.

ICSE、FSE、ASE 与当前问题更自然匹配。NSDI 只有在系统层出现明确的分布式采集、低开销遥测或大规模运行时贡献时才合适。

### Paper 2：Skill Effectiveness

方向有价值，但当前实验设计还不成熟。

主要问题：

- 激活频率高度受任务分布影响；
- 10 个随机种子没有功效分析支撑；
- 瓶颈可能是 harness、环境和 verifier，而不只是 GPU；
- 人工移除或修改 Skill 的 ablation 可能不符合真实使用；
- 单次运行的归因不能直接证明 Skill 有效。

建议先做小型 pilot：

```text
3–5 个 Skill
× 2 个 Agent harness
× 2 个模型
× with / without Skill
× 确定性 verifier
```

先验证：

- 任务是否真的依赖 Skill；
- 结果能否稳定验证；
- 方差是否可控；
- 运行成本是否可接受；
- 事件记录能否解释结果差异。

## 七、建议的产品决策

### 直接吸收

- Panorama 是呈现形式，不是最终价值主张；
- 核心价值改为定位 first observable broken boundary；
- 使用 `Reconstruct → Diagnose → Evaluate` 三层能力；
- 尽早实现少量可解释的诊断规则；
- 保留零配置 Historical Replay；
- 设计默认脱敏、可分享的 Run Card；
- 参与 OpenTelemetry Skill 遥测讨论；
- 优先推进 Paper 1。

### 修改后吸收

- Security Behavior Profile；
- why-not 诊断规则；
- 竞品空白和 novelty 表述；
- 生态规模与安全统计；
- OpenTelemetry reference implementation 的宣传；
- 大规模真实运行研究。

### 暂缓

- 把“更高优先级 Skill 抢占”作为 Observed 事实；
- 自动运行未知第三方 Skill 的沙箱能力；
- 直接开展大规模 Paper 2 GPU 实验；
- 在 MVP 主标题中承诺回答 Skill 是否 “worth it”。

## 八、建议的产品定位

建议将产品定位收敛为：

> Skill Runtime Intelligence 是一个 local-first、evidence-graded 的 Agent Skill 运行时可观测与诊断工具。它从静态 Skill 文件、Agent 运行事件、session 日志和可观察产物中重建 Skill 生命周期，定位第一个可观察断点，并通过版本化 adapter 和标准 exporter 接入不同 Agent 与可观测系统。

它不是：

- 通用 Agent session viewer；
- Skill marketplace；
- Skill registry；
- 安全阻断网关；
- 模型请求代理；
- Agent orchestration runtime；
- 通用 LLM observability platform。

当前最重要的产品纪律仍然是：

> 只陈述证据能够支持的事实，并让用户看见结论的证据基础和观察盲区。

## 参考资料

- `docs/product-definition.md`
- `docs/mvp-specification.md`
- `docs/runtime-event-model.md`
- `docs/ui-information-architecture.md`
- [Agent Skills specification](https://agentskills.io/specification)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [SkillsBench](https://arxiv.org/abs/2602.12670)
- [SWE-Skills-Bench](https://arxiv.org/search/?query=SWE-Skills-Bench&searchtype=all)
- [Skills Are All You Need?](https://arxiv.org/abs/2602.06547)
- [SkillFortify](https://arxiv.org/abs/2603.00195)
- [Who & When](https://arxiv.org/abs/2505.00212)
- [OpenTelemetry Semantic Conventions issue #86](https://github.com/open-telemetry/semantic-conventions-genai/issues/86)
- [SkillScope](https://github.com/notsointresting/skillscope)
