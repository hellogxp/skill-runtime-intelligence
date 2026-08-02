const stageLabels = {
  request: "Request",
  discovery: "Discovery",
  activation: "Activation",
  instructions: "Instructions",
  resources: "Resources",
  execution: "Execution",
  artifacts: "Artifacts",
  outcome: "Outcome",
};
const stageOrder = Object.keys(stageLabels);

let skillRuns = [];
let selectedRunId = null;
let selectedRun = null;
let statusFilter = "all";
let selectedGraphNodeId = null;
let currentGraph = null;
let graphMotionMode = "live";
let graphReplayRequested = false;
let runtimeSources = [];
let runtimeIntegrations = [];
let skillInventory = [];
let skillConflicts = [];
let runtimeSettings = null;
let runtimeExporters = [];
let selectedSkillId = null;
let activeView = "runs";
let selectedComparisonId = null;
let streamConnected = false;
let streamRefreshTimer = null;
let streamRefreshInFlight = false;
let lastStreamRefreshAt = 0;
const STREAM_REFRESH_INTERVAL_MS = 1500;
const graphEventHistory = new Map();

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const tr = (value) => window.SkillRuntimeI18n?.translateText(String(value)) || String(value);

const formatTime = (value, includeDate = true) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return String(value);
  const locale = window.SkillRuntimeI18n?.locale || undefined;
  return includeDate
    ? date.toLocaleString(locale, {month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit"})
    : date.toLocaleTimeString(locale, {hour: "2-digit", minute: "2-digit", second: "2-digit"});
};

const pretty = (value) => String(value || "unknown").replaceAll("_", " ");
const percentBucket = (value) => Math.max(
  0,
  Math.min(100, Math.round((Number(value) || 0) / 10) * 10),
);

async function getJSON(path) {
  const response = await fetch(path, {cache: "no-store"});
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function loadIndex(isBackground = false) {
  if (!selectedRunId && location.hash.startsWith("#/runs/")) {
    selectedRunId = decodeURIComponent(location.hash.slice("#/runs/".length));
  }
  const previousSelected = skillRuns.find((run) => run.skill_run_id === selectedRunId);
  if (isBackground) {
    const runsResponse = await getJSON("/api/skill-runs");
    skillRuns = runsResponse.skill_runs || [];
    populateRunFilters();
    renderRuns();
    renderRuntimeOverview();
    const currentSelected = skillRuns.find((run) => run.skill_run_id === selectedRunId);
    const previousSignature = previousSelected
      ? `${previousSelected.event_count}:${previousSelected.status}:${previousSelected.evidence_completeness}`
      : "";
    const currentSignature = currentSelected
      ? `${currentSelected.event_count}:${currentSelected.status}:${currentSelected.evidence_completeness}`
      : "";
    if (
      currentSelected
      && currentSignature !== previousSignature
      && activeView === "runs"
      && location.hash.startsWith("#/runs")
    ) {
      await loadSkillRun(selectedRunId);
    }
    return;
  }
  const detailPromise = selectedRunId
    ? getJSON(`/api/skill-runs/${encodeURIComponent(selectedRunId)}`)
    : Promise.resolve(null);
  const requestedRunId = selectedRunId;
  const earlyDetailPromise = detailPromise.then((detail) => {
    if (
      detail
      && requestedRunId === selectedRunId
      && location.hash.startsWith("#/runs/")
      && decodeURIComponent(location.hash.slice("#/runs/".length)) === requestedRunId
    ) {
      showSkillRunDetail(detail);
    }
    return detail;
  });
  // Agent binary/version inspection can take seconds on a cold host. It is
  // useful header/settings metadata, not a prerequisite for the run index or
  // detail diagnosis, so keep it out of the critical rendering path.
  const integrationsPromise = getJSON("/api/integrations")
    .catch(() => ({integrations: []}));
  const [
    runsResponse,
    sourcesResponse,
    skillsResponse,
    conflictsResponse,
    settingsResponse,
    exportersResponse,
    initialDetail,
  ] = await Promise.all([
    getJSON("/api/skill-runs"),
    getJSON("/api/sources"),
    getJSON("/api/skills"),
    getJSON("/api/skill-conflicts"),
    getJSON("/api/settings"),
    getJSON("/api/exporters"),
    earlyDetailPromise,
  ]);
  skillRuns = runsResponse.skill_runs || [];
  runtimeSources = sourcesResponse.sources || [];
  skillInventory = skillsResponse.skills || [];
  skillConflicts = conflictsResponse.conflicts || [];
  runtimeSettings = settingsResponse;
  runtimeExporters = exportersResponse.exporters || [];
  populateRunFilters();
  renderSourceSummary();
  renderRuns();
  renderRuntimeOverview();
  renderSkills();
  renderSettings();
  if (initialDetail && selectedRun?.skill_run_id !== initialDetail.skill_run_id) {
    showSkillRunDetail(initialDetail);
  } else if (initialDetail) {
    renderComparePicker(initialDetail);
  }
  routeFromLocation();
  integrationsPromise.then((integrationsResponse) => {
    runtimeIntegrations = integrationsResponse.integrations || [];
    renderSourceSummary();
    renderSettings();
  });
}

function sourceModeLabel(mode) {
  return {
    native_telemetry: "Native telemetry",
    official_hook: "Official hook",
    lightweight_hook: "Lightweight hook",
    sdk: "Runtime SDK",
    transcript_fallback: "Transcript fallback",
    observability_import: "Imported trace",
  }[mode] || pretty(mode);
}

function renderSourceSummary() {
  const summary = document.querySelector("#source-summary");
  if (!runtimeSources.length) {
    const available = runtimeIntegrations.find(
      (integration) => integration.detected && integration.config_valid
    );
    summary.textContent = available
      ? `${available.installed ? "Hook enabled" : "Hook available"} · No runtime source`
      : "No runtime source indexed";
    summary.title = available
      ? "The Agent integration was detected; runtime evidence appears after a new Agent event."
      : "Start the Collector or index a supported Agent source.";
    return;
  }
  const primary = runtimeSources.filter((source) => source.role === "primary");
  const fallback = runtimeSources.filter((source) => source.role === "fallback");
  const imports = runtimeSources.filter((source) => source.role === "import");
  const parts = [];
  if (primary.length) parts.push(tr(`${primary.length} primary`));
  if (fallback.length) parts.push(tr(`${fallback.length} fallback`));
  if (imports.length) {
    parts.push(tr(`${imports.length} import${imports.length === 1 ? "" : "s"}`));
  }
  const detectedIntegrations = runtimeIntegrations.filter(
    (integration) => integration.detected
  );
  const installedIntegrations = detectedIntegrations.filter(
    (integration) => integration.installed
  );
  const verifiedIntegrations = installedIntegrations.filter(
    (integration) => integration.connection_status === "verified"
  );
  if (verifiedIntegrations.length) parts.push(tr(`${verifiedIntegrations.length} live integration`));
  else if (installedIntegrations.length) parts.push(tr(`${installedIntegrations.length} integration pending`));
  else if (detectedIntegrations.length) parts.push(tr("Runtime integrations available"));
  summary.textContent = parts.join(" · ");
  const sourceDetails = runtimeSources.map((source) =>
    `${source.adapter} ${source.adapter_version} — ${sourceModeLabel(source.collection_mode)}; ${source.event_count} events; ${source.source_health}`
  );
  detectedIntegrations.forEach((integration) => {
    sourceDetails.push(
      integration.connection_status === "verified"
        ? `${integration.agent} runtime integration verified by live evidence: ${(integration.installed_events || []).join(", ")}`
        : integration.installed
          ? `${integration.agent} runtime integration configured but not yet verified; restart the Agent and start a new turn.`
        : `${integration.agent} runtime integration is available but requires explicit consent.`
    );
  });
  summary.title = sourceDetails.join("\n");
}

function setConnectionState(state, label) {
  const connection = document.querySelector("#connection-state");
  connection.classList.toggle("degraded", state !== "live");
  connection.classList.toggle("offline", state === "offline");
  connection.querySelector("span").textContent = label;
}

function scheduleStreamRefresh() {
  window.clearTimeout(streamRefreshTimer);
  const elapsed = Date.now() - lastStreamRefreshAt;
  const delay = Math.max(150, STREAM_REFRESH_INTERVAL_MS - elapsed);
  streamRefreshTimer = window.setTimeout(() => {
    if (document.visibilityState !== "visible") return;
    if (streamRefreshInFlight) {
      scheduleStreamRefresh();
      return;
    }
    streamRefreshInFlight = true;
    loadIndex(true)
      .then(() => {
        lastStreamRefreshAt = Date.now();
      })
      .catch(() => setConnectionState("offline", "Collector unavailable"))
      .finally(() => {
        streamRefreshInFlight = false;
      });
  }, delay);
}

function connectRuntimeStream() {
  if (!window.EventSource) {
    setConnectionState("fallback", "Local · polling fallback");
    return;
  }
  const stream = new EventSource("/api/stream");
  stream.addEventListener("open", () => {
    streamConnected = true;
    setConnectionState("live", "Local · live");
  });
  stream.addEventListener("revision", scheduleStreamRefresh);
  stream.addEventListener("error", () => {
    streamConnected = false;
    setConnectionState("fallback", "Local · reconnecting");
  });
}

function visibleRuns() {
  const query = document.querySelector("#run-filter").value.toLowerCase().trim();
  const agent = document.querySelector("#run-agent-filter").value;
  const project = document.querySelector("#run-project-filter").value;
  const skill = document.querySelector("#run-skill-filter").value;
  const grade = document.querySelector("#run-grade-filter").value;
  const date = document.querySelector("#run-date-filter").value;
  const errorsOnly = document.querySelector("#run-error-filter").checked;
  return skillRuns.filter((run) => {
    const matchesStatus = statusFilter === "all" || run.status === statusFilter;
    const haystack = [
      run.name, run.description, run.session_title, run.cwd, run.adapter,
      run.model, run.activation_mode,
    ].join(" ").toLowerCase();
    return matchesStatus
      && (!agent || run.adapter === agent)
      && (!project || run.cwd === project)
      && (!skill || run.name === skill)
      && (!grade || run.evidence_grade === grade)
      && (!date || String(run.started_at || "").slice(0, 10) === date)
      && (!errorsOnly || Number(run.error_count) > 0 || run.status === "failed")
      && (!query || haystack.includes(query));
  });
}

function fillSelect(id, values, emptyLabel) {
  const select = document.querySelector(id);
  const previous = select.value;
  const normalized = [...new Set(values.filter(Boolean))].sort((left, right) =>
    String(left).localeCompare(String(right), window.SkillRuntimeI18n?.locale)
  );
  select.innerHTML = `<option value="">${esc(emptyLabel)}</option>${normalized.map((value) =>
    `<option value="${esc(value)}">${esc(pretty(value))}</option>`
  ).join("")}`;
  select.value = normalized.includes(previous) ? previous : "";
}

function populateRunFilters() {
  fillSelect("#run-agent-filter", skillRuns.map((run) => run.adapter), "All Agents");
  fillSelect("#run-project-filter", skillRuns.map((run) => run.cwd), "All projects");
  fillSelect("#run-skill-filter", skillRuns.map((run) => run.name), "All Skills");
  fillSelect("#run-grade-filter", skillRuns.map((run) => run.evidence_grade), "All grades");
}

function renderRuns() {
  const visible = visibleRuns();
  document.querySelector("#run-count").textContent = visible.length;
  document.querySelector("#runs").innerHTML = visible.map((run) => `
    <button class="run-card ${esc(run.status)} ${selectedRunId === run.skill_run_id ? "active" : ""}"
            type="button" data-run="${esc(run.skill_run_id)}">
      <div class="card-top">
        <span class="card-source">${esc(run.adapter)} · ${esc(tr(pretty(run.activation_mode)))}</span>
        <span class="card-time">${esc(formatTime(run.started_at))}</span>
      </div>
      <h3>${esc(run.name)}</h3>
      <p class="card-task">${esc(run.session_title || "Untitled runtime context")}</p>
      <div class="card-foot">
        <div class="mini-coverage" title="Evidence coverage ${esc(run.evidence_completeness)}%">
          <i class="fill-pct-${percentBucket(run.evidence_completeness)}"></i>
        </div>
        <span>${esc(run.evidence_completeness)}% · ${esc(run.event_count)} events</span>
      </div>
    </button>
  `).join("") || `<div class="empty-inspector"><p>No matching SkillRuns.</p><small>Sessions without Skill evidence are intentionally excluded.</small></div>`;
  document.querySelectorAll(".run-card").forEach((button) => {
    button.addEventListener("click", () => loadSkillRun(button.dataset.run, true));
  });
}

function renderRuntimeOverview() {
  const metrics = document.querySelector("#overview-metrics");
  if (!metrics) return;
  const boundaryCounts = Object.fromEntries(stageOrder.map((stage) => [stage, 0]));
  for (const run of skillRuns) {
    if (run.first_gap && Object.hasOwn(boundaryCounts, run.first_gap)) {
      boundaryCounts[run.first_gap] += 1;
    }
  }
  const dominant = Object.entries(boundaryCounts)
    .sort((left, right) => right[1] - left[1])[0] || [null, 0];
  const runsWithBoundary = Object.values(boundaryCounts).reduce((sum, count) => sum + count, 0);
  const dominantShare = runsWithBoundary
    ? Math.round((dominant[1] / runsWithBoundary) * 100)
    : 0;
  const systemicBoundary = dominant[1] >= 5 && dominantShare >= 80
    ? dominant[0]
    : null;
  const attention = skillRuns.filter((run) => (
    Number(run.error_count) > 0
    || ["failed", "incomplete", "interrupted"].includes(run.status)
    || (run.first_gap && run.first_gap !== systemicBoundary)
  ));
  attention.sort((left, right) => {
    const leftBoundary = left.first_gap ? stageOrder.indexOf(left.first_gap) : stageOrder.length;
    const rightBoundary = right.first_gap ? stageOrder.indexOf(right.first_gap) : stageOrder.length;
    if (leftBoundary !== rightBoundary) return leftBoundary - rightBoundary;
    if (Number(right.error_count) !== Number(left.error_count)) {
      return Number(right.error_count) - Number(left.error_count);
    }
    return String(right.started_at || "").localeCompare(String(left.started_at || ""));
  });
  const liveSources = runtimeIntegrations.filter(
    (item) => item.connection_status === "verified" || item.live_evidence_seen
  ).length;
  metrics.innerHTML = [
    ["Indexed SkillRuns", skillRuns.length, "Observed and derived runtime records"],
    ["Need attention", attention.length, "Boundary-first, not severity-first"],
    [
      "Coverage concentration",
      dominant[1] ? `${dominantShare}% ${stageLabels[dominant[0]]}` : "No systemic gap",
      dominant[1] ? "Derived across runs; not a root-cause claim" : "No repeated boundary in the current index",
    ],
    ["Verified runtime sources", liveSources, `${runtimeIntegrations.length} integrations detected`],
  ].map(([label, value, note]) => `
    <article>
      <span>${esc(label)}</span>
      <strong>${esc(value)}</strong>
      <small>${esc(note)}</small>
    </article>
  `).join("");

  const maxBoundary = Math.max(1, ...Object.values(boundaryCounts));
  document.querySelector("#boundary-distribution").innerHTML = stageOrder.map((stage) => {
    const count = boundaryCounts[stage];
    const width = Math.round((count / maxBoundary) * 100);
    const widthBucket = percentBucket(width);
    return `
      <div class="boundary-row">
        <span>${esc(stageLabels[stage])}</span>
        <div class="boundary-track"><i class="fill-pct-${widthBucket}"></i></div>
        <strong>${count}</strong>
      </div>`;
  }).join("");

  const queue = attention.slice(0, 8);
  document.querySelector("#attention-count").textContent = attention.length;
  document.querySelector("#attention-queue").innerHTML = queue.length
    ? queue.map((run) => `
      <button type="button" class="attention-item" data-overview-run="${esc(run.skill_run_id)}">
        <span class="attention-boundary">
          ${esc(run.first_gap ? stageLabels[run.first_gap] : pretty(run.status))}
        </span>
        <span class="attention-copy">
          <strong>${esc(run.name)}</strong>
          <small>${esc(run.adapter)} · ${esc(run.session_title || "Runtime context")}</small>
        </span>
        <span class="attention-evidence">
          ${esc(run.evidence_completeness)}%
          <small>${esc(formatTime(run.started_at))}</small>
        </span>
      </button>
    `).join("")
    : `
      <div class="overview-clear">
        <span class="healthy-dot"></span>
        <div><strong>No SkillRun currently needs attention</strong>
        <small>The system abstains when no evidence-bounded concern is available.</small></div>
      </div>`;
  document.querySelectorAll("[data-overview-run]").forEach((button) => {
    button.addEventListener("click", () => loadSkillRun(button.dataset.overviewRun, true));
  });
}

function setView(view, navigate = false) {
  activeView = ["runs", "skills", "settings"].includes(view) ? view : "runs";
  document.querySelector("#runs-view").classList.toggle("hidden", activeView !== "runs");
  document.querySelector("#skills-view").classList.toggle("hidden", activeView !== "skills");
  document.querySelector("#settings-view").classList.toggle("hidden", activeView !== "settings");
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === activeView);
  });
  if (navigate) {
    const hash = activeView === "runs" ? "#/runs" : `#/${activeView}`;
    history.pushState({}, "", hash);
  }
  if (activeView === "skills") renderSkills();
  if (activeView === "settings") renderSettings();
  window.scrollTo({top: 0, behavior: "smooth"});
}

