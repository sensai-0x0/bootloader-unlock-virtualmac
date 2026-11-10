export type FindingStatus =
  | "open"
  | "fixed"
  | "disclosed-upstream"
  | "false-positive"
  | "escalated-to-human";

export type FindingSource =
  | "static-analysis"
  | "fuzzer-confirmed"
  | "exploit-dev-chain"
  | "real-data-verification";

export type ClassificationType = "memory-safety" | "panic" | "hang" | "logic-divergence";

/**
 * Mirrors bputil-eval's own PostureConfidence vocabulary
 * (../../design/FEATURE-PLAN.md) — how certain a reading is, independent of
 * what it found. "unmeasured" exists for completeness (a legacy/default
 * state) but no live finding should actually carry it, the same way a
 * fresh BootState never reports Unmeasured.
 */
export type FindingConfidence = "measured" | "untrusted-read" | "unmeasured";

export type ScoreFactor = 1 | 2 | 3;

export interface Score {
  reachability: ScoreFactor;
  weight: ScoreFactor;
  blastRadius: ScoreFactor;
}

export interface Finding {
  id: string;
  target: string;
  source: FindingSource;
  classification: ClassificationType;
  score: Score;
  status: FindingStatus;
  confidence: FindingConfidence;
  technicalDetail: string;
  reproduction?: string;
  chainingNotes?: string;
  resolution?: string;
}

export interface Sweep {
  id: string;
  label: string;
  durationMinutes: number;
  agentsRun: string[];
  environment: string;
  findings: Finding[];
}

export interface Exploit {
  id: string;
  title: string;
  target: string;
  techniqueSource: string;
  impact: string;
  status: FindingStatus;
  sweepId: string;
  chainingNotes: string;
}

/**
 * bputil-eval's own evaluator contracts (spec/contract-spec.md via
 * ../../design/FEATURE-PLAN.md), not vuln_res/'s. Same `FindingConfidence`
 * values, contract-spec.md's own name for the field.
 */
export type PostureConfidence = FindingConfidence;

export type SecurityMode = "Full" | "Reduced" | "Permissive" | "Unknown";

export interface TargetContainer {
  securityMode: SecurityMode;
  ssvEnabled: boolean;
  allowsCustomKernel: boolean;
  allowsThirdPartyKexts: boolean;
}

export type ObjectRole = "LLB" | "iBoot" | "KernelCache" | "AuxKC" | "CustomBootObject";
export type Signer = "Apple" | "SEPLocalPolicy" | "Unknown";

export interface EnrolledObject {
  role: ObjectRole;
  signer: Signer;
  sha384: string;
}

export interface OtherContainer {
  volumeGroupUuid: string;
  securityMode: SecurityMode | "Unknown";
}

export interface BootState {
  schemaVersion: number;
  capturedAt: string;
  environment: "MacOS" | "OneTrueRecovery";
  postureConfidence: PostureConfidence;
  host: { chip: string; macosBuild: string; serialMasked: string };
  targetContainer: TargetContainer;
  enrolledObjects: EnrolledObject[];
  otherContainers: OtherContainer[];
}

/** plan()'s output — always a dry run, never executed (contract-spec.md). */
export type TargetProfile = "Full" | "ReducedKexts" | "PermissiveCustomKernel";

export interface PlannedTransition {
  fromMode: SecurityMode;
  toProfile: TargetProfile;
  targetVolumeGroup: string;
  /** Each entry is one command's argv. */
  commands: string[][];
  /** Always true for any mutating profile per contract-spec.md's PlannedTransition.requires. */
  requiresOneTrueRecoveryAndOwnerConfirmation: boolean;
}

/** The exact eight global invariants from spec/contract-spec.md. */
export type InvariantName =
  | "ReadOnlyUnlessGated"
  | "SingleContainerTouched"
  | "Reversible"
  | "NoCredentialHandling"
  | "SupportedMechanismsOnly"
  | "MeasuredTruth"
  | "EvidenceComplete"
  | "OwnershipConfirmed";

export interface InvariantResult {
  name: InvariantName;
  held: boolean;
}

export interface DiffEntry {
  path: string;
  before: string;
  after: string;
}

export interface Report {
  baseline: BootState;
  result: BootState | null;
  diff: DiffEntry[];
  invariants: InvariantResult[];
  exitCode: number;
  evidenceBundlePath: string;
}
