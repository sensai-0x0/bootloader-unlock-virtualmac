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

export interface SweepHistoryEntry {
  sweepId: string;
  fixedCount: number;
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
