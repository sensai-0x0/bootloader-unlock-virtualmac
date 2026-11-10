import "./Legend.css";
import type { FindingStatus } from "../data/types";

const ALL_STATUSES: FindingStatus[] = [
  "open",
  "fixed",
  "disclosed-upstream",
  "false-positive",
  "escalated-to-human",
];

interface LegendProps {
  active: readonly FindingStatus[];
  onToggle: (status: FindingStatus) => void;
}

/**
 * The status filter IS the legend — clicking a status word toggles it as a
 * filter, no separate "filter" control. Native checkboxes drive the state
 * so toggling, keyboard focus, and screen readers all come for free.
 */
export function Legend({ active, onToggle }: LegendProps) {
  return (
    <div className="legend" role="group" aria-label="filter by status">
      {ALL_STATUSES.map((status) => (
        <span key={status}>
          <input
            type="checkbox"
            id={`legend-${status}`}
            className="legend-toggle"
            checked={active.includes(status)}
            onChange={() => onToggle(status)}
          />
          <label htmlFor={`legend-${status}`}>{status}</label>
        </span>
      ))}
    </div>
  );
}
