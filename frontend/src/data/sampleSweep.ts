import type { Finding, Sweep, SweepHistoryEntry } from "./types";

/**
 * Illustrative sample data only — assembled from real finding slugs and
 * vocabulary seen in vuln_res/sweep-reports/, not a snapshot of the live
 * findings store. See ../../../design/README.md.
 */

const findings: Finding[] = [
  {
    id: "2026-11-11-001/security-mode-full-contains-whole-blob",
    target: 'state::collect::parse_security_mode — unanchored "Full" substring match',
    source: "static-analysis",
    classification: "logic-divergence",
    score: { reachability: 3, weight: 1, blastRadius: 3 },
    status: "fixed",
    technicalDetail:
      'parse_security_mode matched "Full" anywhere in the bputil -d blob instead of anchoring to the "Security Mode:" line, so a decoy token elsewhere in the dump could flip the reading.',
    reproduction: "tests/fixtures/bputil_d_reduced_VM_VIRTUALIZED.txt + appended decoy line",
    resolution: "match anchored to the summary line; regression test added",
  },
  {
    id: "2026-11-10-001/ssv-enabled-contains-whole-blob",
    target: "state::collect — csrutil SSV read, same unanchored-match class",
    source: "fuzzer-confirmed",
    classification: "logic-divergence",
    score: { reachability: 2, weight: 1, blastRadius: 3 },
    status: "fixed",
    technicalDetail:
      "Same unanchored-substring class as above, on the SSV status line. Found first; the Full-mode case was located by pattern after this one was confirmed.",
    reproduction: "minimized to a single-line stdin fixture",
    resolution: "same anchoring fix, applied to both parsers in one pass",
  },
  {
    id: "2026-11-11-001/verify-baseline-no-size-cap",
    target: "verify --baseline — no size cap on the supplied file",
    source: "static-analysis",
    classification: "hang",
    score: { reachability: 2, weight: 1, blastRadius: 2 },
    status: "open",
    technicalDetail:
      "The --baseline JSON file is read fully into memory before any size check. A large supplied file can exhaust memory before validation runs.",
    chainingNotes: "none identified",
  },
  {
    id: "2026-11-11-001/ci-guards-regex-boundary-gaps",
    target: "ci_guards.sh — regex boundary allows a near-miss subprocess call to pass",
    source: "real-data-verification",
    classification: "logic-divergence",
    score: { reachability: 3, weight: 1, blastRadius: 3 },
    status: "escalated-to-human",
    technicalDetail:
      "The no-direct-subprocess CI guard's regex has a word-boundary gap that a renamed import could slip through. Confirmed against a constructed real-data case, not just a synthetic one.",
    chainingNotes:
      "would need to combine with a reviewer missing the new import — flagged for a human call on whether the guard itself needs a rewrite or a second, stricter guard added alongside it.",
    resolution: "awaiting owner decision — see sweep-reports/2026-11-11-001-host-independent-parsing-hardening/",
  },
];

export const currentSweep: Sweep = {
  id: "2026-11-11-001-host-independent-parsing-hardening",
  label: "host-independent parsing hardening",
  durationMinutes: 41,
  agentsRun: ["recon", "triage", "exploit-dev"],
  environment: "disposable-vm, torn down",
  findings,
};

export const sweepHistory: SweepHistoryEntry[] = [
  { sweepId: "2026-11-10-002-fallback-and-audit", fixedCount: 2 },
  { sweepId: "2026-11-10-001-recon-verification", fixedCount: 1 },
];

export const knowledgeEntriesRecorded = 6;
