import "./PostureConfidenceTick.css";
import type { PostureConfidence } from "../data/types";

export function PostureConfidenceTick({ confidence }: { confidence: PostureConfidence }) {
  return (
    <span className="posture-confidence" data-confidence={confidence}>
      <span className="tick" />
      {confidence}
    </span>
  );
}
