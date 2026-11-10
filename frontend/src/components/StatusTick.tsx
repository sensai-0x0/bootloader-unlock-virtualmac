import "./StatusTick.css";
import { StampMark } from "./StampMark";
import type { FindingStatus } from "../data/types";

const STAMP_LABEL: Partial<Record<FindingStatus, string>> = {
  fixed: "FIXED",
  "disclosed-upstream": "DISCLOSED",
};

export function StatusTick({ status }: { status: FindingStatus }) {
  const stampLabel = STAMP_LABEL[status];
  return (
    <span className="status" data-status={status}>
      <span className="tick" />
      {status}
      {stampLabel && <StampMark label={stampLabel} />}
    </span>
  );
}
