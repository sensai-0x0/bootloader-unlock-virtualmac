import "./StampMark.css";

const HEIGHT = 16;

/**
 * A disclosed or fixed finding doesn't just change color — it gets
 * stamped, the way a physical record gets stamped
 * (../../design/AESTHETIC.md, "the stamp"). The border is a hand-perturbed
 * quadrilateral, not a clean rect, and the whole mark sits a few degrees
 * off-axis: a stamp is a one-time act, not a smooth rendered state.
 * Color comes from `currentColor`, so it always matches whatever status
 * text it sits next to.
 */
export function StampMark({ label }: { label: string }) {
  const width = Math.max(40, label.length * 6 + 8);

  return (
    <svg
      className="stamp"
      viewBox={`0 0 ${width} ${HEIGHT}`}
      width={width}
      height={HEIGHT}
      role="img"
      aria-label={`stamped: ${label}`}
    >
      <path
        d={`M3,2 L${width - 2},0.5 L${width - 0.5},${HEIGHT - 1} L1,${HEIGHT - 0.5} Z`}
        stroke="currentColor"
        strokeWidth={1}
      />
      <text x={width / 2} y={HEIGHT / 2 + 2.5} textAnchor="middle" fill="currentColor">
        {label}
      </text>
    </svg>
  );
}
