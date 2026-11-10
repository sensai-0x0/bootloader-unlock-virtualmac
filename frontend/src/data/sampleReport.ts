import { sampleBootState } from "./sampleBootState";
import type { InvariantName, Report } from "./types";

/**
 * Illustrative sample data only — see ../../../design/README.md. Deliberately
 * the "interesting" case (an invariant violated) rather than the more
 * common clean verify, because that's the case the invariants checklist
 * exists to render correctly: per spec/contract-spec.md, a violation after
 * the tool behaved correctly means Apple's own enforcement has a gap —
 * "that's a disclosure finding, never something to engineer around."
 */

const HELD_INVARIANTS: InvariantName[] = [
  "ReadOnlyUnlessGated",
  "Reversible",
  "NoCredentialHandling",
  "SupportedMechanismsOnly",
  "MeasuredTruth",
  "EvidenceComplete",
  "OwnershipConfirmed",
];

export const sampleReport: Report = {
  baseline: sampleBootState,
  result: {
    ...sampleBootState,
    capturedAt: "2026-11-11T02:16:33Z",
    otherContainers: [
      ...sampleBootState.otherContainers,
      { volumeGroupUuid: "F7A0-UNEXPECTED-NEW", securityMode: "Unknown" },
    ],
  },
  diff: [{ path: "other_containers", before: "1 entry", after: "2 entries" }],
  invariants: [
    ...HELD_INVARIANTS.map((name) => ({ name, held: true })),
    { name: "SingleContainerTouched" as InvariantName, held: false },
  ],
  exitCode: 13,
  evidenceBundlePath: "evidence/2026-11-11-021633/report.json",
};