function routeFromLocation() {
  if (location.hash.startsWith("#/runs/")) {
    setView("runs", false);
    return;
  }
  if (location.hash === "#/skills") {
    setView("skills", false);
    return;
  }
  if (location.hash === "#/settings") {
    setView("settings", false);
    return;
  }
  setView("runs", false);
}

function visibleSkills() {
  const filter = document.querySelector("#skill-filter")?.value.toLowerCase().trim() || "";
  return skillInventory.filter((skill) => !filter || [
    skill.name,
    skill.description,
    skill.source_path,
    skill.source_kind,
    skill.version,
  ].join(" ").toLowerCase().includes(filter));
}

function renderSkills() {
  if (!document.querySelector("#skill-list")) return;
  const visible = visibleSkills();
  const observed = skillInventory.filter((skill) => skill.observed_runs > 0).length;
  const invalid = skillInventory.filter((skill) => !skill.valid).length;
  const versions = new Set(
    skillInventory.map((skill) => `${skill.name}:${skill.digest}`)
  ).size;
  document.querySelector("#skill-count").textContent = `${skillInventory.length} Skills`;
  document.querySelector("#skill-metrics").innerHTML = [
    ["Installed definitions", skillInventory.length, "Static files indexed"],
    ["Observed at runtime", observed, "Direct or derived SkillRuns"],
    ["Definition variants", versions, "Name + digest identities"],
    ["Needs attention", invalid, "Malformed or incomplete metadata"],
  ].map(([label, value, note]) => `
    <article><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>
  `).join("");
  document.querySelector("#skill-list").innerHTML = visible.map((skill) => `
    <button type="button" class="skill-card ${skill.skill_id === selectedSkillId ? "active" : ""}"
            data-skill="${esc(skill.skill_id)}">
      <span class="skill-state ${skill.observed_runs ? "observed" : "not-observed"}"></span>
      <span class="skill-card-main">
        <span class="skill-card-top">
          <strong>${esc(skill.name)}</strong>
          <i>${esc(skill.version || skill.digest.slice(0, 8))}</i>
        </span>
        <small>${esc(skill.description || skill.validation_message || "No description")}</small>
        <span class="skill-card-meta">${esc(skill.source_kind)} · ${esc(skill.observed_runs)} runs · ${
          esc(skill.resources.length)
        } resources</span>
      </span>
    </button>
  `).join("") || `<div class="empty-inspector"><p>No matching Skills.</p><small>Adjust the filter or installation roots.</small></div>`;
  document.querySelectorAll(".skill-card").forEach((button) => {
    button.addEventListener("click", () => inspectSkill(button.dataset.skill));
  });
  renderConflicts();
  if (selectedSkillId && skillInventory.some((skill) => skill.skill_id === selectedSkillId)) {
    inspectSkill(selectedSkillId, false);
  }
}

function inspectSkill(skillId, rerender = true) {
  selectedSkillId = skillId;
  const skill = skillInventory.find((item) => item.skill_id === skillId);
  if (!skill) return;
  if (rerender) renderSkills();
  const sameName = skillInventory.filter(
    (item) => item.name.toLowerCase() === skill.name.toLowerCase()
  );
  const variants = sameName.filter((item) => item.skill_id !== skill.skill_id);
  const whyNot = skill.observed_runs
    ? `${skill.observed_runs} SkillRun(s) contain activation or instruction evidence.`
    : "No activation is observed. This does not prove the Agent rejected the Skill; candidate matching is unsupported unless the Agent emits that signal.";
  document.querySelector("#skill-inspector").className = "skill-inspector";
  document.querySelector("#skill-inspector").innerHTML = `
    <div class="skill-detail-head">
      <span class="grade-pill ${skill.observed_runs ? "observed" : "inferred"}">${
        skill.observed_runs ? "Observed use" : "Not observed"
      }</span>
      <h2>${esc(skill.name)}</h2>
      <p>${esc(skill.description || "No description declared.")}</p>
    </div>
    <section class="fact-block">
      <h4>Definition identity</h4>
      <dl class="kv">
        <dt>Version</dt><dd>${esc(skill.version || "not declared")}</dd>
        <dt>Digest</dt><dd class="mono">${esc(skill.digest)}</dd>
        <dt>Source</dt><dd>${esc(skill.source_kind)}</dd>
        <dt>Path</dt><dd class="mono">${esc(skill.source_path)}</dd>
        <dt>Compatibility</dt><dd>${esc(skill.compatibility || "not declared")}</dd>
        <dt>Validation</dt><dd>${skill.valid ? "Valid" : esc(skill.validation_message)}</dd>
      </dl>
    </section>
    <section class="fact-block">
      <h4>Declared resources</h4>
      <div class="resource-summary">
        ${Object.entries(skill.resource_counts).map(([kind, count]) =>
          `<span><strong>${esc(count)}</strong>${esc(kind)}</span>`
        ).join("")}
      </div>
      <ul class="resource-list">${skill.resources.slice(0, 16).map((resource) =>
        `<li><span>${esc(resource.path)}</span><small>${esc(resource.kind)} · ${esc(resource.bytes)} B</small></li>`
      ).join("") || "<li><span>No scripts, references, or assets declared.</span></li>"}</ul>
    </section>
    <section class="fact-block">
      <h4>Runtime diagnosis</h4>
      <p class="basis">${esc(whyNot)}</p>
      <dl class="kv finding-kv">
        <dt>Observed Agents</dt><dd>${esc(skill.observed_agents.join(", ") || "none")}</dd>
        <dt>Failed runs</dt><dd>${esc(skill.failed_runs || 0)}</dd>
        <dt>Last observed</dt><dd>${esc(formatTime(skill.last_observed_at))}</dd>
        <dt>Variants</dt><dd>${esc(sameName.length)} installed definition(s)</dd>
      </dl>
    </section>
    <section class="fact-block">
      <h4>Definition comparison</h4>
      ${variants.length ? `
        <label class="variant-picker">Compare with
          <select id="variant-target">
            ${variants.map((item) => `<option value="${esc(item.skill_id)}">${
              esc(item.version || item.digest.slice(0, 8))
            } · ${esc(item.source_kind)}</option>`).join("")}
          </select>
        </label>
        <div id="variant-comparison" class="variant-comparison"></div>
      ` : `<p class="basis">No same-name definition variant is installed. Cross-version impact cannot be assessed from a single definition.</p>`}
    </section>`;
  const variantTarget = document.querySelector("#variant-target");
  if (variantTarget) {
    const load = () => loadSkillDefinitionComparison(
      skill.skill_id,
      variantTarget.value
    ).catch((error) => {
      document.querySelector("#variant-comparison").innerHTML =
        `<p class="basis">${esc(error.message)}</p>`;
    });
    variantTarget.addEventListener("change", load);
    load();
  }
}

async function loadSkillDefinitionComparison(leftId, rightId) {
  const comparison = await getJSON(
    `/api/skill-compare?left=${encodeURIComponent(leftId)}&right=${encodeURIComponent(rightId)}`
  );
  const changed = comparison.changed_fields || [];
  const added = comparison.resources_added || [];
  const removed = comparison.resources_removed || [];
  const target = document.querySelector("#variant-comparison");
  if (!target || selectedSkillId !== leftId) return;
  target.innerHTML = `
    <p class="comparison-summary">${comparison.same_digest
      ? "Definitions are byte-identical."
      : `${changed.length} metadata field(s) differ.`}</p>
    <dl class="kv finding-kv">
      <dt>Evidence</dt><dd>${esc(comparison.evidence_grade)}</dd>
      <dt>Changed</dt><dd>${esc(changed.join(", ") || "none")}</dd>
      <dt>Resources +</dt><dd>${esc(added.map((item) => item.path).join(", ") || "none")}</dd>
      <dt>Resources −</dt><dd>${esc(removed.map((item) => item.path).join(", ") || "none")}</dd>
    </dl>
    <p class="basis">${esc(comparison.basis)}</p>`;
}

function renderConflicts() {
  document.querySelector("#conflicts").innerHTML = skillConflicts.slice(0, 30).map((item) => `
    <article class="conflict-row">
      <strong>${esc(item.left.name)}</strong>
      <span class="conflict-link"><i class="fill-pct-${percentBucket(item.overlap * 100)}"></i></span>
      <strong>${esc(item.right.name)}</strong>
      <span>${Math.round(item.overlap * 100)}% term overlap</span>
      <small>${esc(item.shared_terms.join(", "))}</small>
    </article>
  `).join("") || `<div class="empty-inspector compact-empty"><p>No high-overlap candidates.</p><small>This is not proof that conflicts cannot occur.</small></div>`;
}

