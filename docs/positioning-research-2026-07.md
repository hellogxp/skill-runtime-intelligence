# 定位完善与论文支撑 Research 报告

Snapshot date: 2026-07-28
Revision: 2026-07-28 (r2, 经 Codex 评审对焦后修订)
Status: research input, not yet approved direction
Scope: 行业痛点分析、产品定位锐化建议、传播策略、论文路线（含实验设计）

本文档是对 `research-and-competitive-landscape.md` 的补充调研，不改变
`product-definition.md` 已批准的方向；其中的建议需评审后再落入产品文档。

> r2 修订说明：本版依据 Codex 评审
> （`codex_positioning-research-review_2026-07-28_19-29-22.md`）修正了 r1 中的
> 事实错误与过强表述，并把可观测能力边界、命名、实验规模收敛到可被证据
> 支持的范围。对焦状态汇总见第 8 节，实验环境见第 9 节。

## 1. 行业现状：三个正在交汇的趋势

### 1.1 Skill 生态已成事实标准，但基础设施严重滞后

- 截至 2026 年中，约 40 个产品支持 agentskills.io 标准（Claude Code、
  Codex、Copilot、Cursor、Gemini CLI 等 15+ CLI agent 支持 `SKILL.md`）。
- GitHub `agent-skills` topic 已有 5600+ repos，`claude-skills` 3600+，
  awesome 列表收录 1000+ Skills。
- 配套工具几乎只有两类：目录/市场（ClawHub、marketplace）和静态检查。
  "装了 Skill 之后发生了什么"这一环没有基础设施。

类比：2015 年的 npm、2019 年的 Kubernetes——包生态爆发 → 运行时黑盒 →
可观测/供应链工具窗口期。本项目处于窗口期早段。

### 1.2 三条独立证据链证明"Skill 运行时是黑盒"是真实痛点

**(a) 效果不确定——装了不等于有用**

