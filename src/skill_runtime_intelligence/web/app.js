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

let skillRuns = [];
let selectedRunId = null;
let selectedRun = null;
let statusFilter = "all";

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const formatTime = (value, includeDate = true) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return String(value);
  return includeDate
    ? date.toLocaleString([], {month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit"})
    : date.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
};

const pretty = (value) => String(value || "unknown").replaceAll("_", " ");

async function getJSON(path) {
  const response = await fetch(path, {cache: "no-store"});
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function loadIndex(isBackground = false) {
  const previousSelected = skillRuns.find((run) => run.skill_run_id === selectedRunId);
  const [runsResponse, sourcesResponse] = await Promise.all([
    getJSON("/api/skill-runs"),
    getJSON("/api/sources"),
  ]);
  skillRuns = runsResponse.skill_runs || [];
  const sources = sourcesResponse.sources || [];
  document.querySelector("#source-summary").textContent = sources.length
    ? `${sources.length} adapter${sources.length === 1 ? "" : "s"} · ${sources.map((source) => source.adapter).join(", ")}`
    : "No runtime source indexed";
  renderRuns();
  if (!selectedRunId && skillRuns.length) {
    await loadSkillRun(skillRuns[0].skill_run_id);
  } else if (selectedRunId && !isBackground) {
    await loadSkillRun(selectedRunId);
  } else if (selectedRunId && isBackground) {
    const currentSelected = skillRuns.find((run) => run.skill_run_id === selectedRunId);
    const previousSignature = previousSelected
      ? `${previousSelected.event_count}:${previousSelected.status}:${previousSelected.evidence_completeness}`
      : "";
    const currentSignature = currentSelected
      ? `${currentSelected.event_count}:${currentSelected.status}:${currentSelected.evidence_completeness}`
      : "";
    if (currentSelected && currentSignature !== previousSignature) {
      await loadSkillRun(selectedRunId);
    }
  }
}

function visibleRuns() {
  const query = document.querySelector("#run-filter").value.toLowerCase().trim();
  return skillRuns.filter((run) => {
    const matchesStatus = statusFilter === "all" || run.status === statusFilter;
    const haystack = [
      run.name, run.description, run.session_title, run.cwd, run.adapter,
      run.model, run.activation_mode,
    ].join(" ").toLowerCase();
    return matchesStatus && (!query || haystack.includes(query));
  });
}

function renderRuns() {
  const visible = visibleRuns();
  document.querySelector("#run-count").textContent = visible.length;
  document.querySelector("#runs").innerHTML = visible.map((run) => `
    <button class="run-card ${esc(run.status)} ${selectedRunId === run.skill_run_id ? "active" : ""}"
            type="button" data-run="${esc(run.skill_run_id)}">
      <div class="card-top">
        <span class="card-source">${esc(run.adapter)} · ${esc(pretty(run.activation_mode))}</span>
        <span class="card-time">${esc(formatTime(run.started_at))}</span>
      </div>
      <h3>${esc(run.name)}</h3>
      <p class="card-task">${esc(run.session_title || "Untitled runtime context")}</p>
      <div class="card-foot">
        <div class="mini-coverage" title="Evidence coverage ${esc(run.evidence_completeness)}%">
          <i style="width:${Number(run.evidence_completeness) || 0}%"></i>
        </div>
        <span>${esc(run.evidence_completeness)}% · ${esc(run.event_count)} events</span>
      </div>
    </button>
  `).join("") || `<div class="empty-inspector"><p>No matching SkillRuns.</p><small>Sessions without Skill evidence are intentionally excluded.</small></div>`;
  document.querySelectorAll(".run-card").forEach((button) => {
    button.addEventListener("click", () => loadSkillRun(button.dataset.run));
  });
}

async function loadSkillRun(skillRunId) {
  selectedRunId = skillRunId;
  renderRuns();
  selectedRun = await getJSON(`/api/skill-runs/${encodeURIComponent(skillRunId)}`);
  document.querySelector("#empty-detail").classList.add("hidden");
  document.querySelector("#run-detail").classList.remove("hidden");
  renderDetail(selectedRun);
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
  document.querySelector("#metric-activation").textContent = pretty(run.activation_mode);
  document.querySelector("#metric-activation-grade").textContent =
    `${pretty(run.evidence_grade)} evidence`;
  document.querySelector("#metric-events").textContent = run.events.length;
  document.querySelector("#metric-relationships").textContent =
    `${run.relationships.length} attribution edges`;
  document.querySelector("#metric-gap").textContent = run.first_gap
    ? stageLabels[run.first_gap] || pretty(run.first_gap)
    : "No gap";
  document.querySelector("#narrative").textContent = run.narrative;
  renderPanorama(run);
  renderTimeline(run);
  renderCapabilities(run);
  resetInspector();
}

function renderPanorama(run) {
  const eventsByStage = Object.fromEntries(
    Object.keys(stageLabels).map((stage) => [
      stage,
      run.events.filter((event) => event.stage === stage),
    ])
  );
  document.querySelector("#panorama").innerHTML = run.stage_summary.map((stage, index) => {
    const note = stage.status === "unsupported"
      ? "adapter unsupported"
      : stage.status === "not_observed"
        ? "not observed"
        : `${stage.evidence_grade || "mixed"} evidence`;
    return `
      <button class="stage ${esc(stage.status)}" type="button" data-stage="${esc(stage.stage)}">
        <span class="stage-index">0${index + 1}</span>
        <span class="stage-name">${esc(stageLabels[stage.stage] || stage.stage)}</span>
        <strong class="stage-value">${stage.event_count || "—"}</strong>
        <span class="stage-note">${esc(note)}</span>
      </button>`;
  }).join("");
  document.querySelectorAll(".stage").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".stage").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      inspectStage(
        run.stage_summary.find((item) => item.stage === button.dataset.stage),
        eventsByStage[button.dataset.stage] || [],
        run
      );
    });
  });
}

function renderTimeline(run) {
  const stage = document.querySelector("#event-filter").value;
  const events = run.events.filter((event) => stage === "all" || event.stage === stage);
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
  `;
}

function inspectStage(stage, events, run) {
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
document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    statusFilter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach((item) => item.classList.toggle("active", item === button));
    renderRuns();
  });
});
document.querySelector("#event-filter").addEventListener("change", () => {
  if (selectedRun) renderTimeline(selectedRun);
});
document.querySelector("#refresh").addEventListener("click", () => {
  loadIndex().catch(showLoadError);
});

function showLoadError(error) {
  document.querySelector("#run-count").textContent = "!";
  document.querySelector("#runs").innerHTML =
    `<div class="empty-inspector"><p>Unable to read the local index.</p><small>${esc(error.message)}</small></div>`;
}

loadIndex().catch(showLoadError);
setInterval(() => {
  if (document.visibilityState === "visible") {
    loadIndex(true).catch(() => {});
  }
}, 4000);
