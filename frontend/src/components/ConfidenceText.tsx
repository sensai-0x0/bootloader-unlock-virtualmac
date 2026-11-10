import "./ConfidenceText.css";
import type { ReactNode } from "react";
import type { FindingConfidence } from "../data/types";

/**
 * Wraps a value with a visible degradation when it wasn't fully measured —
 * see ConfidenceText.css. A `measured` value renders completely plain: no
 * wrapper, no texture, because the honest default is to show nothing extra
 * at all.
 */
export function ConfidenceText({
  confidence,
  children,
}: {
  confidence: FindingConfidence;
  children: ReactNode;
}) {
  if (confidence === "measured") {
    return <>{children}</>;
  }
  return (
    <span className="confidence-text" data-confidence={confidence}>
      {children}
    </span>
  );
}