- SkillsBench（87 任务 × 8 领域 × 18 配置）：使用 Skill 后平均成功率从
  33.9% 提升到 50.5%（绝对 +16.6pp），但方差极大、部分任务倒退；自生成
  Skills 平均无收益。来源: [arXiv:2602.12670](https://arxiv.org/abs/2602.12670)
  （r1 曾误记为 86×11 / +16.2，已修正。）
- SWE-Skills-Bench：多数公开 SWE Skills 零 pass-rate 增益，且带来显著
  token 开销；版本不匹配的指导反而降低性能。
  来源: [arXiv:2603.15401](https://arxiv.org/abs/2603.15401)
- 社区共识性抱怨："If your skill does not trigger, it is almost never
  the instructions. It is the description."——开发者靠猜测调试触发问题。

**(b) 安全不可信——静态审计不够**

- 学术侧（依据综述 arXiv:2602.12430 的权威归属，三项独立研究分开引用）：
  - Liu et al. "Agent Skills in the Wild"：采集 42,447 个 skills、分析
    31,132 个，26.1% 含至少一个漏洞；含可执行脚本的 skill 漏洞风险
    2.12×（OR=2.12, p<0.001）；5.2% 具高危模式。
    来源: [arXiv:2601.10338](https://arxiv.org/abs/2601.10338)
  - Liu et al. "Malicious Agent Skills in the Wild"：行为验证 98,380 个
    skills，确认 157 个恶意（632 个漏洞）；单一产业化行为体占确认案例
    54.1%。来源: [arXiv:2602.06547](https://arxiv.org/abs/2602.06547)
    （r2 曾标题误记为 "Skills Are All You Need?"，按综述引用修正。）
  - Schmotz et al.：Skill 文件是"平凡地简单"的 prompt injection 向量，
    可绕过系统护栏。来源: [arXiv:2510.26328](https://arxiv.org/abs/2510.26328)
- 产业侧线索（Koi、CERT、Mitiga、Unit42、HiddenLayer 的具体百分比/数量）
  在找到一手研究报告、厂商正式公告或可复核披露前，仅作背景线索，**标记
  为待核验**，不作为论文或产品定义中的确定性数字。
- 安全厂商的共同定性结论是 "runtime behavior may differ from static
  appearance"，但市场上没有工具能低成本回答"这个 Skill 运行时到底做了
  什么"。只读 panorama 恰好是这个问题的答案，且无需做安全产品。

**(c) 学术界已把"失败归因"立为正式方向，但没人做 Skill 粒度**

- Who&When（ICML 2025）开创 "automated failure attribution in LLM
  multi-agent systems"，公开摘要报告最佳 agent identification 仅 53.5%、
  best step attribution 仅 14.2%（覆盖 127 个系统）——问题被认可且远未
  解决。来源: [arXiv:2505.00212](https://arxiv.org/abs/2505.00212)
  （r1 曾引用 "158 引用 / 184 tasks"，无稳定来源，已删除。）
- 2026 年已出现 trajectory analysis survey（"From Failure Attribution
  to Enhancement"）、graph-based credit assignment、counterfactual
  credit（leave-one-out）等一批工作。
- 上述工作均以 agent/step 为归因单元。**在本次检索覆盖的公开研究与工具
  中，尚未发现以证据分级方式重建跨 Agent Skill 生命周期的同类工作**（作为
  novelty 线索而非绝对断言，正式投稿前须做系统性文献检索确认）。

### 1.3 标准化窗口正在打开

OpenTelemetry GenAI 语义约定仓库已有开放的 "Add skill span" 提案
（[semantic-conventions-genai#86](https://github.com/open-telemetry/semantic-conventions-genai/issues/86)）。但截至评审时该 issue 仍开放、状态 Need triage、无 assignee、
无 milestone、无已合并 PR。因此它只能支持"社区已意识到 Skill 遥测缺口"，
**不能支持"Skill 遥测标准化已成熟"**。

该提案使用 `gen_ai.skill.*` 命名，而本项目事件模型使用 `skill.runtime.*`。
必须维护一个版本化映射层（内部稳定事件模型 → exporter mapping →
OTel / Rapid / 其他系统），**不要把内部 schema 直接宣传成行业标准**。
可以以实现者身份参与讨论并提交意见，但定位是"参与者"而非"标准已采纳。

## 2. 痛点结构化：谁在什么时刻痛

| 角色 | 痛点时刻 | 现在的做法 | 缺口 |
|---|---|---|---|
| Skill 作者 | Skill 没触发/半触发，看到似是而非的答案 | 肉眼翻 JSONL transcript、改 description 重试 | 无生命周期视图，无"第一个失败边界"诊断 |
| 团队 Skill 维护者 | 模型/harness 升级后 Skill 行为变了 | 无感知，等用户抱怨 | 无跨版本运行对比 |
| 采用 Skill 的工程师 | 装了 10 个 Skill，不知道哪些在干活、哪些烧 token | SkillScope 数触发次数 | 触发次数 ≠ 有效性（H4） |
| 安全审阅者 | 第三方 Skill 静态看着没问题 | 静态扫描 | 无运行时行为证据 |
| 研究者 | 想量化 Skill 效果 | 自建 harness 跑 benchmark | 无标注归因数据集、无跨 harness 事件模型 |

竞品覆盖确认（对 `research-and-competitive-landscape.md` §2 的更新）：
Langfuse/LangSmith/Phoenix 是通用 span 层（不做 Skill 抽象）；SkillsBench/
SWE-Skills-Bench 是离线 benchmark；安全厂商做静态扫描。

**SkillScope 不能简化为"触发计数"**（r1 描述不准）。它已覆盖：transcript
解析、triggers、subagents 与 hooks、per-skill token/成本、active
attribution、dead weight、SVG 报告（[SkillScope](https://github.com/notsointresting/skillscope)）。
本项目的真实差异化必须讲清楚，而不是靠"UI 更好看"：

- Skill 生命周期重建（而非调用统计）；
- 多源证据合并；Observed/Derived/Inferred/Experimental 分级；
- 跨 Agent、版本化 adapter；resources/scripts/artifacts 链路归因；
- first observable gap 诊断；原始/标准化/推断记录分层保存；
- 标准化导出到 Rapid/OTLP/其他可观测系统。

README 必须直接回答：为什么用户不用 SkillScope，而用本产品？
"运行时 Skill 生命周期重建 + 证据分级归因"这一格仍然是空的，且被
benchmark 与安全两侧的研究反向验证了需求。

## 3. 产品定位完善建议

现有定位（local-first, read-only, evidence-graded Skill Run Panorama）
方向正确，建议做四点锐化。

### 3.1 把主叙事从"看全景"升级为"回答一个问题"

"Panorama" 是界面名词，不是传播钩子。建议主消息改为直击痛点的问句：

> Your Skill didn't fire. Or did it? — Find the first **observable**
> broken boundary, and inspect the evidence.

关键词 `observable` 必须保留（评审修正）：不同 Agent adapter 可见范围不同，
产品只能定位"第一个可观察断点"，不能声称发现了模型内部真实发生的第一
个因果断点。五个边界（可见 → 匹配 → 加载 → 执行 → 产出）中"第一个可
观察地断掉的地方"是开发者真正想要的答案；narrative summary 和 panorama
是这个答案的呈现方式。`product-definition.md` §10 的"5 分钟 6 问"应提到
README/官网首屏。

### 3.2 明确三层价值阶梯

```text
L1  Reconstruct   它到底做了什么                  （MVP，已实现雏形）
L2  Diagnose      第一个可观察断点在哪里         （why-not-triggered，提前进 v0.2）
L3  Evaluate      它是否产生可测量价值（跨运行配对评测）（Experimental 证据层）
```

r1 用的是 `Reconstruct → Diagnose → Attribute`，第三层改为 `Evaluate`：
`Attribute` 描述单次运行内事件与 Skill 的关联（它是 L2 的技术机制），
"是否有效、是否值得用"属于跨运行对照/配对实验意义上的 `Evaluate`；归因
记录不能自然升级为因果效果判断。

建议：把 L2 最小版从 deferred 提前进 v0.2。"为什么没触发"是社区最高频
抱怨，也是传播性最强的功能。但诊断规则必须严格化、证据边界清晰（经
评审修正后的版本）：

| 诊断结论 | 证据等级 |
|---|---|
| Skill 未安装或静态格式无效 | Observed |
| 当前 adapter 不支持观察某阶段 | Observed |
| 本地已安装但未被 Agent 暴露/发现 | Observed |
| 未观察到显式 Skill 激活 | Observed |
| Skill 描述与请求语义相似度较低 | Inferred（附 basis 与 confidence） |
| 同一时间窗口内另一个 Skill 被显式激活 | Observed |

三个必须谨慎的修正（r1 过强）：

1. "discovery 通过"必须拆成"本地已安装"与"已被 Agent 暴露/发现"，两者
   不是一回事。
2. 描述与请求相似度只能作 Inferred，不能证明模型未选择 Skill 的真实原因。
3. "更高优先级 Skill 抢占"**通常不是可观察事实**：最多只能观察到另一个
   Skill 被调用，不能把竞争关系与优先级当作事实（列入第 8 节暂缓项）。

### 3.3 吸收安全侧需求但不做安全产品

给 panorama 增加"行为摘要（Behavior Profile）"视图。但必须区分证据等级：
工具层事件只能证明 Agent 启动了某命令（如 `Bash: python render.py`），
**通常无法观察脚本内部行为**（读了哪些文件/子进程/网络地址/环境变量/
系统调用）；那需要 eBPF/DTrace/sandbox audit/语言运行时探针。因此 UI 必须
显式标注：Tool-layer behavior、归因证据等级、当前采集覆盖范围、
`Internal behavior unknown`，并明确"未观察到不等于没发生"。

定位仍是"审计理解界面，不拦截"（符合项目非协商原则）。**不得提供"自动
在沙箱运行未知第三方 Skill"能力**——那会让产品从 observer 漂移成 runner/
orchestrator。正确措辞是：

> 用户在自己的沙箱或测试环境中运行，Skill Runtime Intelligence 被动采集和分析。

### 3.4 占据标准位

- 以实现者身份参与 OTel semantic-conventions-genai#86，把
  `skill.runtime.*` 事件模型作为 reference implementation 提交意见。
- 把 `runtime-event-model.md` 单独发布为一页规范（类似 OpenInference
  的做法），产品是规范的第一个实现。品类名 "Agent Skill Runtime
  Intelligence" 要靠规范 + 论文 + 产品三件套钉死。

## 4. 快速传播策略

开发者工具传播的核心是"30 秒内看到自己的数据被点亮"。本地已有
Claude Code/Codex session，零配置即可回放，是天然优势。

1. **一条命令的 Demo 路径**：`uvx skill-runtime-intelligence` → 自动
   发现本机 sessions → 打开 runs UI。首屏必须出现用户自己昨天的运行
   记录（不是示例数据）。
2. **可晒的产物**：panorama 图 + narrative summary 适合截图传播。给
   UI 加"导出运行卡片（PNG/SVG，自动脱敏）"。
3. **内容弹药（按传播力排序）**：
   - "We analyzed N thousand real Skill runs: X% of activations
     silently skipped resources"——用产品自身产出的实证数据写文（也是
     论文 empirical study 的预演）；
   - "为什么你的 Skill 没触发：五个边界的实证分类"；
   - "第三方 Skill 运行时行为画像：静态审计看不到的部分"；
   - Show HN: "See what your Claude Code Skills actually did"。
4. **渠道顺序**：Show HN → agentskills.io 生态列表收录 →
   awesome-agent-skills PR → Anthropic/OpenAI 开发者社区 → OTel GenAI
   SIG。
5. **命名**：已排除 SkillScope/SkillLens。传播前必须定名，建议方向是
   "证据/回放"隐喻而非 "scope/lens" 隐喻，需按
   `research-and-competitive-landscape.md` §6 的清单做正式检索。

## 5. 论文支撑路线（结合 GPU 资源）

`research-paper-agenda.md` 的 6 个 candidate contributions 一篇论文
装不下，建议拆成两篇加一个 benchmark 资产；GPU 资源主要用于第二篇。

### 5.1 Paper 1（系统 + 实证；目标 ICSE/FSE/NSDI 类，或 arXiv + workshop 先行）

> Reconstructing and Attributing Agent Skill Runtime Behavior Across
> Heterogeneous Harnesses

- 贡献：跨 harness Skill 生命周期事件模型 + capability-aware
  reconstruction + Observed/Derived/Inferred/Experimental 证据分级 +
  一个跨 harness、证据分级的 Skill runtime 分析数据集。
  （"首个数据集"只能在完成系统性文献检索后使用；初始表述用 "A
  cross-harness evidence-graded dataset for Agent Skill runtime analysis"。）
- 采集模式对比：transcript-only、hooks-only、combined 三类。
- 实验（轻量算力）：
  - 标注 200–500 条真实/构造 session（Claude Code + Codex），测 event
    recall、relationship precision、evidence calibration（对应 H2、H3）；
  - runtime overhead、adapter 兼容性与缺失证据表达；
  - 大规模实证扫描：量化五个可观察边界各自的静默失败率（H1）——
    论文 headline number，也是最好的传播素材。
- 目标会议：ICSE/FSE/ASE 与当前问题更自然匹配；NSDI 仅在出现明确的
  分布式采集/低开销遥测/大规模运行时贡献时才合适。
- 与 Who&When 的差异化叙事：他们归因"哪个 agent/step 错了"，本项目
  归因"Skill 生命周期哪个可观察边界断了"，并用证据分级降低无根据推断。

### 5.2 Paper 2（评测 + 归因；目标 NeurIPS/ICML/COLM）

> Activation Is Not Effectiveness: Controlled Attribution of Agent
> Skill Marginal Utility

方向有价值（核心假设 H4/H5：触发频率是效果的坏代理；同一 Skill 跨
harness/模型行为显著不同），但 r1 的实验设计过于乐观，需先做 pilot。

**r1 设计的主要问题**：激活频率高度受任务分布影响；10 seeds 无功效分析
支撑；瓶颈可能是 harness/环境/verifier 而非 GPU；人工移除/修改 Skill 的
 ablation 可能不符合真实使用；单次运行归因不能直接证明 Skill 有效。

**先做小型 pilot（适配当前 H20 单卡环境）**：

```text
3–5 个 Skill
× 2 个 Agent harness
× 2 个模型
× with / without Skill
× 确定性 verifier
```

pilot 先验证：任务是否真的依赖 Skill；结果能否稳定验证；方差是否可控；
运行成本是否可接受；事件记录能否解释结果差异。通过 pilot 后再做功效
分析、确定种子数与规模，才扩到边界消融与反事实归因校准实验。

边界消融与反事实归因校准仍是本项目事件模型的独特贡献，但它们属于 pilot
证实可行后的第二阶段，不列入 MVP 路径。开源模型 self-host 将重复试验成本
降一个量级，是本地算力的正确用途。

### 5.3 Benchmark 资产（社区钩子）

把标注数据集 + 消融 harness 发布为 "SkillAttrBench" 类资产（脱敏
fixtures、评测脚本、可复现图表，对应 `research-paper-agenda.md` §8 的
artifact 清单）。归因方向的标注数据极稀缺，这是论文影响力与产品传播的
双重杠杆（具体数据集规模以正式构建为准，不预设数字）。

产品-论文飞轮：产品收集真实运行 → 实证发现（headline numbers）→ 论文
→ 论文反哺产品公信力与品类定义权。须保持 `research-paper-agenda.md`
§6 的纪律：产品遥测与研究数据集分离、明确 consent、脱敏。

## 6. 风险与建议行动顺序

### 风险

1. Anthropic/OpenAI 官方内置 Skill 调试视图。应对：跨 harness + 证据
   分级 + 本地历史数据是官方单一产品做不到的。
2. transcript 格式无稳定契约。已有 adapter 版本化 + fixtures 应对。
3. 品类名过长不利传播。用问句钩子承担传播，品类名承担定义。

### 建议 90 天顺序

1. 打磨"一条命令看到自己的运行"体验 + 导出运行卡片（传播地基）。
2. 最小 why-not-triggered 诊断进 v0.2（最强传播功能）。
3. 用产品跑自己/社区的 sessions，产出首批边界失败率实证数据 → 首篇
   传播文 + Show HN。
4. 并行启动 Paper 1 数据标注；GPU 配对实验（Paper 2）在事件模型稳定后
   启动。
5. 参与 OTel skill span 提案，发布事件模型单页规范。

## 7. 结论

定位不需要转向，需要锐化：从"一个看 Skill 运行的全景工具"锐化为
"回答'我的 Skill 到底干了什么、为什么没干、值不值'的证据层"。用
why-not-triggered 引爆传播，用边界失败率实证数据和配对归因实验支撑
两篇论文，用 OTel 提案钉死品类。行业的三股力量（生态爆发、安全焦虑、
归因研究兴起）都在把水推向本项目已经站住的位置；当前最大的风险不是
定位错，而是窗口期内声量不够。

## 8. 对焦状态（与 Codex 评审的收敛）

评审结论：约 70% 直接吸收、20% 修改后吸收、10% 暂缓。本文档 r2 已按此
收敛。

### 已直接吸收

- Panorama 是呈现形式，不是最终价值主张（§3.1）；
- 核心价值改为定位 first **observable** broken boundary（§3.1）；
- 三层能力改为 `Reconstruct → Diagnose → Evaluate`（§3.2）；
- 尽早实现少量可解释的诊断规则（§3.2 表）；
- 保留零配置 Historical Replay（见下）；设计默认脱敏可分享 Run Card；
- 参与 OTel Skill 遥测讨论（作为参与者）；优先推进 Paper 1。

### 修改后吸收

- SkillsBench / 恶意 Skill / Who&When / OTel 数字与表述已逐条校正（§1）；
- Behavior Profile 限定为 Tool-layer，标注 `Internal behavior unknown`（§3.3）；
- SkillScope 竞品描述与 novelty 表述已修正（§2、§1.2c）；
- OTel reference implementation 宣传改为"参与者 + 映射层"（§1.3、§3.4）。

### 暂缓

- 把"更高优先级 Skill 抢占"作为 Observed 事实（§3.2）；
- 自动运行未知第三方 Skill 的沙箱能力（§3.3）；
- 直接开展大规模 Paper 2 实验（§5.2，先 pilot）；
- 在 MVP 主标题中承诺回答 Skill 是否 "worth it"。

### 两种采集模式（评审补充，纳入传播与产品叙事）

- **Historical Replay**：默认零配置，读已有 session/transcript/本地文件，
  低侵入，能力不完整，适合快速体验与事后分析。
- **Live Instrumented**：用 Agent hooks/原生事件/OTLP，近实时上报，覆盖率
  更高，需显式配置，适合持续可观测。Rapid 看作 exporter 而非产品主语。

产品绝不得默认静默上传本地运行数据；论文/传播使用的真实运行数据必须区分
来源：opt-in 匿名数据、公开 transcript、受控实验、合成 fixture、单独授权的
企业数据。

## 9. 实验环境（PAI-DSW）

已确认可用算力环境并建立隔离工作目录：

| 项 | 值 |
|---|---|
| 主机 | PAI-DSW（ssh -p 24 root@47.97.34.14） |
| GPU | 1× NVIDIA H20，96GB 显存（推理型卡） |
| CPU / 内存 | 24 核 / 122GB RAM |
| 磁盘 | 911GB 可用 |
| Python | 3.12.13（无 uv，需自行安装环境） |
| 工作目录 | `/root/sri-xueping/`（experiments/data/models/logs/envs） |

约束：

- 仅在 `/root/sri-xueping/` 下工作，不触碰其他用户目录（如已存在的 `go`）。
- H20 是单卡且推理导向，适合 self-host 开源模型做 with/without 评测，不适合
  训练；呼应评审的"先 pilot"结论（§5.2）。
- 首次探测时显存已被占用 ≈90GB（利用率 0%，他人挂载），仅约 7GB 空闲；
  跑实验前需错峰或协调，避免影响他人。
- pilot 优先选可在 <7GB–单卡运行的中小模型，验证流程跑通后再扩规模。

## 10. 第三轮调研：再聚焦与实验驱动的产品设计

Snapshot: 2026-07-28（r3 轮）。本轮目标：用新证据再次收敛产品方向，并把
产品设计分歧转化为可在 PAI-DSW 上实验验证的假设。

### 10.1 新增关键事实（均有一手来源）

**(1) 两大 harness 都没有原生 Skill 生命周期 hook。**

- Claude Code hooks 是 tool/session 粒度（PreToolUse/PostToolUse/
  SessionStart 等；Agent SDK 扩展到更多事件，但部分事件在 agent 上下文
  不触发）。来源: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- Codex 的 `PreSkillUse/PostSkillUse` 仅是开放 issue
  （[openai/codex#17132](https://github.com/openai/codex/issues/17132)）。
- 推论：**没有任何 harness 会直接告诉你 Skill 发生了什么**。跨源重建
  （transcript + hooks + workspace）不是可选架构，而是唯一可行路径。
  这是产品核心命题的硬性地基，也是 Paper 1 "transcript-only vs
  hooks-only vs combined" 实验的直接动机。

**(2) Skill 注入是"隐藏 meta 消息"，且只改变 agent 的准备。**

首篇 Agent Skills 系统综述（[arXiv:2602.12430](https://arxiv.org/abs/2602.12430)，
浙江大学）确认：触发时 Skill 指令作为对模型可见、UI 不渲染的隐藏 meta
消息注入；"skill execution modifies the agent's preparation, not its
output directly"。两个直接后果：

- 激活证据对用户天然不可见 → "到底触发了没有"这个痛点是架构性的，
  不会随 harness 成熟自行消失；
- Skill 不产生直接输出 → "激活 ≠ 有效"有了机制层解释，支撑 Paper 2
  的核心叙事。

**(3) 学术界已把"验证 Skill 只做它声称的事"列为公开难题。**

同一综述的七大开放挑战中，Challenge 5（Skill Verification and Testing：
"confirming that a skill does what it claims and nothing more"）与
Challenge 7（评测方法学：现有 benchmark 只测任务完成，不测 Skill 质量）
直接对应本产品；其治理框架的 G4 环节——把"声明的权限清单"与"观测到的
运行时行为"比对——正是 Behavior Profile 的学术版本。社区也已出现同构
讨论（"runtime attestation compares the declared manifest against
observed behavior... and nobody is checking"）。本轮检索仍未发现任何已
发布的 Skill 运行时调试器产品（市面上的 "debug skills" 是用于调试代码的
Skill，不是调试 Skill 的工具）。

**(4) 触发问题有了更精确的结构。**

社区共识：description 是唯一触发机制（激活前 agent 只能看到
name+description）；失败分为 under-triggering 与 over-triggering 两类；
简单单步请求本就不应触发 Skill（agent 用基础工具处理是正确行为）——
印证"未观察到 ≠ 失败"原则。另有 Li 2026
（[arXiv:2601.04748](https://arxiv.org/abs/2601.04748)）发现 Skill 库规模
超过临界点后选择准确率陡降（phase transition）——"装太多 Skill 会互相
干扰"是可测量现象，产品可以直接把"库规模/重叠度"作为诊断维度。

**(5) 开发者信任危机支撑"审计理解"价值主张。**

Sonar State of Code 2026（1,149 名开发者）：96% 不完全信任 AI 代码的
功能正确性；另有调查显示 84% 日常使用但仅 29% 信任输出；最大挫败感是
"almost right, but not quite"。理解/审计工具的宏观需求在变强。

**(6) L3 Evaluate 层出现官方竞争信号。**

OpenAI 已发布 "Testing Agent Skills Systematically with Evals" 官方
指南。含义：纯离线 eval 工具会被官方生态覆盖；本产品的 L3 必须绑定自己
的独特资产——**把受控评测结果与运行时证据链关联**（eval 工具告诉你
分数，本产品告诉你分数差异发生在哪个生命周期边界）。

### 10.2 再聚焦：把产品锤定在 "Declared vs Observed" 差异上

综合三轮调研，最锐利、最难被替代的产品切入点是：

> **Skill 声明了什么（SKILL.md 元数据、allowed-tools、引用的 scripts/
> references） vs 运行时实际观察到什么——带证据分级的差异视图。**

它同时服务三个已验证的需求，且都是同一份数据的不同投影：

| 需求 | Declared vs Observed 的投影 |
|---|---|
| 调试（Skill 作者） | 声明的 reference 没被读、script 没被执行 → 第一个可观察断点 |
| 信任（采用者/安全） | 观察到声明之外的行为 → Behavior Profile 差异告警 |
| 评估（维护者/研究者） | 声明资源的实际利用率、跨运行一致性 → dead weight、漂移检测 |

相对 r2 的增量：这不是新方向，而是把"重建生命周期"的产出物从"全景图"
收敛为一个更可检验、更可传播的交付物：**每次运行产出一份
declared-vs-observed diff**（声明的每项能力标注 Observed / Not
observed / Unsupported + 声明外行为列表）。panorama、timeline、诊断
都是这份 diff 的展开视图。它同时是 Challenge 5/G4 的第一个可用实现，
论文叙事与产品交付物完全重合。

边界约束不变：只陈述可观察层（tool-layer），声明外行为的"未观察到"
不等于"没发生"；不拦截、不打分、不做安全网关。

### 10.3 实验驱动的产品设计：四级实验梯子

把产品设计分歧转化为可在 PAI-DSW（`/root/sri-xueping/`）上验证的假设。
每个实验同时回答一个产品设计问题和一个论文问题；失败也有价值（排除
方向）。

**E0 可观测性普查（CPU 即可，1–2 天）**

- 做法：在受控容器里用 Claude Code/Codex 跑同一组 Skill 任务，同时开
  transcript、全量 hooks、文件系统监控三路采集，逐事件比对三路覆盖。
- 产品问题：adapter capability matrix 里每个信号的真实覆盖率；哪些边界
  必须标 Unsupported。直接产出 `adapter-capability-matrix.md` 的实证版。
- 论文问题：H2（跨源 > 单源）的预实验数据。

**E1 触发边界普查（单卡小模型可跑，错峰）**

- 做法：固定一组任务 × 系统性变换 Skill 库配置（库大小 1/5/15/30、
  description 质量好/坏、同义 Skill 重叠度），测 under/over-triggering
  率与 Li 2026 的 phase transition 是否在真实 harness 中复现。
- 产品问题：why-not-triggered 诊断规则的先验概率——哪类原因占比最高，
  决定诊断 UI 的默认排序与文案；"库规模警告"是否值得做成功能。
- 论文问题：H1（静默失败分布）的受控版本。

**E2 Declared vs Observed 差异普查（核心，单卡可跑）**

- 做法：选 20–30 个真实公开 Skill（含 scripts/references），每个跑
  N 次匹配任务，统计：声明资源的实际加载率、声明外行为发生率、跨运行
  一致性。
- 产品问题：diff 视图的信噪比——如果大部分 Skill 的 diff 都非空，这就是
  首屏产品；如果普遍为空，diff 降级为诊断页的一个区块。同时产出首批
  可传播 headline number（"X% 的 Skill 运行未加载其声明的 reference"）。
- 论文问题：Challenge 5/G4 的首个实证数据；Paper 1 的核心表格。

**E3 with/without-Skill 配对 pilot（即 §5.2 的 pilot，排在 E0–E2 之后）**

- 做法不变（3–5 Skill × 2 harness × 2 模型 × 确定性 verifier），但新增
  一个产品导向目标：验证 E2 的 declared-vs-observed 信号能否预测配对
  效果差异（如"未加载声明资源的运行成功率更低"）。若成立，产品可在
  不跑 eval 的情况下给出校准过的风险提示（Inferred + 实验校准 basis）。
- verifier 基座复用 Terminal-Bench/SWE-bench 风格的确定性验证器。

顺序约束：E0 → E1/E2（可并行）→ E3。E0–E2 不依赖大显存，可在当前 7GB
空闲的环境里用中小模型启动；E3 需错峰。所有实验数据留在
`/root/sri-xueping/experiments/`，与产品遥测分离。

### 10.4 对产品文档的待评审建议（经本轮调研更新）

1. `product-definition.md` §5 的核心产品体验增加第 7 项：declared-vs-
   observed 差异摘要（待 E2 验证信噪比后定层级）。
2. `runtime-event-model.md` 考虑增加 `declaration.*` 实体（声明的
   allowed-tools/资源清单），使 diff 成为一等公民而非 UI 拼接。
3. `adapter-capability-matrix.md` 用 E0 结果替换为实证版，并明确标注
   "Codex 无原生 skill hook（见 openai/codex#17132）"作为能力依据。
4. Paper 1 叙事锚定："首个面向 Skill 生命周期的 declared-vs-observed
   运行时审计方法"（呼应综述 Challenge 5/7，引用其作为动机来源）。
