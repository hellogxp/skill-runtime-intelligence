(() => {
  "use strict";

  const STORAGE_KEY = "skill-runtime.locale";
  const SUPPORTED_LOCALES = [
    "en", "zh-CN", "zh-TW", "fr", "de", "it", "es", "ja", "ko", "ru",
    "pt-BR", "tr", "pl", "cs", "hu",
  ];
  const SUPPORTED = new Set(SUPPORTED_LOCALES);

  const zh = {
    "Evidence intelligence": "证据智能",
    "Product navigation": "产品导航",
    "Runs": "运行",
    "Skills": "技能",
    "Settings": "设置",
    "Reading adapters…": "正在读取适配器…",
    "Local · connecting": "本地 · 正在连接",
    "Refresh index view": "刷新索引视图",
    "Refresh": "刷新",
    "RUNTIME INDEX": "运行时索引",
    "Skill execution is primary. Agent sessions remain context.": "以 Skill 执行为主体，Agent 会话仅作为上下文。",
    "Filter Skill, project, adapter": "筛选 Skill、项目或适配器",
    "Run status filter": "运行状态筛选",
    "All": "全部",
    "Completed": "已完成",
    "Incomplete": "不完整",
    "Failed": "失败",
    "More filters": "更多筛选",
    "Agent": "Agent",
    "All Agents": "全部 Agent",
    "Project": "项目",
    "All projects": "全部项目",
    "Skill": "Skill",
    "All Skills": "全部 Skill",
    "All grades": "全部证据等级",
    "Date": "日期",
    "Has errors": "存在错误",
    "SKILL RUNTIME PANORAMA": "SKILL 运行全景",
    "Select a SkillRun": "选择一次 SkillRun",
    "Follow its lifecycle from request context through observable outcome.": "沿请求上下文追踪到可观察结果的完整生命周期。",
    "Observed": "已观察",
    "Derived": "派生",
    "Inferred": "推断",
    "Experimental": "实验",
    "Compare": "对比",
    "Delete index": "删除索引",
    "SkillRun summary": "SkillRun 摘要",
    "Evidence coverage": "证据覆盖率",
    "Activation mode": "激活方式",
    "Attributed events": "归因事件",
    "First evidence gap": "首个证据缺口",
    "absence is not failure": "缺少证据不等于失败",
    "EVIDENCE-AWARE COMPARE": "证据感知对比",
    "Run and adapter differences": "运行与适配器差异",
    "Select a SkillRun to compare": "选择要对比的 SkillRun",
    "Compare runs": "对比运行",
    "DIAGNOSTICS": "诊断",
    "Evidence-graded findings": "证据分级诊断",
    "LIFECYCLE GRAPH": "生命周期图",
    "Skill Runtime Panorama": "Skill 运行全景",
    "Source fact": "来源事实",
    "Lifecycle": "生命周期",
    "Live · semantic motion": "实时 · 语义流动",
    "Graph motion mode": "图流动模式",
    "Live": "实时",
    "Replay": "回放",
    "Static": "静态",
    "Fit start": "回到起点",
    "Skill runtime evidence graph": "Skill 运行时证据图",
    "EVIDENCE-BACKED RECONSTRUCTION": "证据支持的重建",
    "TRUSTED CHRONOLOGY": "可信时间线",
    "Runtime evidence": "运行时证据",
    "Filter timeline by lifecycle stage": "按生命周期阶段筛选时间线",
    "Filter timeline by event type": "按事件类型筛选时间线",
    "Filter timeline by Skill": "按 Skill 筛选时间线",
    "Filter timeline by evidence grade": "按证据等级筛选时间线",
    "All event types": "全部事件类型",
    "All stages": "全部阶段",
    "Request": "请求",
    "Discovery": "发现",
    "Activation": "激活",
    "Instructions": "指令",
    "Resources": "资源",
    "Execution": "执行",
    "Artifacts": "产物",
    "Outcome": "结果",
    "EVIDENCE INSPECTOR": "证据检查器",
    "Why this is attributed": "归因依据",
    "Select a lifecycle node or timeline event.": "选择生命周期节点或时间线事件。",
    "Source facts and attribution are shown separately.": "来源事实与归因关系分别展示。",
    "STATIC DEFINITION × RUNTIME EVIDENCE": "静态定义 × 运行时证据",
    "Skill Inventory": "Skill 清单",
    "What each Agent can discover, what is installed, and what has actually run.": "查看各 Agent 能发现什么、安装了什么，以及实际运行了什么。",
    "Filter name, source, description": "筛选名称、来源或描述",
    "Observed use": "已观察使用",
    "Not observed": "未观察到",
    "Select a Skill definition.": "选择一个 Skill 定义。",
    "Static inventory and runtime evidence remain distinct.": "静态清单与运行时证据保持分离。",
    "POTENTIAL TRIGGER OVERLAP": "潜在触发重叠",
    "Conflict candidates": "冲突候选",
    "Description overlap is a review aid, not proof that an Agent considered or confused two Skills.": "描述重叠仅用于辅助审查，不代表 Agent 曾考虑或混淆两个 Skill。",
    "COLLECTION, PRIVACY & INTEROPERABILITY": "采集、隐私与互操作",
    "Runtime Settings": "运行时设置",
    "See exactly what is connected, read, stored, and exported.": "准确查看已连接、读取、存储和导出的内容。",
    "Local control plane": "本地控制面",
    "AGENT ADAPTERS": "AGENT 适配器",
    "Collection health": "采集健康",
    "LOCAL EVIDENCE STORE": "本地证据存储",
    "Data & privacy": "数据与隐私",
    "PROJECT BOUNDARIES": "项目边界",
    "Included and excluded paths": "纳入与排除路径",
    "Save settings": "保存设置",
    "Included projects": "纳入的项目",
    "Never read or index": "永不读取或索引",
    "Retention days (blank = unlimited)": "保留天数（留空表示无限）",
    "Changes apply after restart. Retention removes only expired local index records, never Agent source files.": "更改将在重启后生效。保留策略只删除过期本地索引，绝不删除 Agent 来源文件。",
    "OBSERVABILITY EXPORT": "可观测性导出",
    "OTLP/HTTP destinations": "OTLP/HTTP 目标",
    "Opt-in": "主动启用",
    "Exports contain normalized Skill evidence and categorical metadata, never raw prompts or tool payloads.": "仅导出标准化 Skill 证据与分类元数据，不导出原始提示词或工具载荷。",
    "Native telemetry": "原生遥测",
    "Official hook": "官方 Hook",
    "Lightweight hook": "轻量 Hook",
    "Runtime SDK": "运行时 SDK",
    "Transcript fallback": "会话日志回退",
    "Imported trace": "导入的 Trace",
    "No runtime source indexed": "尚未索引运行时来源",
    "Runtime integrations available": "运行时集成可用",
    "Collector unavailable": "Collector 不可用",
    "Local · polling fallback": "本地 · 轮询回退",
    "Local · live": "本地 · 实时",
    "Local · reconnecting": "本地 · 正在重连",
    "Untitled runtime context": "未命名运行上下文",
    "No matching SkillRuns.": "没有匹配的 SkillRun。",
    "Sessions without Skill evidence are intentionally excluded.": "没有 Skill 证据的会话会被主动排除。",
    "Installed definitions": "已安装定义",
    "Static files indexed": "已索引静态文件",
    "Observed at runtime": "运行时已观察",
    "Direct or derived SkillRuns": "直接或派生的 SkillRun",
    "Definition variants": "定义变体",
    "Name + digest identities": "名称与摘要标识",
    "Needs attention": "需要关注",
    "Malformed or incomplete metadata": "格式错误或元数据不完整",
    "No description": "无描述",
    "No matching Skills.": "没有匹配的 Skill。",
    "Adjust the filter or installation roots.": "请调整筛选条件或安装根目录。",
    "No activation is observed. This does not prove the Agent rejected the Skill; candidate matching is unsupported unless the Agent emits that signal.": "未观察到激活。这不代表 Agent 拒绝了该 Skill；除非 Agent 发出候选匹配信号，否则无法观察这一判断。",
    "No description declared.": "未声明描述。",
    "Definition identity": "定义标识",
    "Version": "版本",
    "Digest": "摘要",
    "Source": "来源",
    "Path": "路径",
    "Compatibility": "兼容性",
    "Validation": "校验",
    "Valid": "有效",
    "Declared resources": "声明的资源",
    "No scripts, references, or assets declared.": "未声明脚本、参考资料或资产。",
    "Runtime diagnosis": "运行时诊断",
    "Observed Agents": "已观察 Agent",
    "Failed runs": "失败运行",
    "Last observed": "最后观察时间",
    "Variants": "变体",
    "Definition comparison": "定义对比",
    "Compare with": "对比对象",
    "No same-name definition variant is installed. Cross-version impact cannot be assessed from a single definition.": "未安装同名定义变体，无法从单一定义评估跨版本影响。",
    "Definitions are byte-identical.": "定义逐字节一致。",
    "Evidence": "证据",
    "Changed": "变更",
    "No high-overlap candidates.": "没有高重叠候选。",
    "This is not proof that conflicts cannot occur.": "这不代表冲突一定不会发生。",
    "Detected · runtime collection consent not granted": "已检测 · 尚未同意运行时采集",
    "Agent not detected on this machine": "本机未检测到 Agent",
    "Pending": "待验证",
    "Available": "可用",
    "Absent": "不存在",
    "Stored size": "存储大小",
    "Evidence events": "证据事件",
    "Retention": "保留策略",
    "Model proxy": "模型代理",
    "Raw prompt export": "原始提示词导出",
    "Enabled": "已启用",
    "Never": "从不",
    "Deleting a SkillRun removes only this SQLite index. Agent source transcripts remain untouched.": "删除 SkillRun 只会移除 SQLite 索引，不会修改 Agent 来源会话。",
    "Retrying": "正在重试",
    "No network exporter configured.": "尚未配置网络导出器。",
    "Start with --otlp-endpoint or OTEL_EXPORTER_OTLP_ENDPOINT.": "请使用 --otlp-endpoint 或 OTEL_EXPORTER_OTLP_ENDPOINT 启动。",
    "Unable to save settings": "无法保存设置",
    "Saved. Restart Skill Runtime to apply collection boundaries and retention.": "已保存。重启 Skill Runtime 后应用采集边界和保留策略。",
    "Unable to delete SkillRun index": "无法删除 SkillRun 索引",
    "Runtime-observed Skill": "运行时观察到的 Skill",
    "session context": "会话上下文",
    "model unavailable": "模型不可用",
    "No gap": "无缺口",
    "No comparable difference": "没有可比差异",
    "Unclassified tool": "未分类工具",
    "The active adapter does not expose this lifecycle boundary.": "当前适配器不提供此生命周期边界。",
    "Stage coverage is reconstructed from normalized runtime records. It is not a claim that the stage caused the next stage.": "阶段覆盖由标准化运行记录重建，不代表该阶段导致了下一阶段。",
    "These source events were normalized into this lifecycle stage.": "这些来源事件已标准化到此生命周期阶段。",
    "Lifecycle continuation for navigation only; it is not a causal claim.": "生命周期延续仅用于导航，不构成因果声明。",
    "Declared Skill lifecycle order; absence or adjacency does not establish causality.": "声明的 Skill 生命周期顺序；缺失或相邻关系不能建立因果性。",
    "Open frontier is derived from an observed tool start without a matching terminal event. It remains open until a terminal source event closes it.": "开放前沿由已观察到但没有终止事件的工具启动派生，直到来源终止事件将其关闭。",
    "This SkillRun has no recorded terminal event. The latest observed boundary remains an open frontier; this does not prove a process is currently executing.": "此 SkillRun 没有记录终止事件。最后观察到的边界保持开放，但这不代表进程仍在执行。",
    "Live · open frontier + new evidence": "实时 · 开放前沿与新证据",
    "Replay · reconstructed event flow": "回放 · 重建事件流",
    "Static · motion disabled": "静态 · 已关闭流动",
    "No Skill relationship is recorded for this context event.": "此上下文事件没有记录 Skill 关系。",
    "No evidence in this stage.": "此阶段没有证据。",
    "This is not classified as a failure.": "这不会被归类为失败。",
    "run context": "运行上下文",
    "Status": "状态",
    "Basis": "依据",
    "Locator": "定位信息",
    "Skill attribution": "Skill 归因",
    "Relationship": "关系",
    "Grade": "等级",
    "Redacted payload": "脱敏载荷",
    "Show redacted normalized JSON": "查看脱敏后的标准化 JSON",
    "Lifecycle stage": "生命周期阶段",
    "Observability": "可观测性",
    "Events": "事件",
    "Capability": "能力",
    "Interpretation": "解释",
    "This adapter cannot observe this lifecycle boundary. No conclusion is made.": "此适配器无法观察该生命周期边界，因此不作结论。",
    "The adapter could observe this signal, but no matching evidence was found. This is a gap, not proof of failure.": "适配器能够观察该信号，但没有找到匹配证据。这是证据缺口，不是失败证明。",
    "Unable to read the local index.": "无法读取本地索引。",
    "not declared": "未声明",
    "none": "无",
    "unknown": "未知",
    "unlimited": "无限",
    "observed": "已观察",
    "derived": "派生",
    "inferred": "推断",
    "experimental": "实验",
    "unsupported": "不支持",
    "not observed": "未观察到",
    "not_observed": "未观察到",
    "completed": "已完成",
    "failed": "失败",
    "incomplete": "不完整",
    "interrupted": "已中断",
    "explicit tool": "显式工具",
    "explicit_tool": "显式工具",
    "automatic": "自动",
    "nested": "嵌套",
    "direct": "直接",
    "partial": "部分",
    "Language": "语言",
    "Interface language": "界面语言",
  };

  const zhPatterns = [
    [/^(\d+) Skills$/, "$1 个 Skill"],
    [/^(\d+) runs · (\d+) resources$/, "$1 次运行 · $2 个资源"],
    [/^(\d+)% · (\d+) events$/, "$1% · $2 个事件"],
    [/^Evidence coverage (\d+)%$/, "证据覆盖率 $1%"],
    [/^(\d+) primary$/, "$1 个主要来源"],
    [/^(\d+) fallback$/, "$1 个回退来源"],
    [/^(\d+) imports?$/, "$1 个导入来源"],
    [/^(\d+) live integrations?$/, "$1 个实时集成"],
    [/^(\d+) integrations? pending$/, "$1 个集成待验证"],
    [/^(\d+) SkillRun\(s\) contain activation or instruction evidence\.$/, "$1 个 SkillRun 包含激活或指令证据。"],
    [/^(\d+) installed definition\(s\)$/, "$1 个已安装定义"],
    [/^(\d+) metadata field\(s\) differ\.$/, "$1 个元数据字段不同。"],
    [/^(\d+)% term overlap$/, "$1% 术语重叠"],
    [/^(\d+) runtime events · live evidence verified · fail-open$/, "$1 个运行时事件 · 实时证据已验证 · fail-open"],
    [/^(\d+) events configured · awaiting Agent restart\/trust or a new run$/, "$1 个事件已配置 · 等待 Agent 重启、信任或新运行"],
    [/^(\d+) exported · (\d+) failed$/, "已导出 $1 · 失败 $2"],
    [/^(\d+) attribution edges$/, "$1 条归因边"],
    [/^(\d+) evidence records$/, "$1 条证据记录"],
    [/^(\d+) evidence record\(s\) support this lifecycle stage\.$/, "$1 条证据记录支持此生命周期阶段。"],
    [/^No comparable (.+) run$/, "没有可对比的 $1 运行"],
  ];

  const patternRules = [
    [/^(\d+) Skills$/, "skills_count", ["count"]],
    [/^(\d+) runs · (\d+) resources$/, "runs_resources", ["runs", "resources"]],
    [/^(\d+)% · (\d+) events$/, "percent_events", ["percent", "events"]],
    [/^Evidence coverage (\d+)%$/, "evidence_coverage", ["percent"]],
    [/^(\d+) primary$/, "primary_count", ["count"]],
    [/^(\d+) fallback$/, "fallback_count", ["count"]],
    [/^(\d+) imports?$/, "import_count", ["count"]],
    [/^(\d+) live integrations?$/, "live_integration_count", ["count"]],
    [/^(\d+) integrations? pending$/, "pending_integration_count", ["count"]],
    [/^(\d+) SkillRun\(s\) contain activation or instruction evidence\.$/, "activation_run_count", ["count"]],
    [/^(\d+) installed definition\(s\)$/, "definition_count", ["count"]],
    [/^(\d+) metadata field\(s\) differ\.$/, "metadata_difference_count", ["count"]],
    [/^(\d+)% term overlap$/, "overlap_percent", ["percent"]],
    [/^(\d+) runtime events · live evidence verified · fail-open$/, "runtime_events", ["count"]],
    [/^(\d+) events configured · awaiting Agent restart\/trust or a new run$/, "configured_events", ["count"]],
    [/^(\d+) exported · (\d+) failed$/, "exported_failed", ["exported", "failed"]],
    [/^(\d+) attribution edges$/, "attribution_edges", ["count"]],
    [/^(\d+) evidence records$/, "evidence_records", ["count"]],
    [/^(\d+) evidence record\(s\) support this lifecycle stage\.$/, "stage_records", ["count"]],
    [/^No comparable (.+) run$/, "no_comparable_run", ["status"]],
  ];

  function normalizeLocale(value) {
    if (SUPPORTED.has(value)) return value;
    const normalized = String(value || "").replace("_", "-");
    const lower = normalized.toLowerCase();
    if (lower === "zh-tw" || lower === "zh-hk" || lower === "zh-mo" || lower.includes("hant")) {
      return "zh-TW";
    }
    if (lower.startsWith("zh")) return "zh-CN";
    if (lower.startsWith("pt")) return "pt-BR";
    const base = lower.split("-")[0];
    return SUPPORTED.has(base) ? base : "en";
  }

  const locale = normalizeLocale(
    window.localStorage.getItem(STORAGE_KEY) || navigator.language
  );

  function preserveWhitespace(original, translated) {
    const leading = original.match(/^\s*/)?.[0] || "";
    const trailing = original.match(/\s*$/)?.[0] || "";
    return `${leading}${translated}${trailing}`;
  }

  function translateText(value) {
    if (locale === "en" || typeof value !== "string") return value;
    const trimmed = value.trim();
    if (!trimmed) return value;
    const pack = window.SkillRuntimeLocalePacks?.[locale];
    let translated = locale === "zh-CN"
      ? zh[trimmed]
      : pack?.messages?.[trimmed];
    if (!translated && locale === "zh-CN") {
      for (const [pattern, replacement] of zhPatterns) {
        if (pattern.test(trimmed)) {
          translated = trimmed.replace(pattern, replacement);
          break;
        }
      }
    } else if (!translated && pack?.patterns) {
      for (const [pattern, key, fields] of patternRules) {
        const match = trimmed.match(pattern);
        if (!match) continue;
        translated = pack.patterns[key];
        fields.forEach((field, index) => {
          const raw = match[index + 1];
          const replacement = field === "status" ? translateText(raw).trim() : raw;
          translated = translated.replaceAll(`{${field}}`, replacement);
        });
        break;
      }
    }
    return translated ? preserveWhitespace(value, translated) : value;
  }

  function translateElement(element) {
    for (const attribute of ["placeholder", "aria-label", "title"]) {
      if (!element.hasAttribute?.(attribute)) continue;
      const current = element.getAttribute(attribute);
      const translated = translateText(current);
      if (translated !== current) element.setAttribute(attribute, translated);
    }
  }

  function apply(root = document) {
    if (locale === "en") return;
    if (root.nodeType === Node.TEXT_NODE) {
      const translated = translateText(root.nodeValue);
      if (translated !== root.nodeValue) root.nodeValue = translated;
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) {
      return;
    }
    if (root.nodeType === Node.ELEMENT_NODE) translateElement(root);
    const walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT
    );
    let node = walker.nextNode();
    while (node) {
      if (node.nodeType === Node.TEXT_NODE) {
        const translated = translateText(node.nodeValue);
        if (translated !== node.nodeValue) node.nodeValue = translated;
      } else {
        translateElement(node);
      }
      node = walker.nextNode();
    }
  }

  function init() {
    document.documentElement.lang = locale;
    const selector = document.querySelector("#locale-select");
    if (selector) {
      selector.value = locale;
      selector.addEventListener("change", () => {
        window.localStorage.setItem(
          STORAGE_KEY,
          normalizeLocale(selector.value)
        );
        window.location.reload();
      });
    }
    apply(document);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => apply(node));
      }
    });
    observer.observe(document.body, {childList: true, subtree: true});
  }

  window.SkillRuntimeI18n = {
    locale,
    supportedLocales: [...SUPPORTED_LOCALES],
    translateText,
    apply,
  };
  document.addEventListener("DOMContentLoaded", init, {once: true});
})();
