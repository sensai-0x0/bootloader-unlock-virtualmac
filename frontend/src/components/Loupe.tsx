import { useEffect, useRef, useState, type ReactNode } from "react";
import "./Loupe.css";

const SHOW_DELAY_MS = 250;

interface LoupeProps {
  /** Always visible — the compact form (a glyph, a truncated value). */
  display: ReactNode;
  /** Shown magnified on hover/focus — the exact, full-precision form. */
  full: ReactNode;
  label: string;
}

/**
 * Hovering (or focusing — this works from the keyboard too, unlike a
 * native `title`) briefly magnifies the exact value, the way you'd hold a
 * loupe over a printed ledger rather than reach for a separate tool
 * (../../design/AESTHETIC.md, "the loupe"). Keeps the collapsed row
 * compact without losing precision.
 */
export function Loupe({ display, full, label }: LoupeProps) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    return () => clearTimeout(timeoutRef.current);
  }, []);

  const show = () => {
    timeoutRef.current = setTimeout(() => setVisible(true), SHOW_DELAY_MS);
  };
  const hide = () => {
    clearTimeout(timeoutRef.current);
    setVisible(false);
  };

  return (
    <span
      className="loupe-trigger"
      tabIndex={0}
      aria-label={label}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {display}
      {visible && (
        <span className="loupe-overlay" role="tooltip">
          {full}
        </span>
      )}
    </span>
  );
}
