import type { Finding, Sweep } from "./types";

/**
 * Illustrative sample data only — assembled from real finding slugs and
 * vocabulary seen in vuln_res/sweep-reports/ and this repo's own
 * CLAUDE.md/offensive-robustness report, not a snapshot of the live
 * findings store. See ../../../design/README.md.
 *
 * `sweeps` is chronological, oldest first, so the scrub timeline and the
 * phosphor trace can both read it directly with no reversing.
 */

const sweep001Findings: Finding[] = [
  {
    id: "2026-11-10-001/ssv-enabled-contains-whole-blob",
    target: "state::collect — csrutil SSV read, unanchored substring match",
    source: "fuzzer-confirmed",
    classification: "logic-divergence",
    score: { reachability: 2, weight: 1, blastRadius: 3 },
    status: "fixed",
    confidence: "measured",
    technicalDetail:
      "parse matched the SSV status anywhere in the csrutil blob instead of anchoring to its own line, so a decoy token elsewhere in the dump could flip the reading. Found first; the same-class Full-mode bug was located afterward by pattern.",
    reproduction: "minimized to a single-line stdin fixture",
    resolution: "anchoring fix, later applied to both parsers in one pass",
  },
];

const sweep002Findings: Finding[] = [
  {
    id: "2026-11-10-002/env-fallback-recovery-mislabeled",
    target: "env::detect — fallback/\"ordinary recovery\" folded into the wrong Environment variant",
    source: "real-data-verification",
    classification: "logic-divergence",
    score: { reachability: 2, weight: 1, blastRadius: 2 },
    status: "fixed",
    confidence: "measured",
    technicalDetail:
      'bputil -d\'s "OS Type" line reads "macOS (overriden)" on real hardware, not the "ordinary recovery OS" wording env::detect\'s fallback branch was written expecting — confirmed wrong against real captures, not just a stale assumption.',
    reproduction: "tests/fixtures/bputil_d_* real captures, cross-checked against progress/milestones.md",
    resolution: "detection path corrected; fallback case documented as likely real-hardware-only",
  },
  {
    id: "2026-11-10-002/audit-stale-test-counts",
    target: "CLAUDE.md and reports/evaluator/* — stale test counts (43, 55) vs actual",
    source: "static-analysis",
    classification: "logic-divergence",
    score: { reachability: 1, weight: 1, blastRadius: 1 },
    status: "fixed",
    confidence: "measured",
    technicalDetail:
      "Documentation housekeeping, not a code bug: the test counts recorded in CLAUDE.md and the evaluator reports no longer matched cargo test's actual output after several unrelated phases landed.",
    resolution: "counts corrected at each doc site as part of the same sweep's audit pass",
  },
];

const currentSweepFindings: Finding[] = [
  {
    id: "2026-11-11-001/security-mode-full-contains-whole-blob",
    target: 'state::collect::parse_security_mode — unanchored "Full" substring match',
    source: "static-analysis",
    classification: "logic-divergence",
    score: { reachability: 3, weight: 1, blastRadius: 3 },
    status: "fixed",
    confidence: "measured",
    technicalDetail:
      'parse_security_mode matched "Full" anywhere in the bputil -d blob instead of anchoring to the "Security Mode:" line, so a decoy token elsewhere in the dump could flip the reading.',
    reproduction: "tests/fixtures/bputil_d_reduced_VM_VIRTUALIZED.txt + appended decoy line",
    resolution: "match anchored to the summary line; regression test added",
  },
  {
    id: "2026-11-11-001/verify-baseline-no-size-cap",
    target: "verify --baseline — no size cap on the supplied file",
    source: "static-analysis",
    classification: "hang",
    score: { reachability: 2, weight: 1, blastRadius: 2 },
    status: "open",
    confidence: "untrusted-read",
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
    confidence: "measured",
    technicalDetail:
      "The no-direct-subprocess CI guard's regex has a word-boundary gap that a renamed import could slip through. Confirmed against a constructed real-data case, not just a synthetic one.",
    chainingNotes:
      "would need to combine with a reviewer missing the new import — flagged for a human call on whether the guard itself needs a rewrite or a second, stricter guard added alongside it.",
    resolution: "awaiting owner decision — see sweep-reports/2026-11-11-001-host-independent-parsing-hardening/",
  },
];

export const sweeps: Sweep[] = [
  {
    id: "2026-11-10-001-recon-verification",
    label: "recon verification",
    durationMinutes: 28,
    agentsRun: ["recon"],
    environment: "disposable-vm, torn down",
    findings: sweep001Findings,
  },
  {
    id: "2026-11-10-002-fallback-and-audit",
    label: "fallback and audit",
    durationMinutes: 19,
    agentsRun: ["recon", "triage"],
    environment: "disposable-vm, torn down",
    findings: sweep002Findings,
  },
  {
    id: "2026-11-11-001-host-independent-parsing-hardening",
    label: "host-independent parsing hardening",
    durationMinutes: 41,
    agentsRun: ["recon", "triage", "exploit-dev"],
    environment: "disposable-vm, torn down",
    findings: currentSweepFindings,
  },
];

export const knowledgeEntriesRecorded = 6;