function renderSettings() {
  if (!runtimeSettings || !document.querySelector("#integration-list")) return;
  document.querySelector("#integration-list").innerHTML = runtimeIntegrations.map((item) => `
    <article class="integration-row">
      <span class="integration-status ${item.connection_status === "verified" ? "active" : item.detected ? "available" : "missing"}"></span>
      <div>
        <strong>${esc(item.agent)}</strong>
        <small>${item.connection_status === "verified"
          ? `${(item.installed_events || []).length} runtime events · live evidence verified · ${item.fail_open ? "fail-open" : "blocking unknown"}`
          : item.installed
            ? `${(item.installed_events || []).length} events configured · awaiting Agent restart/trust or a new run`
          : item.detected
            ? "Detected · runtime collection consent not granted"
            : "Agent not detected on this machine"}</small>
        <code>${esc(item.agent_version || "version unavailable")} · ${esc(item.selected_collection_mode || "unknown")}</code>
        <code>${esc(item.config_path || "")}</code>
      </div>
      <span class="integration-mode">${esc(item.connection_status === "verified" ? "Live" : item.installed ? "Pending" : item.detected ? "Available" : "Absent")}</span>
    </article>
  `).join("");
  const counts = runtimeSettings.counts || {};
  const privacy = runtimeSettings.privacy || {};
  document.querySelector("#data-settings").innerHTML = `
    <dl class="settings-kv">
      <dt>SQLite</dt><dd class="mono">${esc(runtimeSettings.database)}</dd>
      <dt>Stored size</dt><dd>${esc(formatBytes(runtimeSettings.database_bytes))}</dd>
      <dt>SkillRuns</dt><dd>${esc(counts.skill_runs || 0)}</dd>
      <dt>Evidence events</dt><dd>${esc(counts.normalized_events || 0)}</dd>
      <dt>Retention</dt><dd>${esc(runtimeSettings.config.retention_days || "unlimited")}</dd>
      <dt>Model proxy</dt><dd>${privacy.model_requests_proxied ? "Enabled" : "Never"}</dd>
      <dt>Raw prompt export</dt><dd>${privacy.raw_prompt_exported ? "Enabled" : "Never"}</dd>
    </dl>
    <p class="privacy-callout">Deleting a SkillRun removes only this SQLite index. Agent source transcripts remain untouched.</p>`;
  document.querySelector("#included-projects").value =
    (runtimeSettings.config.projects || []).join("\n");
  document.querySelector("#excluded-paths").value =
    (runtimeSettings.config.exclude_paths || []).join("\n");
  document.querySelector("#retention-days").value =
    runtimeSettings.config.retention_days || "";
  document.querySelector("#exporter-list").innerHTML = runtimeExporters.length
    ? runtimeExporters.map((item) => `
      <article class="integration-row">
        <span class="integration-status ${item.ok === false ? "missing" : "active"}"></span>
        <div><strong>${esc(item.endpoint || "OTLP/HTTP")}</strong><small>${esc(item.exported || 0)} exported · ${esc(item.failed || 0)} failed</small></div>
        <span class="integration-mode">${item.ok === false ? "Retrying" : "Live"}</span>
      </article>`).join("")
    : `<div class="empty-inspector compact-empty"><p>No network exporter configured.</p><small>Start with --otlp-endpoint or OTEL_EXPORTER_OTLP_ENDPOINT.</small></div>`;
}

