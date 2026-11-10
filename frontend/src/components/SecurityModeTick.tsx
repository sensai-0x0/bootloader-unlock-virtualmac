import "./SecurityModeTick.css";
import type { SecurityMode } from "../data/types";

export function SecurityModeTick({ mode }: { mode: SecurityMode }) {
  return (
    <span className="security-mode" data-mode={mode}>
      <span className="tick" />
      {mode}
    </span>
  );
}
