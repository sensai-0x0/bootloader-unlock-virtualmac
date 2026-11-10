import "./ScrubTimeline.css";
import type { Sweep } from "../data/types";

interface ScrubTimelineProps {
  sweeps: readonly Sweep[];
  selectedIndex: number;
  onChange: (index: number) => void;
}

/**
 * Drag a position along sweep history, rather than clicking "previous
 * sweep" (../../design/AESTHETIC.md, "the scrub timeline") — there's no
 * step to click, just a position to be at. Built on a native
 * <input type="range"> rather than hand-rolled pointer-drag math: full
 * keyboard (arrow keys) and touch support for free, styled to not look
 * like a default slider. The tick labels underneath are a pointer-only
 * shortcut on top of that already-accessible control, not the only way to
 * operate it.
 */
export function ScrubTimeline({ sweeps, selectedIndex, onChange }: ScrubTimelineProps) {
  return (
    <div className="scrub">
      <input
        type="range"
        min={0}
        max={sweeps.length - 1}
        step={1}
        value={selectedIndex}
        aria-label="sweep history — drag to view an earlier sweep"
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="scrub-ticks">
        {sweeps.map((sweep, i) => (
          <span
            key={sweep.id}
            className="tick-label"
            data-active={i === selectedIndex ? "true" : undefined}
            onClick={() => onChange(i)}
          >
            {sweep.label}
          </span>
        ))}
      </div>
    </div>
  );
}
