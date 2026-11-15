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

/**
 * projects/04-agentic-serving-layer/ — persistent multi-turn agent sessions
 * over bootloader/vuln-research tools, reachable over HTTP + WebSocket.
 * The one genuinely live/monitorable workflow in this app; everything
 * above this is a point-in-time snapshot.
 */
export type SessionTrack = "bootloader" | "vuln-research";
export type SessionStatus = "active" | "idle" | "disconnected" | "closed";
export type SessionEventType =
  | "assistant_delta"
  | "tool_use"
  | "tool_result"
  | "interrupt_ack"
  | "error"
  | "session_closed";

export interface SessionEvent {
  type: SessionEventType;
  ts: string;
  /** A human synopsis, not the raw frame payload — a ledger, not a debug console. */
  summary: string;
}

export interface AgentSession {
  id: string;
  track: SessionTrack;
  workspacePath: string;
  status: SessionStatus;
  createdAt: string;
  lastActivityAt: string;
  events: SessionEvent[];
}

/**
 * projects/supervisor-agent/ — fuses state across the whole research
 * portfolio into ranked "do next" recommendations and dispatch tickets.
 * Never executes anything itself; every dispatch stays gated behind a
 * human decision.
 */
export type InitiativeKind =
  | "project1_fuzz"
  | "project2_mutation"
  | "project3_drift"
  | "vulnres_suite"
  | "supervisor"
  | "vm_sec_research";

export type InitiativeStatus = "pre-build" | "active" | "blocked" | "concluded";

export type PhaseName = "recon" | "build" | "execute" | "triage-learn" | "persist-report";
export type PhaseState = "green" | "stale" | "blocked" | "in-progress" | "never-run";

export interface Initiative {
  id: string;
  name: string;
  kind: InitiativeKind;
  status: InitiativeStatus;
  phases: Record<PhaseName, PhaseState>;
}

export interface Recommendation {
  rank: number;
  initiativeId: string;
  scoreTotal: number;
  scoreStaleness: number;
  scoreBlast: number;
  scoreReadiness: number;
  scorePrecedent: number;
  requiredGate: ApprovalClass;
}

export type ApprovalClass = "autonomous" | "user_gated" | "gated_plus_1tr";
export type DispatchApprovalStatus = "pending" | "approved" | "rejected";

export interface DispatchTicket {
  id: string;
  initiativeId: string;
  scopeInvariants: string;
  requiredGate: ApprovalClass;
  approvalStatus: DispatchApprovalStatus;
  approvedBy?: string;
  approvedAt?: string;
  executedAt?: string;
}
