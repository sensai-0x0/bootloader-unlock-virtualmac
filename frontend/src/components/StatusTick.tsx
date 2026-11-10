import "./StatusTick.css";
import { StampMark } from "./StampMark";
import type { FindingStatus } from "../data/types";

const STAMP_LABEL: Partial<Record<FindingStatus, string>> = {
  fixed: "FIXED",
  "disclosed-upstream": "DISCLOSED",
};

/**
 * `label` overrides the displayed text while keeping `status`'s visual
 * grammar (tick shape, color, stamp) — lets other domains (the invariants
 * checklist's held/violated, a plan preview's "requires 1TR + owner
 * confirmation") borrow this component's look without claiming to be a
 * literal `FindingStatus`.
 */
export function StatusTick({ status, label }: { status: FindingStatus; label?: string }) {
  const stampLabel = STAMP_LABEL[status];
  return (
    <span className="status" data-status={status}>
      <span className="tick" />
      {label ?? status}
      {stampLabel && <StampMark label={stampLabel} />}
    </span>
  );
}
