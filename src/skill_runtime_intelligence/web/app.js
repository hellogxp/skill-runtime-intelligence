const stages = [
  ["request", "Request"],
  ["discovery", "Discovery"],
  ["activation", "Activation"],
  ["instructions", "Instructions"],
  ["resources", "Resources"],
  ["execution", "Execution"],
  ["artifacts", "Artifacts"],
  ["outcome", "Outcome"],
];

let runs = [];
let selectedRun = null;

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const shortTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
};

const duration = (ms) => {
  if (ms == null) return "duration unavailable";
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`;
  return `${(ms / 60000).toFixed(1)} min`;
};

async function loadRuns() {
  const response = await fetch("/api/runs");
  const data = await response.json();
  runs = data.runs || [];
  renderRuns();
}

function renderRuns() {
  const query = document.querySelector("#run-filter").value.toLowerCase();
  const visible = runs.filter((run) =>
    [run.title, run.cwd, run.skills, run.status, run.model]
      .join(" ").toLowerCase().includes(query)
  );
  document.querySelector("#run-count").textContent =
    `${visible.length} indexed session${visible.length === 1 ? "" : "s"}`;
  document.querySelector("#runs").innerHTML = visible.map((run) => `
    <button class="run-card ${selectedRun === run.session_id ? "active" : ""}"
            data-session="${esc(run.session_id)}">
      <div class="card-top">
        <span class="eyebrow">${esc(run.adapter)} · ${esc(shortTime(run.started_at))}</span>
        <span class="badge ${esc(run.status)}">${esc(run.status)}</span>
      </div>
      <h3>${esc(run.title)}</h3>
      <div class="card-meta">
        <span>${run.skills ? esc(run.skills) : "No Skill observed"}</span>
        <span>${esc(duration(run.duration_ms))}</span>
      </div>
    </button>
  `).join("") || `<p class="muted" style="padding:16px">No matching runs.</p>`;
  document.querySelectorAll(".run-card").forEach((button) => {
    button.addEventListener("click", () => loadRun(button.dataset.session));
  });
}

async function loadRun(sessionId) {
  selectedRun = sessionId;
  renderRuns();
  const response = await fetch(`/api/runs/${encodeURIComponent(sessionId)}`);
  const run = await response.json();
  document.querySelector("#empty-detail").classList.add("hidden");
  document.querySelector("#run-detail").classList.remove("hidden");
  document.querySelector("#detail-title").textContent = run.title;
  document.querySelector("#detail-meta").textContent =
    `${run.adapter} ${run.agent_version || ""} · ${run.model || "model unavailable"} · ${run.cwd || "project unavailable"}`;
  document.querySelector("#detail-status").innerHTML =
    `<span class="badge ${esc(run.status)}">${esc(run.status)}</span>`;

  const skillNames = run.skill_runs.map((item) => `\`${item.name}\``);
  const loaded = run.events.filter((event) => event.event_type === "instruction.loaded").length;
  const tools = run.events.filter((event) => event.event_type === "tool.started").length;
  const narrative = skillNames.length
    ? `${skillNames.join(", ")} was connected to this run from exact source evidence. ` +
      `${loaded} instruction load${loaded === 1 ? "" : "s"} and ${tools} tool call${tools === 1 ? "" : "s"} were observed. ` +
      `Activation remains unknown unless the source exposed an explicit Skill invocation.`
    : `No Skill activation or exact Skill-path access was observed. ${tools} agent tool call${tools === 1 ? "" : "s"} remain visible separately.`;
  document.querySelector("#narrative").textContent = narrative;
  renderPanorama(run.events);
  renderTimeline(run.events);
  document.querySelector("#inspector").className = "inspector-body muted";
  document.querySelector("#inspector").textContent = "No event selected.";
}

function renderPanorama(events) {
  const counts = Object.fromEntries(stages.map(([key]) => [key, 0]));
  events.forEach((event) => {
    if (event.stage in counts) counts[event.stage] += 1;
  });
  document.querySelector("#panorama").innerHTML = stages.map(([key, label]) => {
    const count = counts[key];
    return `<div class="stage ${count ? "observed" : ""}">
      <span class="stage-label">${esc(label)}</span>
      <strong class="stage-value">${count || "—"}</strong>
      <span class="stage-note">${count ? "evidence records" : "not observed"}</span>
    </div>`;
  }).join("");
}

function renderTimeline(events) {
  document.querySelector("#timeline").innerHTML = events.map((event, index) => `
    <button class="event" data-event="${index}">
      <span class="event-time">${esc(shortTime(event.occurred_at).split(", ").pop())}</span>
      <span>
        <strong>${esc(event.summary)}</strong><br>
        <span class="event-type">${esc(event.event_type)} · ${esc(event.stage)}</span>
      </span>
      <span class="badge ${esc(event.evidence_grade)}">${esc(event.evidence_grade)}</span>
    </button>
  `).join("") || `<p class="muted" style="padding:16px">No supported events observed.</p>`;
  document.querySelectorAll(".event").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".event").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      inspectEvent(events[Number(button.dataset.event)]);
    });
  });
}

function inspectEvent(event) {
  const inspector = document.querySelector("#inspector");
  inspector.className = "inspector-body";
  inspector.innerHTML = `
    <h3>${esc(event.summary)}</h3>
    <dl>
      <dt>Event</dt><dd>${esc(event.event_type)}</dd>
      <dt>Evidence</dt><dd><span class="badge ${esc(event.evidence_grade)}">${esc(event.evidence_grade)}</span> confidence ${esc(event.confidence)}</dd>
      <dt>Basis</dt><dd>${esc(event.basis)}</dd>
      <dt>Status</dt><dd>${esc(event.status)}</dd>
      <dt>Source locator</dt><dd class="source">${esc(event.source_locator)}</dd>
      ${event.parent_event_id ? `<dt>Parent</dt><dd class="source">${esc(event.parent_event_id)}</dd>` : ""}
    </dl>`;
}

document.querySelector("#run-filter").addEventListener("input", renderRuns);
loadRuns().catch((error) => {
  document.querySelector("#run-count").textContent = "Unable to load local index";
  document.querySelector("#runs").innerHTML = `<p class="muted" style="padding:16px">${esc(error.message)}</p>`;
});
