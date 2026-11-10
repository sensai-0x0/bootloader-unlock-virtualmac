import "./PhosphorTrace.css";
import { tracePoints } from "../lib/trace";

const WIDTH = 120;
const HEIGHT = 20;

/**
 * A drawn line, never a filled bar/area — how this system shows anything
 * over time (../../design/AESTHETIC.md, "the phosphor trace"). Decorative
 * but literal: each point is a real value, not an illustration.
 */
export function PhosphorTrace({ values, label }: { values: readonly number[]; label: string }) {
  if (values.length < 2) {
    return null;
  }
  return (
    <svg
      className="phosphor-trace"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width={WIDTH}
      height={HEIGHT}
      role="img"
      aria-label={label}
    >
      <polyline points={tracePoints(values, WIDTH, HEIGHT)} />
    </svg>
  );
}