function formatBytes(bytes) {
  const value = Number(bytes) || 0;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

async function saveRuntimeSettings() {
  const projects = document.querySelector("#included-projects").value
    .split("\n").map((value) => value.trim()).filter(Boolean);
  const exclusions = document.querySelector("#excluded-paths").value
    .split("\n").map((value) => value.trim()).filter(Boolean);
  const retentionValue = document.querySelector("#retention-days").value.trim();
  const retentionDays = retentionValue ? Number(retentionValue) : null;
  const response = await fetch("/api/settings", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      projects,
      exclude_paths: exclusions,
      retention_days: retentionDays,
    }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Unable to save settings");
  runtimeSettings.config = result.config;
  document.querySelector("#settings-save-state").textContent =
    "Saved. Restart Skill Runtime to apply collection boundaries and retention.";
  renderSettings();
}

async function deleteSelectedRun() {
  if (!selectedRun) return;
  const confirmed = window.confirm(
    `Delete the local index for ${selectedRun.name}? The Agent source transcript will not be changed.`
  );
  if (!confirmed) return;
  const response = await fetch(
    `/api/skill-runs/${encodeURIComponent(selectedRun.skill_run_id)}`,
    {method: "DELETE"}
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Unable to delete SkillRun index");
  selectedRunId = null;
  selectedRun = null;
  await loadIndex(true);
  showRunIndex(true);
}

async function loadSkillRun(skillRunId, navigate = false) {
  if (navigate || location.hash.startsWith("#/runs")) setView("runs", false);
  selectedRunId = skillRunId;
  if (navigate) history.pushState({}, "", `#/runs/${encodeURIComponent(skillRunId)}`);
  renderRuns();
  const run = await getJSON(`/api/skill-runs/${encodeURIComponent(skillRunId)}`);
  showSkillRunDetail(run);
}

function showSkillRunDetail(run) {
  selectedRun = run;
  document.body.classList.add("detail-mode");
  document.querySelector("#empty-detail").classList.add("hidden");
  document.querySelector("#run-detail").classList.remove("hidden");
  renderDetail(selectedRun);
  window.scrollTo({top: 0, behavior: "smooth"});
}

function showRunIndex(navigate = false) {
  setView("runs", false);
  selectedRunId = null;
  selectedRun = null;
  selectedGraphNodeId = null;
  currentGraph = null;
  if (navigate) history.pushState({}, "", "#/runs");
  document.body.classList.remove("detail-mode");
  document.querySelector("#run-detail").classList.add("hidden");
  document.querySelector("#empty-detail").classList.remove("hidden");
  renderRuns();
  renderRuntimeOverview();
  window.scrollTo({top: 0, behavior: "smooth"});
}

function renderRunFactSummary(run) {
  const entries = new Map(
    (run.activity_summary?.entries || []).map((entry) => [entry.stage, entry])
  );
  const execution = entries.get("execution");
  const artifacts = entries.get("artifacts");
  const outcome = entries.get("outcome");
  const calls = execution?.objects?.reduce(
    (total, object) => total + (object.call_count || 0), 0
  ) || 0;
  const finalResponses = outcome?.objects?.find(
    (object) => object.label === "Final response"
  )?.count || 0;
  const facts = [
    `<strong>Skill</strong> ${esc(run.name)}`,
  ];
  if (entries.get("instructions")?.event_count) {
    facts.push(esc(tr("Primary instructions loaded")));
  }
  if (entries.get("resources")?.objects?.length) {
    facts.push(`${esc(entries.get("resources").objects.length)} ${esc(tr("Skill resources accessed"))}`);
  }
  if (calls) facts.push(`${esc(calls)} ${esc(tr("tool calls"))}`);
  if (artifacts?.objects?.length) {
    facts.push(`${esc(artifacts.objects.length)} ${esc(tr("logical artifacts"))}`);
  }
  if (finalResponses) facts.push(esc(tr("Final response available")));
  if (run.first_gap) {
    const separator = window.SkillRuntimeI18n?.locale?.startsWith("zh") ? "：" : ": ";
    facts.push(`${esc(tr("First observable boundary"))}${separator}${esc(tr(stageLabels[run.first_gap] || run.first_gap))}`);
  }
  document.querySelector("#narrative").innerHTML = facts
    .map((fact) => `<span>${fact}</span>`)
    .join('<i aria-hidden="true">·</i>');
}

function renderDetail(run) {
  document.querySelector("#detail-context").textContent =
    `${run.adapter} ${run.adapter_version} · ${run.model || "model unavailable"} · ${formatTime(run.started_at)}`;
  document.querySelector("#detail-title").textContent = run.name;
  document.querySelector("#detail-description").textContent =
    `${run.description || "Runtime-observed Skill"} · ${run.session_title || "session context"}`;
  document.querySelector("#detail-status").innerHTML =
    `<span class="status-pill ${esc(run.status)}">${esc(run.status)}</span>`;
  document.querySelector("#metric-coverage").textContent = `${run.evidence_completeness}%`;
  document.querySelector("#coverage-fill").style.width = `${run.evidence_completeness}%`;
  document.querySelector("#metric-activation").textContent = tr(pretty(run.activation_mode));
  document.querySelector("#metric-activation-grade").textContent =
    `${pretty(run.evidence_grade)} evidence`;
  document.querySelector("#metric-events").textContent = run.events.length;
  document.querySelector("#metric-relationships").textContent =
    `${run.relationships.length} attribution edges`;
  document.querySelector("#metric-gap").textContent = run.first_gap
    ? stageLabels[run.first_gap] || pretty(run.first_gap)
    : "No gap";
  renderRunFactSummary(run);
  renderAssessment(run);
  renderActivitySummary(run);
  fillSelect(
    "#event-type-filter",
    run.events.map((event) => event.event_type),
    "All event types",
  );
  fillSelect(
    "#event-skill-filter",
    run.events.map((event) => event.skill_name),
    "All Skills",
  );
  fillSelect(
    "#event-grade-filter",
    run.events.map((event) => event.evidence_grade),
    "All grades",
  );
  renderFindings(run);
  renderInferredAnalysis(run);
  renderComparePicker(run);
  renderPanorama(run);
  renderTimeline(run);
  renderCapabilities(run);
  resetInspector();
}

function activityObjectLabel(object) {
  if (object.kind === "tool") {
    const terminal = object.failed_count
      ? `${object.failed_count} ${tr("failed")}`
      : `${object.completed_count || 0} ${tr("completed")}`;
    return `${object.label} ×${object.call_count} · ${terminal}`;
  }
  if (object.kind === "artifact") {
    return `${object.label} · ${tr(object.final_state)}`;
  }
  if (object.kind === "outcome") {
    return `${tr(object.label)} · ${object.count}`;
  }
  const location = object.location && object.location !== "not recorded"
    ? ` · ${tr(object.location)}`
    : "";
  return `${tr(object.label)} · ${tr(object.action || object.kind)}${location}`;
}

function activityHeadline(entry) {
  if (entry.stage === "activation") {
    if (entry.status === "observed") {
      const mode = entry.headline.split(" · ").slice(1).join(" · ");
      return `${tr("Activation signal observed")} · ${tr(pretty(mode || "unknown"))}`;
    }
    return tr("Activation method is unconfirmed");
  }
  if (entry.stage === "instructions") {
    return `${entry.objects.length} ${tr(entry.objects.length === 1 ? "instruction source loaded" : "instruction sources loaded")}`;
  }
  if (entry.stage === "resources") {
    return `${entry.objects.length} ${tr(entry.objects.length === 1 ? "Skill resource accessed" : "Skill resources accessed")}`;
  }
  if (entry.stage === "execution") {
    const calls = entry.objects.reduce((total, object) => total + (object.call_count || 0), 0);
    return `${calls} ${tr("tool calls")} · ${entry.event_count} ${tr("lifecycle events")}`;
  }
  if (entry.stage === "artifacts") {
    return `${entry.objects.length} ${tr("logical artifacts")} · ${entry.event_count} ${tr("evidence records")}`;
  }
  if (entry.stage === "outcome") {
    const finalResponse = entry.objects.find((object) => object.label === "Final response")?.count || 0;
    const progress = entry.objects.find((object) => object.label === "Progress updates")?.count || 0;
    const verified = entry.objects.find((object) => object.label === "Independent verification")?.count || 0;
    return `${finalResponse} ${tr("final response")} · ${progress} ${tr("progress updates")} · ${verified} ${tr("independently verified")}`;
  }
  return tr(entry.headline);
}

function activityObjectDetails(object) {
  const rows = [];
  if (object.path_hint && object.path_hint !== "not recorded") {
    rows.push(`<dt>${esc(tr("Location"))}</dt><dd class="mono">${esc(object.path_hint)}</dd>`);
  } else if (object.location) {
    rows.push(`<dt>${esc(tr("Location"))}</dt><dd>${esc(tr(object.location))}</dd>`);
  }
  if (object.final_state) {
    rows.push(`<dt>${esc(tr("Final state"))}</dt><dd>${esc(tr(object.final_state))}</dd>`);
  }
  if (object.action) {
    rows.push(`<dt>${esc(tr("Observed action"))}</dt><dd>${esc(tr(object.action))}</dd>`);
  }
  if (object.call_count != null) {
    rows.push(`<dt>${esc(tr("Tool calls"))}</dt><dd>${esc(object.call_count)} · ${esc(object.completed_count || 0)} ${esc(tr("completed"))} · ${esc(object.failed_count || 0)} ${esc(tr("failed"))}</dd>`);
  }
  if (object.source_event_count != null) {
    rows.push(`<dt>${esc(tr("Evidence"))}</dt><dd>${esc(object.source_event_count)} ${esc(tr("records"))} · ${esc(object.observed_event_count || 0)} ${esc(tr("observed"))} · ${esc(object.derived_event_count || 0)} ${esc(tr("derived"))}</dd>`);
  }
  if (object.count != null) {
    rows.push(`<dt>${esc(tr("Count"))}</dt><dd>${esc(object.count)}</dd>`);
  }
  if (object.occurred_at) {
    rows.push(`<dt>${esc(tr("Last observed"))}</dt><dd>${esc(formatTime(object.occurred_at))}</dd>`);
  }
  return rows.join("");
}

function activityObjectMarkup(object) {
  const content = object.content
    ? `<div class="report-content">
        <span>${esc(tr("Available report content"))} · ${esc(tr(object.content_scope || "redacted normalized excerpt"))}</span>
        <p>${esc(object.content)}</p>
      </div>`
    : "";
  return `<article class="object-evidence-card">
    <strong>${esc(tr(activityObjectLabel(object)))}</strong>
    <dl class="kv finding-kv">${activityObjectDetails(object)}</dl>
    ${object.basis ? `<p class="basis">${esc(tr(object.basis))}</p>` : ""}
    ${content}
  </article>`;
}

function renderActivitySummary(run) {
  const summary = run.activity_summary;
  const target = document.querySelector("#activity-summary");
  if (!summary) {
    target.innerHTML = `<div class="empty-inspector"><p>No object summary is available.</p></div>`;
    document.querySelector("#activity-discipline").textContent = "";
    return;
  }
  target.innerHTML = summary.entries.map((entry) => `
    <button class="activity-row" type="button" data-activity-stage="${esc(entry.stage)}">
      <span class="activity-stage">${esc(tr(stageLabels[entry.stage] || entry.stage))}</span>
      <span class="activity-main">
        <strong>${esc(activityHeadline(entry))}</strong>
        <span class="activity-objects">
          ${(entry.objects || []).map((object) =>
            `<span class="activity-object">${esc(tr(activityObjectLabel(object)))}</span>`
          ).join("") || `<span class="activity-empty">${esc(tr(entry.limitation || (
            entry.status === "observed"
              ? "Direct lifecycle evidence is available."
              : "No matching evidence."
          )))}</span>`}
        </span>
        ${entry.limitation ? `<small>${esc(tr(entry.limitation))}</small>` : ""}
      </span>
      <span class="activity-evidence">
        ${entry.evidence_grade
          ? `<span class="grade-pill ${esc(entry.evidence_grade)}">${esc(tr(pretty(entry.evidence_grade)))}</span>`
          : `<span class="activity-status">${esc(tr(pretty(entry.status)))}</span>`}
        <small>${esc(entry.event_count)} ${esc(tr("records"))}</small>
      </span>
    </button>
  `).join("");
  document.querySelector("#activity-discipline").textContent = summary.discipline;
  document.querySelectorAll("[data-activity-stage]").forEach((button) => {
    button.addEventListener("click", () => {
      const entry = summary.entries.find(
        (item) => item.stage === button.dataset.activityStage
      );
      if (!entry) return;
      document.querySelectorAll(".activity-row").forEach(
        (item) => item.classList.remove("active")
      );
      button.classList.add("active");
      inspectActivityEntry(entry, run);
      document.querySelector(".inspector-pane")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  });
}

function inspectActivityEntry(entry, run) {
  const evidenceEvents = run.events.filter((event) =>
    entry.event_ids.includes(event.event_id)
  );
  const grade = entry.evidence_grade || "unknown";
  document.querySelector("#inspector-grade").innerHTML =
    `<span class="grade-pill ${esc(grade)}">${esc(grade)}</span>`;
  document.querySelector("#inspector").className = "inspector";
  document.querySelector("#inspector").innerHTML = `
    <h3 class="inspector-title">${esc(activityHeadline(entry))}</h3>
    <p class="inspector-type">${esc(tr(stageLabels[entry.stage] || entry.stage))} · ${esc(tr("object summary"))}</p>
    <section class="fact-block">
      <h4>Concrete objects</h4>
      <div class="object-evidence-list">${(entry.objects || []).map(activityObjectMarkup).join("")
        || `<p class="basis">${esc(tr(entry.limitation || "No matching evidence."))}</p>`}</div>
    </section>
    <section class="fact-block">
      <h4>Evidence boundary</h4>
      <dl class="kv finding-kv">
        <dt>Source records</dt><dd>${esc(evidenceEvents.length)}</dd>
        <dt>Evidence grade</dt><dd>${esc(grade)}</dd>
        <dt>Causal scope</dt><dd>${esc(entry.causal_scope)}</dd>
      </dl>
      <p class="basis">${esc(tr(entry.limitation || run.activity_summary.discipline))}</p>
    </section>
    <section class="fact-block">
      <h4>Underlying facts</h4>
      <ul class="evidence-list">${evidenceEvents.slice(0, 12).map((event) =>
        `<li><strong>${esc(event.summary)}</strong><br>${esc(event.evidence_grade)} · ${esc(formatTime(event.occurred_at, false))}</li>`
      ).join("")}</ul>
    </section>`;
}

function diagnosisTitle(diagnosis) {
  const titles = {
    explicit_failure: "An explicit runtime failure was observed",
    behavior_deviation: "Checkable Skill behavior needs review",
    result_unverified: "No explicit execution failure was observed; result correctness is unverified",
    result_verified: "No explicit execution failure was observed; result verified",
    result_not_observed: "No explicit execution failure was observed; no result is available",
    no_observed_issue: "No observable runtime issue was found",
  };
  return tr(titles[diagnosis.status] || diagnosis.title);
}

function diagnosisSummary(diagnosis) {
  const summaries = {
    explicit_failure: "Inspect the earliest failed lifecycle boundary. The record does not establish that the Skill caused the failure.",
    behavior_deviation: "One or more checkable constraints from the current Skill definition do not match the observable runtime evidence.",
    result_unverified: "Instructions, runtime activity, artifacts, and a final response are available for inspection. No deterministic verifier confirms the Agent's completion claims.",
    result_verified: "The runtime record contains an independent verification signal. This still does not establish that the Skill caused the outcome.",
    result_not_observed: "The available runtime record contains no explicit failed event, but there is no final result to inspect.",
    no_observed_issue: "Skill activity and a final response are visible. Result verification is not configured and is not counted as a failure.",
  };
  return tr(summaries[diagnosis.status] || diagnosis.summary);
}

function diagnosisItemCopy(item) {
  const titles = {
    runtime_failure: "Explicit runtime failure observed",
    skill_behavior_deviation: "A Skill behavior constraint needs review",
    result_not_verified: "Reported result is not independently verified",
    result_not_observed: "No final result was observed",
    source_incomplete: "The source may be incomplete",
    enablement_unconfirmed: "Skill enablement method is unconfirmed",
  };
  const summaries = {
    result_not_verified: "The final response can be inspected, but no deterministic test or explicit evaluation verifies its claims.",
    result_not_observed: "The source contains no inspectable final response.",
    source_incomplete: "Core activity is present, but the source is marked partial or incomplete; intermediate or later events may be missing.",
    enablement_unconfirmed: "Later Skill activity is visible, but no direct signal identifies how this Skill became active for the request.",
    skill_behavior_deviation: "The observable run does not match a checkable behavior constraint from the current SKILL.md.",
  };
  const impacts = {
    result_not_verified: "Impact: execution can be diagnosed, but result correctness cannot be concluded.",
    result_not_observed: "Impact: completion and result quality cannot be assessed.",
    source_incomplete: "Impact: an absent event cannot be treated as proof that it did not occur.",
    enablement_unconfirmed: "Impact: explicit invocation, automatic selection, and always-on enablement cannot be distinguished.",
    skill_behavior_deviation: "Impact: inspect the linked lifecycle stage and the source constraint before changing the Skill.",
  };
  return {
    title: tr(titles[item.code] || item.title),
    summary: tr(summaries[item.code] || item.summary),
    impact: tr(impacts[item.code] || item.impact || ""),
  };
}

function diagnosisFactCopy(fact, run) {
  const entry = run.activity_summary?.entries?.find(
    (item) => item.stage === fact.stage
  );
  const titles = {
    instructions_loaded: "Primary instructions loaded",
    resources_accessed: "Skill resource access recorded",
    tool_calls_recorded: "Tool execution recorded",
    artifacts_recorded: "Artifacts recorded",
    final_response_available: "Final response available",
  };
  return {
    title: tr(titles[fact.code] || fact.title),
    summary: entry ? activityHeadline(entry) : tr(fact.summary),
  };
}

function diagnosisReasoningStep(step, run) {
  const sentenceEnd = window.SkillRuntimeI18n?.locale?.startsWith("zh")
    ? "。"
    : ".";
  const execution = run.activity_summary?.entries?.find(
    (entry) => entry.stage === "execution"
  );
  const artifacts = run.activity_summary?.entries?.find(
    (entry) => entry.stage === "artifacts"
  );
  const outcome = run.activity_summary?.entries?.find(
    (entry) => entry.stage === "outcome"
  );
  if (step.code === "pair_tool_calls") {
    const calls = execution?.objects?.reduce(
      (total, object) => total + (object.call_count || 0), 0
    ) || 0;
    return `${execution?.event_count || 0} ${tr("tool lifecycle records were paired by source call ID into")} ${calls} ${tr("calls")}${sentenceEnd}`;
  }
  if (step.code === "group_artifacts") {
    return `${artifacts?.event_count || 0} ${tr("file records were grouped by canonical path into")} ${artifacts?.objects?.length || 0} ${tr("logical artifacts")}${sentenceEnd}`;
  }
  if (step.code === "scan_failures") {
    const failed = run.events.filter((event) => event.status === "failed").length;
    return `${failed} ${tr("source events explicitly report failed status")}${sentenceEnd}`;
  }
  if (step.code === "separate_report_from_verification") {
    const reports = outcome?.objects?.find(
      (object) => object.label === "Final response"
    )?.count || 0;
    const verified = outcome?.objects?.find(
      (object) => object.label === "Independent verification"
    )?.count || 0;
    return `${reports} ${tr("reported result and")} ${verified} ${tr("independent verification records were kept separate")}${sentenceEnd}`;
  }
  return tr(step.summary);
}

function renderDiagnosisList(selector, items, run, emptyText) {
  const target = document.querySelector(selector);
  target.innerHTML = items.map((item) => {
    const copy = diagnosisItemCopy(item);
    return `
      <button class="diagnosis-item ${esc(item.severity || item.category)}"
              type="button" data-diagnosis-stage="${esc(item.stage || "")}">
        <span class="diagnosis-item-icon"></span>
        <span class="diagnosis-item-copy">
          <strong>${esc(copy.title)}</strong>
          <span>${esc(copy.summary)}</span>
          ${copy.impact ? `<small>${esc(copy.impact)}</small>` : ""}
        </span>
        <span class="diagnosis-item-meta">${esc(tr(stageLabels[item.stage] || item.category))}</span>
      </button>`;
  }).join("") || `<div class="diagnosis-empty">${esc(tr(emptyText))}</div>`;
}

function behaviorConstraintTitle(constraint) {
  const target = constraint.target_label || constraint.target;
  if (constraint.polarity === "prohibited") {
    return `${tr("Must not use")} ${target}`;
  }
  if (constraint.kind === "resource") {
    return `${tr("Must access Skill resource")} ${target}`;
  }
  if (constraint.kind === "command") {
    return `${tr("Must execute command")} ${target}`;
  }
  if (constraint.kind === "verification") {
    return `${tr("Must execute verification")} ${target}`;
  }
  return `${tr("Must call tool")} ${target}`;
}

function behaviorConstraintBasis(constraint) {
  const messages = {
    satisfied: "Matching runtime evidence was observed.",
    deviation: "Observed runtime evidence conflicts with this constraint.",
    expected_not_observed: "The expected behavior was not found in the complete observable boundary.",
    not_evaluable: constraint.conditional
      ? "The trigger condition cannot be confirmed from current evidence."
      : "Current telemetry cannot evaluate this constraint safely.",
  };
  return tr(messages[constraint.status] || constraint.basis);
}

function behaviorConstraintMarkup(constraint) {
  const statusLabels = {
    satisfied: "Satisfied",
    deviation: "Deviation",
    expected_not_observed: "Not observed",
    not_evaluable: "Insufficient evidence",
  };
  const source = constraint.source || {};
  const sourceLine = source.line
    ? (window.SkillRuntimeI18n?.locale?.startsWith("zh")
      ? `第 ${source.line} 行`
      : `${tr("line")} ${source.line}`)
    : "";
  const sourceLabel = [
    source.file || "SKILL.md",
    sourceLine,
    source.section || "",
  ].filter(Boolean).join(" · ");
  return `
    <button class="behavior-constraint ${esc(constraint.status)}" type="button"
            data-behavior-stage="${esc(constraint.stage || "execution")}">
      <span class="behavior-constraint-status">${esc(tr(statusLabels[constraint.status] || pretty(constraint.status)))}</span>
      <span class="behavior-constraint-copy">
        <strong>${esc(behaviorConstraintTitle(constraint))}</strong>
        <small>${esc(behaviorConstraintBasis(constraint))} · ${esc(sourceLabel)}</small>
      </span>
      <span class="behavior-constraint-stage">${esc(tr(stageLabels[constraint.stage] || constraint.stage))}</span>
    </button>`;
}

function renderBehaviorAssessment(conformance) {
  const counts = conformance?.counts || {};
  const constraints = conformance?.constraints || [];
  const statusLabels = {
    deviation: "Behavior deviation found",
    expected_not_observed: "Expected behavior not observed",
    partially_checked: "Partially checked",
    satisfied_observed_scope: "Satisfied in observed scope",
    not_evaluable: "Insufficient evidence",
    no_checkable_constraints: "No checkable constraints",
    definition_unavailable: "Skill definition unavailable",
  };
  const status = document.querySelector("#behavior-status");
  status.className = `behavior-status ${esc(conformance?.status || "definition_unavailable")}`;
  status.textContent = tr(statusLabels[conformance?.status] || "Skill definition unavailable");
  document.querySelector("#behavior-counts").innerHTML = `
    <article><span>${esc(tr("Extracted constraints"))}</span><strong>${esc(counts.total || 0)}</strong></article>
    <article><span>${esc(tr("Checked"))}</span><strong>${esc(counts.checked || 0)}</strong></article>
    <article><span>${esc(tr("Satisfied"))}</span><strong>${esc(counts.satisfied || 0)}</strong></article>
    <article><span>${esc(tr("Needs review"))}</span><strong>${esc((counts.deviations || 0) + (counts.expected_not_observed || 0))}</strong></article>`;

  const priority = {deviation: 0, expected_not_observed: 1, satisfied: 2, not_evaluable: 3};
  const sorted = [...constraints].sort(
    (left, right) => (priority[left.status] ?? 9) - (priority[right.status] ?? 9)
  );
  const actionable = sorted.filter((item) => item.status !== "not_evaluable");
  const visible = (actionable.length ? actionable : sorted).slice(0, 6);
  document.querySelector("#behavior-list").innerHTML = visible
    .map(behaviorConstraintMarkup).join("")
    || `<div class="diagnosis-empty">${esc(tr("No checkable behavior constraint was extracted from this Skill."))}</div>`;
  const more = document.querySelector("#behavior-more");
  more.classList.toggle("hidden", sorted.length <= visible.length);
  document.querySelector("#behavior-more-label").textContent =
    `${tr("View all constraints")} · ${sorted.length}`;
  document.querySelector("#behavior-all").innerHTML = sorted
    .map(behaviorConstraintMarkup).join("");
  document.querySelector("#behavior-limitation").textContent = tr(
    conformance?.source_status === "current_changed"
      ? "The current SKILL.md differs from the indexed definition; results are shown as a review aid only."
      : "Only exact tool, resource, command, and verification constraints are checked; unsupported natural-language rules are not guessed."
  );
}

function renderAssessment(run) {
  const assessment = run.assessment;
  const diagnosis = assessment?.diagnosis;
  const verdict = document.querySelector("#assessment-verdict");
  if (!assessment || !diagnosis) {
    verdict.className = "assessment-verdict open_questions";
    verdict.textContent = tr("Assessment unavailable");
    document.querySelector("#diagnosis-status-label").textContent =
      tr("Assessment unavailable");
    document.querySelector("#assessment-title").textContent =
      tr("Structured run assessment is unavailable");
    document.querySelector("#assessment-summary").textContent =
      tr("The current index lacks a structured assessment; recorded timeline facts remain inspectable.");
    document.querySelector("#diagnosis-counts").innerHTML = "";
    document.querySelector("#diagnosis-attention").innerHTML = "";
    document.querySelector("#diagnosis-limits").innerHTML = "";
    document.querySelector("#diagnosis-facts").innerHTML = "";
    renderBehaviorAssessment(null);
    document.querySelector("#diagnosis-reasoning-steps").innerHTML = "";
    document.querySelector("#diagnosis-does-not-establish").innerHTML = "";
    document.querySelector("#assessment-checks").innerHTML = "";
    document.querySelector("#assessment-discipline").textContent =
      tr("Evidence coverage is not a pass score, and completion is not proof of correctness.");
    return;
  }
  const counts = diagnosis.counts || {};
  const verdictLabels = {
    explicit_failure: `${counts.confirmed_failures || 0} ${tr("confirmed issues")}`,
    behavior_deviation: `${counts.behavior_deviations || 0} ${tr("behavior deviations")}`,
    result_unverified: `${counts.verification_gaps || 0} ${tr("verification gaps")}`,
    result_verified: "Result verified",
    result_not_observed: "Result unavailable",
    no_observed_issue: "No observable issue",
  };
  verdict.className = `assessment-verdict ${esc(diagnosis.status)}`;
  verdict.textContent = tr(verdictLabels[diagnosis.status] || pretty(diagnosis.status));
  document.querySelector("#diagnosis-status-label").className =
    `diagnosis-status-label ${esc(diagnosis.status)}`;
  document.querySelector("#diagnosis-status-label").textContent =
    tr(diagnosis.status === "explicit_failure" ? "Execution failure" :
      diagnosis.status === "behavior_deviation" ? "Behavior needs review" :
      diagnosis.status === "result_verified" ? "Result verified" :
      diagnosis.status === "result_not_observed" ? "Result unavailable" :
      diagnosis.status === "no_observed_issue" ? "No observable issue" :
      "Result unverified");
  document.querySelector("#assessment-title").textContent = diagnosisTitle(diagnosis);
  document.querySelector("#assessment-summary").textContent = diagnosisSummary(diagnosis);
  document.querySelector("#assessment-discipline").textContent = tr(assessment.discipline);
  document.querySelector("#diagnosis-counts").innerHTML = `
    <article>
      <span>${esc(tr("Explicit failures"))}</span>
      <strong>${esc(counts.confirmed_failures || 0)}</strong>
      <small>${esc(tr("source-reported"))}</small>
    </article>
    <article>
      <span>${esc(tr("Behavior deviations"))}</span>
      <strong>${esc(counts.behavior_deviations || 0)}</strong>
      <small>${esc(tr("from checkable constraints"))}</small>
    </article>
    <article>
      <span>${esc(tr("Result verification"))}</span>
      <strong>${esc(diagnosis.status === "result_verified" ? tr("Verified") :
        counts.verification_gaps ? tr("Missing") : tr("Not configured"))}</strong>
      <small>${esc(tr("not a failure by default"))}</small>
    </article>
    <article>
      <span>${esc(tr("Observability limits"))}</span>
      <strong>${esc(counts.observability_limits || 0)}</strong>
      <small>${esc(tr("adapter or source limits"))}</small>
    </article>`;
  renderBehaviorAssessment(diagnosis.conformance);
  renderDiagnosisList(
    "#diagnosis-attention",
    diagnosis.attention_items || [],
    run,
    "No issue currently requires attention.",
  );
  renderDiagnosisList(
    "#diagnosis-limits",
    diagnosis.observability_limits || [],
    run,
    "No material observability limit was detected.",
  );
  document.querySelector("#diagnosis-attention-count").textContent =
    diagnosis.attention_items?.length || 0;
  document.querySelector("#diagnosis-limit-count").textContent =
    diagnosis.observability_limits?.length || 0;
  document.querySelector("#diagnosis-facts").innerHTML =
    (diagnosis.confirmed_facts || []).map((fact) => {
      const copy = diagnosisFactCopy(fact, run);
      return `
        <button class="diagnosis-fact" type="button"
                data-diagnosis-stage="${esc(fact.stage)}">
          <span>${esc(tr(stageLabels[fact.stage] || fact.stage))}</span>
          <strong>${esc(copy.title)}</strong>
          <small>${esc(copy.summary)}</small>
        </button>`;
    }).join("") || `<div class="diagnosis-empty">${esc(tr("No confirmed activity is available."))}</div>`;
  document.querySelector("#diagnosis-method").textContent =
    tr(diagnosis.reasoning?.label || "Calculated by system rules");
  document.querySelector("#diagnosis-reasoning-summary").textContent =
    tr("Fixed rules summarize normalized source records; the same evidence produces the same result. No model-generated explanation is used.");
  document.querySelector("#diagnosis-reasoning-steps").innerHTML =
    (diagnosis.reasoning?.steps || []).map(
      (step) => `<li>${esc(diagnosisReasoningStep(step, run))}</li>`
    ).join("");
  document.querySelector("#diagnosis-does-not-establish").innerHTML = [
    "that the Skill caused the final outcome",
    "that the reported result is correct",
    "that an unobserved event did not occur",
  ].map((item) => `<li>${esc(tr(item))}</li>`).join("");
  document.querySelector("#assessment-checks").innerHTML = assessment.checks.map((check) => `
    <button class="assessment-row" type="button" role="row"
            data-assessment-stage="${esc(check.stage)}">
      <span class="assessment-check" role="cell">
        <strong>${esc(tr(check.label))}</strong>
        <small>${esc(tr(stageLabels[check.stage] || check.stage))} · ${esc(check.event_count)}</small>
      </span>
      <span class="assessment-expected" role="cell">${esc(tr(check.expected))}</span>
      <span class="assessment-observed" role="cell">${esc(tr(check.observed))}</span>
      <span class="assessment-judgment ${esc(check.status)}" role="cell">
        ${esc(tr(pretty(check.status)))}
      </span>
    </button>
  `).join("");
  document.querySelectorAll("[data-assessment-stage]").forEach((button) => {
    button.addEventListener("click", () => {
      const stage = run.stage_summary.find(
        (item) => item.stage === button.dataset.assessmentStage
      );
      if (!stage) return;
      document.querySelectorAll(".assessment-row").forEach(
        (item) => item.classList.remove("active")
      );
      button.classList.add("active");
      inspectStage(
        stage,
        run.events.filter((event) => event.stage === stage.stage),
        run,
      );
      document.querySelector(".inspector-pane")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  });
  document.querySelectorAll("[data-diagnosis-stage]").forEach((button) => {
    button.addEventListener("click", () => {
      const entry = run.activity_summary?.entries?.find(
        (item) => item.stage === button.dataset.diagnosisStage
      );
      if (entry) inspectActivityEntry(entry, run);
    });
  });
  document.querySelectorAll("[data-behavior-stage]").forEach((button) => {
    button.addEventListener("click", () => {
      const entry = run.activity_summary?.entries?.find(
        (item) => item.stage === button.dataset.behaviorStage
      );
      if (entry) inspectActivityEntry(entry, run);
    });
  });
}

function renderComparePicker(run) {
  const axis = document.querySelector("#compare-axis").value;
  const candidates = skillRuns.filter((candidate) =>
    candidate.skill_run_id !== run.skill_run_id
    && (axis === "skill_version" ? candidate.name === run.name : candidate.name === run.name)
  );
  const target = document.querySelector("#compare-target");
  target.innerHTML = candidates.map((candidate) => `
    <option value="${esc(candidate.skill_run_id)}">
      ${esc(candidate.adapter)} · ${esc(candidate.model || "model unavailable")} ·
      ${esc(formatTime(candidate.started_at))}
    </option>
  `).join("") || `<option value="">No comparable ${esc(run.name)} run</option>`;
  target.disabled = !candidates.length;
  document.querySelector("#compare-run").disabled = !candidates.length;
  selectedComparisonId = candidates[0]?.skill_run_id || null;
  document.querySelector("#comparison").innerHTML = candidates.length
    ? `<div class="compare-empty">Choose a run to align its evidence by lifecycle stage.</div>`
    : `<div class="compare-empty">A second run of this Skill is required for comparison.</div>`;
}

async function loadComparison() {
  const right = document.querySelector("#compare-target").value;
  if (!selectedRunId || !right) return;
  selectedComparisonId = right;
  const axis = document.querySelector("#compare-axis").value;
  const aligned = document.querySelector("#compare-aligned").checked ? "true" : "false";
  const comparison = await getJSON(
    `/api/compare?left=${encodeURIComponent(selectedRunId)}&right=${encodeURIComponent(right)}`
    + `&axis=${encodeURIComponent(axis)}&aligned=${aligned}`
  );
  renderComparison(comparison);
}

function renderComparison(comparison) {
  const changedLabel = comparison.first_changed_stage
    ? stageLabels[comparison.first_changed_stage] || pretty(comparison.first_changed_stage)
    : "No comparable difference";
  const mask = comparison.comparability_mask || {};
  const maskEntries = ["lifecycle", "outcome", "absolute_time"].map((dimension) => {
    const item = mask[dimension] || {status: "masked", reason: "No comparability decision available."};
    return `
      <article class="mask-card ${esc(item.status)}">
        <span>${esc(pretty(dimension))}</span>
        <strong>${esc(pretty(item.status))}</strong>
        <small>${esc(item.reason)}</small>
      </article>`;
  }).join("");
  document.querySelector("#comparison").innerHTML = `
    <div class="comparability-banner ${esc(comparison.decision || "not_comparable")}">
      <div>
        <span>COMPARABILITY MASK</span>
        <strong>${esc(pretty(comparison.decision || "not_comparable"))}</strong>
      </div>
      <p>${esc(comparison.alignment_basis || "No shared evaluation-task evidence was observed.")}</p>
    </div>
    <div class="comparability-mask">${maskEntries}</div>
    <div class="compare-summary">
      <article><span>First comparable difference</span><strong>${esc(changedLabel)}</strong></article>
      <article><span>Comparable stages</span><strong>${esc(comparison.comparable_stage_count)}</strong></article>
      <article><span>Changed stages</span><strong>${esc(comparison.changed_stage_count)}</strong></article>
      <article><span>Capability-limited</span><strong>${esc(comparison.limited_stage_count)}</strong></article>
    </div>
    <div class="compare-identities">
      <div><span>BASELINE</span><strong>${esc(comparison.left.agent)} · ${esc(comparison.left.model || "unknown model")}</strong><small>${esc(formatTime(comparison.left.started_at))}</small></div>
      <div><span>COMPARISON</span><strong>${esc(comparison.right.agent)} · ${esc(comparison.right.model || "unknown model")}</strong><small>${esc(formatTime(comparison.right.started_at))}</small></div>
    </div>
    <div class="stage-compare" role="table" aria-label="Lifecycle comparison">
      ${comparison.stages.map((stage) => `
        <div class="stage-diff ${esc(stage.comparability)} ${stage.changed ? "changed" : ""}" role="row">
          <span class="stage-name">${esc(stageLabels[stage.stage] || stage.stage)}</span>
          <span><strong>${esc(stage.left.event_count)}</strong><small>${esc(stage.left.status)} · ${esc(stage.left.capability)}</small></span>
          <span class="diff-mark">${stage.changed === null ? "≉" : stage.changed ? "≠" : "="}</span>
          <span><strong>${esc(stage.right.event_count)}</strong><small>${esc(stage.right.status)} · ${esc(stage.right.capability)}</small></span>
          <span class="diff-reason">${esc(stage.reason)}</span>
        </div>
      `).join("")}
    </div>
    <p class="compare-discipline">${esc(comparison.discipline)}</p>
    <p class="compare-causality">Causal attribution: not allowed. Differences describe evidence, adapter capability, or aligned behavior only.</p>`;
}

function renderInferredAnalysis(run) {
  const persisted = (run.inferences || []).map((inference) => ({
    title: pretty(inference.inference_type || "Recorded inference"),
    claim: inference.payload?.claim || inference.payload?.summary
      || inference.payload?.description || "A source-provided inference is available.",
    confidence: inference.confidence,
    basis: [inference.basis].filter(Boolean),
  }));
  const candidates = [...persisted];
  for (const finding of (run.findings || [])) {
    if (finding.code === "runtime_failure") {
      candidates.push({
        title: "Inspect the earliest failed relationship",
        claim: "The earliest observed failure is a useful investigation boundary, but the Skill is not established as its cause.",
        confidence: 0.65,
        basis: finding.basis || [],
      });
    }
  }
  const unique = candidates.filter((candidate, index, all) =>
    all.findIndex((item) => item.title === candidate.title) === index
  ).slice(0, 5);
  document.querySelector("#inferred-analysis").innerHTML = unique.length
    ? unique.map((candidate) => `
      <article class="inference-card">
        <div class="inference-title">
          <i class="shape inferred"></i>
          <strong>${esc(tr(candidate.title))}</strong>
          <span>${esc(Math.round(Number(candidate.confidence || 0) * 100))}%</span>
        </div>
        <p>${esc(tr(candidate.claim))}</p>
        <details>
          <summary>${esc(tr("Why this is suggested"))}</summary>
          <ul>${(candidate.basis || []).map((basis) => `<li>${esc(tr(basis))}</li>`).join("")}</ul>
        </details>
        <small>${esc(tr("Investigation candidate · not a runtime fact · not a causal claim"))}</small>
      </article>
    `).join("")
    : `
      <div class="inference-abstention">
        <i class="shape inferred"></i>
        <div><strong>${esc(tr("No evidence-bounded inference"))}</strong>
        <small>${esc(tr("The system abstains instead of completing an unsupported story."))}</small></div>
      </div>`;
}

function renderFindings(run) {
  const findings = (run.findings || []).filter(
    (finding) => finding.severity === "error"
  );
  document.querySelector("#finding-count").textContent = findings.length;
  document.querySelector("#findings").innerHTML = findings.length
    ? findings.map((finding) => `
      <button class="finding ${esc(finding.severity)}" type="button"
              data-finding="${esc(finding.finding_id)}">
        <span class="finding-severity">${esc(finding.severity)}</span>
        <span class="finding-copy">
          <strong>${esc(tr(finding.title))}</strong>
          <span>${esc(tr(finding.summary))}</span>
        </span>
        <span class="finding-stage">${esc(stageLabels[finding.stage] || pretty(finding.stage))}</span>
      </button>
    `).join("")
    : `
      <div class="healthy-finding">
        <span class="healthy-dot"></span>
        <span>
          <strong>${esc(tr("No actionable diagnostic finding"))}</strong>
          <small>${esc(tr("Systemic observability limits are summarized above instead of repeated as run issues."))}</small>
        </span>
      </div>`;
  document.querySelectorAll(".finding").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".finding").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      inspectFinding(
        findings.find((finding) => finding.finding_id === button.dataset.finding)
      );
    });
  });
}

function inspectFinding(finding) {
  if (!finding) return;
  document.querySelector("#inspector-grade").innerHTML =
    `<span class="grade-pill ${esc(finding.evidence_grade)}">${esc(finding.evidence_grade)}</span>`;
  document.querySelector("#inspector").className = "inspector";
  document.querySelector("#inspector").innerHTML = `
    <h3 class="inspector-title">${esc(finding.title)}</h3>
    <p class="inspector-type">Diagnostic finding · ${esc(finding.code)}</p>
    <section class="fact-block">
      <h4>Finding</h4>
      <p class="basis">${esc(finding.summary)}</p>
      <dl class="kv finding-kv">
        <dt>Severity</dt><dd>${esc(finding.severity)}</dd>
        <dt>Boundary</dt><dd>${esc(stageLabels[finding.stage] || pretty(finding.stage))}</dd>
        <dt>Evidence</dt><dd>${esc(finding.evidence_grade)} · confidence ${esc(finding.confidence)}</dd>
        <dt>Causal scope</dt><dd>${esc(finding.causal_scope || "none")}</dd>
      </dl>
    </section>
    <section class="fact-block">
      <h4>Basis</h4>
      <ul class="evidence-list">${(finding.basis || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
    </section>
    ${(finding.missing_signals || []).length ? `
      <section class="fact-block">
        <h4>Missing signals</h4>
        <ul class="evidence-list">${finding.missing_signals.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      </section>` : ""}
    ${(finding.recommended_actions || []).length ? `
      <section class="fact-block">
        <h4>Next checks</h4>
        <ul class="evidence-list">${finding.recommended_actions.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      </section>` : ""}
  `;
}

const gradeRank = {observed: 0, derived: 1, inferred: 2, experimental: 3};

function weakestGrade(events) {
  return events.reduce((grade, event) => {
    const candidate = event.evidence_grade || "derived";
    return (gradeRank[candidate] ?? 1) > (gradeRank[grade] ?? 0) ? candidate : grade;
  }, "observed");
}

function groupLabel(stage, key) {
  if (stage === "execution") return key === "unknown" ? "Unclassified tool" : key;
  if (stage === "resources") return `${pretty(key)} resource`;
  if (stage === "artifacts") return pretty(key).replace("artifact ", "");
  return pretty(key);
}

function eventGroupKey(event) {
  const payload = event.payload || {};
  if (event.stage === "execution") return payload.tool_name || event.event_type || "unknown";
  if (event.stage === "resources") return payload.resource_kind || event.event_type || "resource";
  return event.event_type || event.status || "artifact";
}

function activityDetailNodes(entry, limit = 6) {
  if (!entry) return [];
  const objects = [...(entry.objects || [])]
    .filter((object) => object.count !== 0)
    .slice(0, limit);
  return objects.map((object, index) => {
    let subtitle = object.action || object.final_state || object.kind;
    let detail = object.path_hint || "";
    if (object.kind === "tool") {
      subtitle = `${object.call_count} ${tr("calls")} · ${object.completed_count || 0} ${tr("completed")}`;
      detail = `${object.failed_count || 0} ${tr("failed")} · ${object.event_ids.length} ${tr("source records")}`;
    } else if (object.kind === "outcome") {
      subtitle = `${object.count} ${tr(object.count === 1 ? "record" : "records")}`;
      detail = object.content ? tr("Report content available") : "";
    } else if (object.kind === "artifact") {
      subtitle = object.final_state;
    }
    return {
      id: `detail-${entry.stage}-${index}`,
      type: "activity_object",
      stage: entry.stage,
      label: object.label,
      subtitle,
      detail,
      status: object.failed_count ? "failed" : entry.status,
      evidence_grade: object.evidence_grade || entry.evidence_grade || "derived",
      event_ids: object.event_ids || [],
      occurred_at: object.occurred_at,
      basis: entry.limitation || "This object deterministically summarizes its underlying source records.",
      runtime_state_basis: null,
      object,
    };
  });
}

function stagePresentation(stage, summary, entry) {
  if (!entry) {
    return {
      subtitle: summary.status === "unsupported"
        ? tr("Adapter does not expose this signal")
        : summary.status === "not_observed"
          ? tr("No matching signal")
          : `${summary.event_count} ${tr("evidence records")}`,
      detail: "",
    };
  }
  if (stage === "activation") {
    return entry.status === "observed"
      ? {subtitle: tr("How enabled: confirmed"), detail: entry.headline}
      : {subtitle: tr("How enabled: unconfirmed"), detail: tr("Later Skill activity is visible")};
  }
  if (stage === "instructions") {
    const object = entry.objects[0];
    return {
      subtitle: object ? `${object.label} · ${tr("loaded")}` : tr("No instruction source observed"),
      detail: object?.path_hint || "",
    };
  }
  if (stage === "resources") {
    return {
      subtitle: entry.objects.length === 1
        ? `1 ${tr("Skill resource accessed")}`
        : `${entry.objects.length} ${tr("Skill resources accessed")}`,
      detail: entry.objects[0]?.label || entry.limitation,
    };
  }
  if (stage === "execution") {
    const calls = entry.objects.reduce((total, object) => total + (object.call_count || 0), 0);
    return {
      subtitle: `${calls} ${tr("tool calls")}`,
      detail: `${entry.event_count} ${tr("lifecycle records")}`,
    };
  }
  if (stage === "artifacts") {
    const retained = entry.objects.filter((object) => object.final_state?.includes("retained")).length;
    const removed = entry.objects.filter((object) => object.final_state?.includes("removed") || object.final_state === "deleted").length;
    return {
      subtitle: `${entry.objects.length} ${tr("logical artifacts")}`,
      detail: `${retained} ${tr("retained")} · ${removed} ${tr("removed")}`,
    };
  }
  if (stage === "outcome") {
    const finalResponse = entry.objects.find((object) => object.label === "Final response")?.count || 0;
    const verified = entry.objects.find((object) => object.label === "Independent verification")?.count || 0;
    return {
      subtitle: tr(finalResponse ? "Final response available" : "No final response observed"),
      detail: verified ? `${verified} ${tr("independently verified")}` : tr("Correctness not independently verified"),
    };
  }
  return {subtitle: entry.headline, detail: ""};
}

function buildEvidenceGraph(run) {
  const nodes = [];
  const edges = [];
  const ownEvents = run.events
    .filter((event) => !event.context_only)
    .sort((left, right) => new Date(left.occurred_at || 0) - new Date(right.occurred_at || 0));
  const terminalCallIds = new Set(
    ownEvents
      .filter((event) => ["tool.completed", "tool.failed", "tool.cancelled"].includes(event.event_type))
      .map((event) => event.payload?.call_id)
      .filter(Boolean)
  );
  const openEventIds = new Set(
    ownEvents
      .filter((event) =>
        event.event_type === "tool.started"
        && event.payload?.call_id
        && !terminalCallIds.has(event.payload.call_id)
      )
      .map((event) => event.event_id)
  );
  const latestOwnEvent = ownEvents.at(-1);
  const stageRanks = {
    request: 0, discovery: 1, activation: 2, instructions: 3,
    resources: 4, execution: 6, artifacts: 8, outcome: 10,
  };
  const summaries = Object.fromEntries(run.stage_summary.map((stage) => [stage.stage, stage]));
  const activityEntries = Object.fromEntries(
    (run.activity_summary?.entries || []).map((entry) => [entry.stage, entry])
  );
  Object.keys(stageLabels).forEach((stage, index) => {
    const summary = summaries[stage] || {status: "not_observed", event_count: 0};
    const stageEvents = run.events.filter((event) => event.stage === stage);
    const entry = activityEntries[stage];
    const presentation = stagePresentation(stage, summary, entry);
    nodes.push({
      id: `stage-${stage}`,
      type: "stage",
      stage,
      rank: stageRanks[stage],
      label: stageLabels[stage],
      subtitle: presentation.subtitle,
      detail: presentation.detail,
      status: summary.status,
      evidence_grade: summary.evidence_grade || (summary.status === "unsupported" ? "unsupported" : "derived"),
      event_ids: stageEvents.map((event) => event.event_id),
      count: summary.event_count,
      index: index + 1,
      basis: entry?.limitation || (summary.status === "unsupported"
        ? "The active adapter does not expose this lifecycle boundary."
        : "Stage coverage is reconstructed from normalized runtime records. It is not a claim that the stage caused the next stage."),
      runtime_state_basis: null,
      activity_entry: entry,
    });
  });

  const detailedStages = ["resources", "execution", "artifacts", "outcome"];
  const detailNodes = {};
  detailedStages.forEach((stage) => {
    const grouped = activityDetailNodes(activityEntries[stage]);
    grouped.forEach((node) => {
      node.rank = stageRanks[stage] + 1;
      nodes.push(node);
    });
    detailNodes[stage] = grouped;
  });

  const sequence = Object.keys(stageLabels);
  sequence.forEach((stage, index) => {
    const nextStage = sequence[index + 1];
    const groups = detailNodes[stage] || [];
    if (groups.length) {
      groups.forEach((group) => {
        edges.push({
          id: `membership-${stage}-${group.id}`,
          source: `stage-${stage}`,
          target: group.id,
          relationship_type: "stage_membership",
          evidence_grade: group.evidence_grade,
          basis: "These source events were normalized into this lifecycle stage.",
        });
        if (nextStage) {
          edges.push({
            id: `continuation-${group.id}-${nextStage}`,
            source: group.id,
            target: `stage-${nextStage}`,
            relationship_type: "lifecycle_order",
            evidence_grade: "derived",
            basis: "Lifecycle continuation for navigation only; it is not a causal claim.",
          });
        }
      });
    } else if (nextStage) {
      edges.push({
        id: `lifecycle-${stage}-${nextStage}`,
        source: `stage-${stage}`,
        target: `stage-${nextStage}`,
        relationship_type: "lifecycle_order",
        evidence_grade: "derived",
        basis: "Declared Skill lifecycle order; absence or adjacency does not establish causality.",
      });
    }
  });

  if (run.status === "incomplete" && latestOwnEvent) {
    let frontierNodes = nodes.filter((node) =>
      node.type === "activity_object"
      && node.event_ids.some((eventId) => openEventIds.has(eventId))
    );
    if (frontierNodes.length) {
      const frontierStages = new Set(frontierNodes.map((node) => node.stage));
      frontierNodes = frontierNodes.concat(
        nodes.filter((node) => node.type === "stage" && frontierStages.has(node.stage))
      );
    } else {
      const specific = nodes.find((node) =>
        node.type === "activity_object" && node.event_ids.includes(latestOwnEvent.event_id)
      );
      frontierNodes = [
        specific || nodes.find((node) => node.id === `stage-${latestOwnEvent.stage}`),
      ].filter(Boolean);
    }
    frontierNodes.forEach((node) => {
      node.status = "open_frontier";
      node.runtime_state_basis = openEventIds.size
        ? "Open frontier is derived from an observed tool start without a matching terminal event. It remains open until a terminal source event closes it."
        : "This SkillRun has no recorded terminal event. The latest observed boundary remains an open frontier; this does not prove a process is currently executing.";
    });
  }

  edges.forEach((edge) => {
    const target = nodes.find((node) => node.id === edge.target);
    edge.open_frontier = target?.status === "open_frontier";
    if (edge.open_frontier) {
      edge.runtime_state_basis = target.runtime_state_basis;
    }
  });
  return {nodes, edges};
}

function graphIcon(node) {
  if (node.type !== "stage") {
    if (node.stage === "execution") return `<path d="M8 9h8M8 15h8M5 6h14v12H5z"/>`;
    if (node.stage === "resources") return `<path d="M7 4h8l3 3v13H7z"/><path d="M15 4v4h4"/>`;
    return `<path d="M5 7h14v12H5z"/><path d="M9 7V4h6v3"/>`;
  }
  const icons = {
    request: `<circle cx="12" cy="12" r="7"/><path d="M12 8v4l3 2"/>`,
    discovery: `<circle cx="10" cy="10" r="5"/><path d="m14 14 5 5"/>`,
    activation: `<path d="m8 4 10 8-10 8z"/>`,
    instructions: `<path d="M6 4h12v16H6z"/><path d="M9 8h6M9 12h6M9 16h4"/>`,
    resources: `<path d="M4 7h6l2 2h8v10H4z"/>`,
    execution: `<path d="m7 8-4 4 4 4M17 8l4 4-4 4M14 5l-4 14"/>`,
    artifacts: `<path d="M5 7h14v12H5z"/><path d="M9 7V4h6v3"/>`,
    outcome: `<circle cx="12" cy="12" r="8"/><path d="m8 12 3 3 5-6"/>`,
  };
  return icons[node.stage] || icons.outcome;
}

function updateMotionControls() {
  document.querySelectorAll(".motion-mode").forEach((button) => {
    button.classList.toggle("active", button.dataset.motion === graphMotionMode);
  });
  const labels = {
    live: "Live · open frontier + new evidence",
    replay: "Replay · reconstructed event flow",
    static: "Static · motion disabled",
  };
  document.querySelector("#motion-status").textContent = labels[graphMotionMode];
}

function renderPanorama(run) {
  currentGraph = buildEvidenceGraph(run);
  selectedGraphNodeId = null;
  const currentEventIds = new Set(run.events.map((event) => event.event_id));
  const previousEventIds = graphEventHistory.get(run.skill_run_id);
  const newEventIds = previousEventIds
    ? new Set([...currentEventIds].filter((eventId) => !previousEventIds.has(eventId)))
    : new Set();
  const firstGraphRender = !previousEventIds;
  graphEventHistory.set(run.skill_run_id, currentEventIds);
  const svg = document.querySelector("#panorama");
  svg.setAttribute("class", `panorama motion-${graphMotionMode}`);
  updateMotionControls();
  const nodeWidth = 184;
  const nodeHeight = 92;
  const rankGap = 58;
  const rowGap = 18;
  const padX = 34;
  const padY = 34;
  const ranks = new Map();
  currentGraph.nodes.forEach((node) => {
    if (!ranks.has(node.rank)) ranks.set(node.rank, []);
    ranks.get(node.rank).push(node);
  });
  const maxRows = Math.max(...[...ranks.values()].map((items) => items.length), 1);
  const canvasHeight = Math.max(310, padY * 2 + maxRows * nodeHeight + (maxRows - 1) * rowGap);
  const maxRank = Math.max(...currentGraph.nodes.map((node) => node.rank));
  const canvasWidth = padX * 2 + (maxRank + 1) * nodeWidth + maxRank * rankGap;
  const positions = new Map();
  [...ranks.entries()].forEach(([rank, items]) => {
    const columnHeight = items.length * nodeHeight + (items.length - 1) * rowGap;
    const startY = (canvasHeight - columnHeight) / 2;
    items.forEach((node, row) => {
      positions.set(node.id, {
        x: padX + rank * (nodeWidth + rankGap),
        y: startY + row * (nodeHeight + rowGap),
      });
    });
  });

  const edgeVisuals = currentGraph.edges.map((edge, index) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) return null;
    const x1 = source.x + nodeWidth;
    const y1 = source.y + nodeHeight / 2;
    const x2 = target.x;
    const y2 = target.y + nodeHeight / 2;
    const bend = Math.max(34, (x2 - x1) * .48);
    const d = `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;
    const targetNode = currentGraph.nodes.find((node) => node.id === edge.target);
    const hasNewEvidence = targetNode?.event_ids.some((eventId) => newEventIds.has(eventId));
    const hasNewFailure = hasNewEvidence && run.events.some((event) =>
      newEventIds.has(event.event_id)
      && targetNode.event_ids.includes(event.event_id)
      && event.status === "failed"
    );
    const flowing = graphMotionMode === "live" && edge.open_frontier;
    const transient = graphMotionMode === "live" && hasNewEvidence;
    const replay = graphMotionMode === "replay" && graphReplayRequested;
    return {
      ...edge, index, d, flowing, transient, replay, hasNewFailure,
      pathId: `dag-path-${index}`,
    };
  }).filter(Boolean);

  const edgeMarkup = edgeVisuals.map((edge) => {
    const markerGrade = edge.flowing ? "frontier" : edge.evidence_grade;
    return `<path id="${edge.pathId}"
      class="dag-edge ${esc(edge.evidence_grade)} ${edge.flowing ? "open-frontier" : ""} ${edge.hasNewFailure ? "failure-arrived" : ""}"
      data-edge="${esc(edge.id)}" data-source="${esc(edge.source)}" data-target="${esc(edge.target)}"
      d="${edge.d}" marker-end="url(#arrow-${esc(markerGrade)})"/>`;
  }).join("");

  const tracerMarkup = edgeVisuals.filter((edge) => edge.transient || edge.replay).map((edge) => {
    const delay = edge.replay ? edge.index * .16 : 0;
    const duration = edge.replay ? 1.1 : 1.35;
    const tracerClass = edge.hasNewFailure ? "failure" : edge.replay ? "replay" : "evidence";
    return `<circle class="dag-tracer ${tracerClass}" r="${edge.hasNewFailure ? 4 : 3.2}" opacity="0">
      <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.78;1"
               dur="${duration}s" begin="${delay}s" fill="remove"/>
      <animateMotion dur="${duration}s" begin="${delay}s" fill="remove" rotate="auto">
        <mpath href="#${edge.pathId}"/>
      </animateMotion>
    </circle>`;
  }).join("");

  const nodeMarkup = currentGraph.nodes.map((node) => {
    const position = positions.get(node.id);
    const grade = node.evidence_grade || "derived";
    const indexLabel = node.type === "stage" ? String(node.index).padStart(2, "0") : grade.slice(0, 1).toUpperCase();
    const hasNewEvidence = node.event_ids.some((eventId) => newEventIds.has(eventId));
    const hasNewFailure = hasNewEvidence && run.events.some((event) =>
      newEventIds.has(event.event_id)
      && node.event_ids.includes(event.event_id)
      && event.status === "failed"
    );
    const entering = firstGraphRender || hasNewEvidence;
    return `<g class="dag-node ${esc(node.status)} ${esc(grade)} ${entering ? "entering" : ""} ${hasNewEvidence ? "evidence-arrived" : ""} ${hasNewFailure ? "failure-arrived" : ""}"
      data-node="${esc(node.id)}"
      transform="translate(${position.x} ${position.y})" tabindex="0" role="button"
      aria-label="${esc(node.label)}: ${esc(node.subtitle)}">
      <rect class="dag-node-body" width="${nodeWidth}" height="${nodeHeight}" rx="11"/>
      <rect class="dag-node-accent" width="3" height="${nodeHeight - 20}" y="10" rx="2"/>
      <rect class="dag-node-icon-bg" x="14" y="14" width="34" height="34" rx="9"/>
      <g class="dag-node-icon" transform="translate(19 19) scale(1)" aria-hidden="true">${graphIcon(node)}</g>
      <text class="dag-node-label" x="59" y="25">${esc(tr(node.label))}</text>
      <text class="dag-node-subtitle" x="59" y="43">${esc(tr(node.subtitle))}</text>
      ${node.detail ? `<text class="dag-node-detail" x="59" y="59">${esc(tr(node.detail))}</text>` : ""}
      <text class="dag-node-grade" x="59" y="78">${esc(indexLabel)} · ${esc(tr(pretty(grade)))}</text>
      ${node.occurred_at ? `<text class="dag-node-time" x="${nodeWidth - 12}" y="79" text-anchor="end">${esc(formatTime(node.occurred_at, false))}</text>` : ""}
    </g>`;
  }).join("");

  svg.setAttribute("viewBox", `0 0 ${canvasWidth} ${canvasHeight}`);
  svg.setAttribute("width", canvasWidth);
  svg.setAttribute("height", canvasHeight);
  svg.innerHTML = `
    <defs>
      ${["observed", "derived", "inferred", "experimental", "frontier"].map((grade) => `
        <marker id="arrow-${grade}" markerWidth="8" markerHeight="8" refX="7" refY="4"
                orient="auto" markerUnits="strokeWidth">
          <path class="dag-arrow ${grade}" d="M0,0 L8,4 L0,8 z"/>
        </marker>`).join("")}
    </defs>
    <g class="dag-edges">${edgeMarkup}</g>
    <g class="dag-tracers" pointer-events="none">${tracerMarkup}</g>
    <g class="dag-nodes">${nodeMarkup}</g>`;
  graphReplayRequested = false;

  svg.querySelectorAll(".dag-node").forEach((element) => {
    const activate = () => selectGraphNode(element.dataset.node, true);
    element.addEventListener("click", activate);
    element.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
    element.addEventListener("mouseenter", () => highlightGraphNode(element.dataset.node));
    element.addEventListener("mouseleave", () => {
      if (selectedGraphNodeId) highlightGraphNode(selectedGraphNodeId);
      else clearGraphHighlight();
    });
  });
}

function connectedGraphIds(nodeId) {
  if (!currentGraph) return new Set();
  const connected = new Set([nodeId]);
  const walk = (direction) => {
    const queue = [nodeId];
    while (queue.length) {
      const current = queue.shift();
      currentGraph.edges.forEach((edge) => {
        const matches = direction === "forward" ? edge.source === current : edge.target === current;
        if (!matches) return;
        const next = direction === "forward" ? edge.target : edge.source;
        if (connected.has(next)) return;
        connected.add(next);
        queue.push(next);
      });
    }
  };
  walk("forward");
  walk("backward");
  return connected;
}

function clearGraphHighlight() {
  document.querySelectorAll(".dag-node, .dag-edge").forEach((element) => {
    element.classList.remove("selected", "related", "dimmed");
  });
}

function highlightGraphNode(nodeId) {
  const connected = connectedGraphIds(nodeId);
  document.querySelectorAll(".dag-node").forEach((element) => {
    element.classList.toggle("related", connected.has(element.dataset.node));
    element.classList.toggle("dimmed", !connected.has(element.dataset.node));
    element.classList.toggle("selected", element.dataset.node === nodeId);
  });
  document.querySelectorAll(".dag-edge").forEach((element) => {
    const related = connected.has(element.dataset.source) && connected.has(element.dataset.target);
    element.classList.toggle("related", related);
    element.classList.toggle("dimmed", !related);
  });
}

function selectGraphNode(nodeId, inspect = false) {
  selectedGraphNodeId = nodeId;
  highlightGraphNode(nodeId);
  if (!inspect || !currentGraph || !selectedRun) return;
  const node = currentGraph.nodes.find((item) => item.id === nodeId);
  if (!node) return;
  if (node.type === "stage") {
    if (node.activity_entry) {
      inspectActivityEntry(node.activity_entry, selectedRun);
    } else {
      inspectStage(
        selectedRun.stage_summary.find((item) => item.stage === node.stage),
        selectedRun.events.filter((event) => event.stage === node.stage),
        selectedRun,
        node
      );
    }
  } else {
    inspectGraphNode(node, selectedRun);
  }
}

function inspectGraphNode(node, run) {
  const events = run.events.filter((event) => node.event_ids.includes(event.event_id));
  document.querySelector("#inspector-grade").innerHTML =
    `<span class="grade-pill ${esc(node.evidence_grade)}">${esc(node.evidence_grade)}</span>`;
  document.querySelector("#inspector").className = "inspector";
  document.querySelector("#inspector").innerHTML = `
    <h3 class="inspector-title">${esc(node.label)}</h3>
    <p class="inspector-type">${esc(tr(stageLabels[node.stage]))} · ${esc(tr("concrete object"))} · ${esc(tr(pretty(node.status)))}</p>
    ${node.object ? `<section class="fact-block">
      <h4>${esc(tr("Object details"))}</h4>
      <dl class="kv">${activityObjectDetails(node.object)}</dl>
      ${node.object.content ? `<div class="report-content">
        <span>${esc(tr("Available report content"))} · ${esc(tr(node.object.content_scope || "redacted normalized excerpt"))}</span>
        <p>${esc(node.object.content)}</p>
      </div>` : ""}
    </section>` : ""}
    <section class="fact-block">
      <h4>${esc(tr("Evidence semantics"))}</h4>
      <p class="basis">${esc(node.basis)}</p>
      ${node.runtime_state_basis ? `<p class="runtime-basis">${esc(node.runtime_state_basis)}</p>` : ""}
      <dl class="kv finding-kv">
        <dt>${esc(tr("Source events"))}</dt><dd>${events.length}</dd>
        <dt>${esc(tr("Weakest grade"))}</dt><dd>${esc(tr(pretty(node.evidence_grade)))}</dd>
        <dt>${esc(tr("Failed events"))}</dt><dd>${events.filter((event) => event.status === "failed").length}</dd>
      </dl>
    </section>
    <section class="fact-block">
      <h4>Underlying facts</h4>
      <ul class="evidence-list">${events.slice(0, 12).map((event) =>
        `<li><strong>${esc(event.summary)}</strong><br>${esc(event.evidence_grade)} · ${esc(formatTime(event.occurred_at, false))}</li>`
      ).join("")}</ul>
      ${events.length > 12 ? `<p class="basis">+ ${events.length - 12} more records in the chronology.</p>` : ""}
    </section>`;
}

function renderTimeline(run) {
  const stage = document.querySelector("#event-filter").value;
  const eventType = document.querySelector("#event-type-filter").value;
  const skill = document.querySelector("#event-skill-filter").value;
  const grade = document.querySelector("#event-grade-filter").value;
  const events = run.events.filter((event) =>
    (stage === "all" || event.stage === stage)
    && (!eventType || event.event_type === eventType)
    && (!skill || event.skill_name === skill)
    && (!grade || event.evidence_grade === grade)
  );
  document.querySelector("#timeline").innerHTML = events.map((event) => `
    <button class="event ${esc(event.evidence_grade)}" type="button" data-event="${esc(event.event_id)}">
      <time>${esc(formatTime(event.occurred_at, false))}</time>
      <span class="event-dot"></span>
      <span class="event-main">
        <strong>${esc(event.summary)}</strong>
        <span>${esc(event.event_type)} · ${esc(stageLabels[event.stage] || event.stage)}</span>
      </span>
      ${event.context_only ? `<span class="event-context">run context</span>` : ""}
    </button>
  `).join("") || `<div class="empty-inspector"><p>No evidence in this stage.</p><small>This is not classified as a failure.</small></div>`;
  document.querySelectorAll(".event").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".event").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      inspectEvent(run.events.find((event) => event.event_id === button.dataset.event), run);
    });
  });
}

function relationshipFor(event, run) {
  const links = run.relationships.filter((item) => item.target_event_id === event.event_id);
  return links.find((item) => item.relationship_type === "skill_scope")
    || links.find((item) => item.relationship_type === "runtime_context")
    || links[0];
}

function inspectEvent(event, run) {
  if (!event) return;
  const relation = relationshipFor(event, run);
  document.querySelector("#inspector-grade").innerHTML =
    `<span class="grade-pill ${esc(event.evidence_grade)}">${esc(event.evidence_grade)}</span>`;
  const payloadRows = Object.entries(event.payload || {}).filter(([, value]) =>
    value !== null && value !== "" && typeof value !== "object"
  );
  document.querySelector("#inspector").className = "inspector";
  document.querySelector("#inspector").innerHTML = `
    <h3 class="inspector-title">${esc(event.summary)}</h3>
    <p class="inspector-type">${esc(event.event_type)} · ${esc(stageLabels[event.stage] || event.stage)}</p>
    <section class="fact-block">
      <h4>Source fact</h4>
      <dl class="kv">
        <dt>Evidence</dt><dd>${esc(event.evidence_grade)} · confidence ${esc(event.confidence)}</dd>
        <dt>Status</dt><dd>${esc(event.status)}</dd>
        <dt>Basis</dt><dd class="basis">${esc(event.basis)}</dd>
        <dt>Locator</dt><dd class="mono">${esc(event.source_locator)}</dd>
      </dl>
    </section>
    <section class="fact-block">
      <h4>Skill attribution</h4>
      <dl class="kv">
        <dt>Relationship</dt><dd>${esc(relation?.relationship_type || "unattributed")}</dd>
        <dt>Grade</dt><dd>${esc(relation?.evidence_grade || "unknown")}</dd>
        <dt>Basis</dt><dd class="basis">${esc(relation?.basis || "No Skill relationship is recorded for this context event.")}</dd>
      </dl>
    </section>
    ${payloadRows.length ? `<section class="fact-block"><h4>Redacted payload</h4><dl class="kv">${
      payloadRows.map(([key, value]) => `<dt>${esc(key)}</dt><dd class="mono">${esc(value)}</dd>`).join("")
    }</dl></section>` : ""}
    <details class="raw-record">
      <summary>Show redacted normalized JSON</summary>
      <pre>${esc(JSON.stringify(event, null, 2))}</pre>
    </details>
  `;
}

function inspectStage(stage, events, run, graphNode = null) {
  const grade = stage.evidence_grade || (stage.status === "unsupported" ? "unsupported" : "unknown");
  document.querySelector("#inspector-grade").innerHTML =
    `<span class="grade-pill ${esc(grade)}">${esc(grade)}</span>`;
  const capability = run.adapter_capabilities[stage.stage] || "unsupported";
  document.querySelector("#inspector").className = "inspector";
  document.querySelector("#inspector").innerHTML = `
    <h3 class="inspector-title">${esc(stageLabels[stage.stage] || stage.stage)}</h3>
    <p class="inspector-type">Lifecycle stage · ${esc(stage.status)}</p>
    <section class="fact-block">
      <h4>Observability</h4>
      <dl class="kv">
        <dt>Events</dt><dd>${esc(stage.event_count)}</dd>
        <dt>Capability</dt><dd>${esc(capability)}</dd>
        <dt>Status</dt><dd>${esc(stage.status)}</dd>
      </dl>
    </section>
    <section class="fact-block">
      <h4>Interpretation</h4>
      <p class="basis">${stage.status === "unsupported"
        ? "This adapter cannot observe this lifecycle boundary. No conclusion is made."
        : stage.status === "not_observed"
          ? "The adapter could observe this signal, but no matching evidence was found. This is a gap, not proof of failure."
          : `${events.length} evidence record(s) support this lifecycle stage.`}</p>
      ${graphNode?.runtime_state_basis ? `<p class="runtime-basis">${esc(graphNode.runtime_state_basis)}</p>` : ""}
    </section>
  `;
}

function resetInspector() {
  document.querySelector("#inspector-grade").innerHTML = "";
  document.querySelector("#inspector").className = "inspector empty-inspector";
  document.querySelector("#inspector").innerHTML = `
    <div class="inspector-orbit"></div>
    <p>Select a lifecycle node or timeline event.</p>
    <small>Source facts and attribution are shown separately.</small>`;
}

function renderCapabilities(run) {
  document.querySelector("#capabilities").innerHTML = `
    <h4>${esc(run.adapter)} adapter capability</h4>
    ${Object.entries(run.adapter_capabilities).map(([stage, capability]) => `
      <div class="cap-row">
        <span>${esc(stageLabels[stage] || stage)}</span>
        <span class="${esc(capability)}">${esc(capability)}</span>
      </div>
    `).join("")}`;
}

document.querySelector("#run-filter").addEventListener("input", renderRuns);
[
  "#run-agent-filter",
  "#run-project-filter",
  "#run-skill-filter",
  "#run-grade-filter",
  "#run-date-filter",
  "#run-error-filter",
].forEach((selector) => {
  document.querySelector(selector).addEventListener("change", renderRuns);
});
document.querySelector("#skill-filter").addEventListener("input", renderSkills);
document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view, true));
});
document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    statusFilter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach((item) => item.classList.toggle("active", item === button));
    renderRuns();
  });
});
[
  "#event-filter",
  "#event-type-filter",
  "#event-skill-filter",
  "#event-grade-filter",
].forEach((selector) => {
  document.querySelector(selector).addEventListener("change", () => {
    if (selectedRun) renderTimeline(selectedRun);
  });
});
document.querySelector("#refresh").addEventListener("click", () => {
  loadIndex().catch(showLoadError);
});
document.querySelector("#back-to-runs").addEventListener("click", () => showRunIndex(true));
document.querySelector("#compare-toggle").addEventListener("click", () => {
  document.querySelector("#compare-panel").classList.toggle("hidden");
});
document.querySelector("#compare-target").addEventListener("change", (event) => {
  selectedComparisonId = event.target.value;
});
document.querySelector("#compare-axis").addEventListener("change", () => {
  if (selectedRun) renderComparePicker(selectedRun);
});
document.querySelector("#compare-run").addEventListener("click", () => {
  loadComparison().catch(showLoadError);
});
document.querySelector("#save-settings").addEventListener("click", () => {
  saveRuntimeSettings().catch((error) => {
    document.querySelector("#settings-save-state").textContent = error.message;
  });
});
document.querySelector("#delete-run").addEventListener("click", () => {
  deleteSelectedRun().catch(showLoadError);
});
document.querySelectorAll(".motion-mode").forEach((button) => {
  button.addEventListener("click", () => {
    graphMotionMode = button.dataset.motion;
    graphReplayRequested = graphMotionMode === "replay";
    if (selectedRun) renderPanorama(selectedRun);
  });
});
document.querySelector("#dag-reset").addEventListener("click", () => {
  document.querySelector("#dag-scroll").scrollTo({left: 0, behavior: "smooth"});
  selectedGraphNodeId = null;
  clearGraphHighlight();
  resetInspector();
});
window.addEventListener("popstate", () => {
  if (location.hash.startsWith("#/runs/")) {
    const runId = decodeURIComponent(location.hash.slice("#/runs/".length));
    loadSkillRun(runId, false).catch(showLoadError);
  } else if (location.hash === "#/skills") {
    setView("skills", false);
  } else if (location.hash === "#/settings") {
    setView("settings", false);
  } else {
    showRunIndex(false);
  }
});

function showLoadError(error) {
  document.querySelector("#run-count").textContent = "!";
  document.querySelector("#runs").innerHTML =
    `<div class="empty-inspector"><p>Unable to read the local index.</p><small>${esc(error.message)}</small></div>`;
}

loadIndex().then(connectRuntimeStream).catch(showLoadError);
setInterval(() => {
  if (!streamConnected && document.visibilityState === "visible") {
    loadIndex(true).catch(() => {});
  }
}, 12000);
