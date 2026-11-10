import "./StatusTick.css";
import type { FindingStatus } from "../data/types";

export function StatusTick({ status }: { status: FindingStatus }) {
  return (
    <span className="status" data-status={status}>
      <span className="tick" />
      {status}
    </span>
  );
}
