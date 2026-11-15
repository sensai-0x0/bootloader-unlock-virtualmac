import "./SessionStatusTick.css";
import type { SessionStatus } from "../data/types";

export function SessionStatusTick({ status }: { status: SessionStatus }) {
  return (
    <span className="session-status" data-status={status}>
      <span className="tick" />
      {status}
    </span>
  );
}
