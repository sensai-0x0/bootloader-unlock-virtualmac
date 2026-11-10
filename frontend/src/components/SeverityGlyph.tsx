import "./SeverityGlyph.css";
import { ConfidenceText } from "./ConfidenceText";
import { Loupe } from "./Loupe";
import { formatScore, glyphCells } from "../lib/score";
import type { FindingConfidence, Score } from "../data/types";

export function SeverityGlyph({
  score,
  confidence = "measured",
}: {
  score: Score;
  confidence?: FindingConfidence;
}) {
  const cells = glyphCells(score);
  const formatted = formatScore(score);
  return (
    <Loupe
      label={`severity score ${formatted}`}
      display={
        <ConfidenceText confidence={confidence}>
          <span className="severity">
            {cells.map((lit, i) => (
              <span key={i} data-lit={lit ? "" : undefined} />
            ))}
          </span>
        </ConfidenceText>
      }
      full={<ConfidenceText confidence={confidence}>{formatted}</ConfidenceText>}
    />
  );
}
