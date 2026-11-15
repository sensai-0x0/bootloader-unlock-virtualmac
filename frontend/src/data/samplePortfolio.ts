import type { DispatchTicket, Initiative, Recommendation } from "./types";

/**
 * Illustrative sample data only — see ../../../design/README.md. Shaped to
 * projects/supervisor-agent/'s real schema (db/schema.sql): six initiative
 * kinds, the same five phases v_phase_coverage tracks, and the four-
 * component score formula from db/queries/q-scoring.sql. Not a read of the
 * real state/portfolio.db.
 */
export const initiatives: Initiative[] = [
  {
    id: "vulnres-suite",
    name: "vuln_res/ research suite",
    kind: "vulnres_suite",
    status: "active",
    phases: { recon: "green", build: "green", execute: "green", "triage-learn": "green", "persist-report": "green" },
  },
  {
    id: "supervisor",
    name: "supervisor-agent",
    kind: "supervisor",
    status: "active",
    phases: {
      recon: "green",
      build: "green",
      execute: "green",
      "triage-learn": "in-progress",
      "persist-report": "green",
    },
  },
  {
    id: "vm-sec-research",
    name: "VM boot-security research",
    kind: "vm_sec_research",
    status: "active",
    phases: { recon: "green", build: "stale", execute: "stale", "triage-learn": "stale", "persist-report": "green" },
  },
  {
    id: "project1-fuzz",
    name: "continuous fuzz bug hunter",
    kind: "project1_fuzz",
    status: "pre-build",
    phases: {
      recon: "never-run",
      build: "never-run",
      execute: "never-run",
      "triage-learn": "never-run",
      "persist-report": "never-run",
    },
  },
  {
    id: "project2-mutation",
    name: "gated mutation engine",
    kind: "project2_mutation",
    status: "blocked",
    phases: { recon: "green", build: "blocked", execute: "never-run", "triage-learn": "never-run", "persist-report": "never-run" },
  },
  {
    id: "project3-drift",
    name: "fleet drift watch",
    kind: "project3_drift",
    status: "pre-build",
    phases: {
      recon: "green",
      build: "never-run",
      execute: "never-run",
      "triage-learn": "never-run",
      "persist-report": "never-run",
    },
  },
];

export const recommendations: Recommendation[] = [
  {
    rank: 1,
    initiativeId: "vm-sec-research",
    scoreTotal: 8,
    scoreStaleness: 7,
    scoreBlast: 3,
    scoreReadiness: 9,
    scorePrecedent: 4,
    requiredGate: "user_gated",
  },
  {
    rank: 2,
    initiativeId: "vulnres-suite",
    scoreTotal: 6,
    scoreStaleness: 2,
    scoreBlast: 4,
    scoreReadiness: 6,
    scorePrecedent: 6,
    requiredGate: "autonomous",
  },
  {
    rank: 3,
    initiativeId: "project2-mutation",
    scoreTotal: 2,
    scoreStaleness: 1,
    scoreBlast: 2,
    scoreReadiness: 1,
    scorePrecedent: 1,
    requiredGate: "gated_plus_1tr",
  },
];

export const dispatchTickets: DispatchTicket[] = [
  {
    id: "2026-11-11-001/ticket-1",
    initiativeId: "vm-sec-research",
    scopeInvariants: "read-only evaluate against the paired 1TR capture only; no apply/revert",
    requiredGate: "user_gated",
    approvalStatus: "pending",
  },
  {
    id: "2026-11-11-001/ticket-2",
    initiativeId: "vulnres-suite",
    scopeInvariants: "recon + triage only, disposable environment, no exploit-dev without a second sign-off",
    requiredGate: "autonomous",
    approvalStatus: "approved",
    approvedBy: "owner",
    approvedAt: "2026-11-11T03:40:00Z",
    executedAt: "2026-11-11T04:18:00Z",
  },
  {
    id: "2026-11-10-001/ticket-3",
    initiativeId: "project2-mutation",
    scopeInvariants: "requires a hardware gate not yet present — zero approved environments",
    requiredGate: "gated_plus_1tr",
    approvalStatus: "rejected",
    approvedBy: "owner",
    approvedAt: "2026-11-10T14:02:00Z",
  },
];
