import { createHash } from "node:crypto"
import { appendFileSync } from "node:fs"

const RAW_TOKEN = process.env.SRI_ATTEMPT_CORRELATION_TOKEN || ""
const EVIDENCE_PATH = process.env.SRI_ATTEMPT_CORRELATION_EVIDENCE || ""

// Remove propagation inputs before any model-requested child process starts.
delete process.env.SRI_ATTEMPT_CORRELATION_TOKEN
delete process.env.SRI_ATTEMPT_CORRELATION_EVIDENCE

function first(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && value !== "") return value
  }
  return ""
}

function sessionFromEvent(event) {
  const properties = event?.properties || {}
  const info = properties?.info || {}
  return String(first(
    properties.sessionID,
    properties.sessionId,
    properties.session_id,
    info.sessionID,
    info.sessionId,
    info.id,
  ))
}

function record(eventType, sessionID) {
  if (!RAW_TOKEN || !EVIDENCE_PATH || !sessionID) return
  try {
    appendFileSync(EVIDENCE_PATH, JSON.stringify({
      event_type: eventType,
      session_id: String(sessionID),
      token_sha256: createHash("sha256").update(RAW_TOKEN).digest("hex"),
    }) + "\n", { encoding: "utf8", mode: 0o600 })
  } catch (_) {}
}

const AttemptCorrelationPilot = async () => ({
  event: async ({ event }) => {
    if (event?.type === "session.created") {
      record("session.created", sessionFromEvent(event))
    }
  },
  "tool.execute.before": async (input) => {
    record("tool.execute.before", input?.sessionID)
  },
})

export const SkillRuntimeAttemptCorrelationPilot = AttemptCorrelationPilot
