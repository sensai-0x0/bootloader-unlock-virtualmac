import type { AgentSession } from "./types";

/**
 * Illustrative sample data only — see ../../../design/README.md. Shaped to
 * projects/04-agentic-serving-layer/'s real Session model and WebSocket
 * frame types, not a live connection to that service (it isn't running
 * here, and wiring it would mean handling its bearer-token auth and CORS —
 * a separate decision, not made here).
 */
export const sampleSessions: AgentSession[] = [
  {
    id: "sess-7f21a9",
    track: "bootloader",
    workspacePath: "/workspaces/sess-7f21a9",
    status: "active",
    createdAt: "2026-11-15T01:02:11Z",
    lastActivityAt: "2026-11-15T01:06:44Z",
    events: [
      { type: "tool_use", ts: "2026-11-15T01:06:40Z", summary: "called evaluate_boot_state" },
      {
        type: "tool_result",
        ts: "2026-11-15T01:06:42Z",
        summary: "returned BootState — security_mode Full, posture_confidence measured",
      },
      {
        type: "assistant_delta",
        ts: "2026-11-15T01:06:44Z",
        summary: "“The target container is Full with SSV enabled, no custom kernel…”",
      },
    ],
  },
  {
    id: "sess-3c08e5",
    track: "vuln-research",
    workspacePath: "/workspaces/sess-3c08e5",
    status: "idle",
    createdAt: "2026-11-15T00:41:02Z",
    lastActivityAt: "2026-11-15T00:58:19Z",
    events: [
      { type: "tool_use", ts: "2026-11-15T00:57:50Z", summary: "called read_knowledge_index" },
      {
        type: "tool_result",
        ts: "2026-11-15T00:57:53Z",
        summary: "returned 6 knowledge entries, 3 open sweep-report findings",
      },
      { type: "tool_use", ts: "2026-11-15T00:58:10Z", summary: "called run_static_analysis" },
      {
        type: "tool_result",
        ts: "2026-11-15T00:58:19Z",
        summary: "clippy clean, fmt clean, ci_guards.sh: 3/3 passed",
      },
    ],
  },
  {
    id: "sess-a610d2",
    track: "vuln-research",
    workspacePath: "/workspaces/sess-a610d2",
    status: "disconnected",
    createdAt: "2026-11-14T22:15:30Z",
    lastActivityAt: "2026-11-14T23:02:08Z",
    events: [
      {
        type: "tool_use",
        ts: "2026-11-14T23:01:40Z",
        summary: "called execute_in_environment (vm-sec-research-25D125)",
      },
      {
        type: "error",
        ts: "2026-11-14T23:02:08Z",
        summary: "environment profile approved_for did not include this track — refused",
      },
    ],
  },
  {
    id: "sess-901fb4",
    track: "bootloader",
    workspacePath: "/workspaces/sess-901fb4",
    status: "closed",
    createdAt: "2026-11-14T19:03:00Z",
    lastActivityAt: "2026-11-14T19:11:52Z",
    events: [
      { type: "tool_use", ts: "2026-11-14T19:11:40Z", summary: "called write_evidence_report" },
      {
        type: "tool_result",
        ts: "2026-11-14T19:11:48Z",
        summary: "wrote evidence/2026-11-14-191148/report.json",
      },
      { type: "session_closed", ts: "2026-11-14T19:11:52Z", summary: "closed after disconnect grace expired" },
    ],
  },
];
