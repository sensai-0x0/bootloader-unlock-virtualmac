import "./SeverityGlyph.css";
import { formatScore, glyphCells } from "../lib/score";
import type { Score } from "../data/types";

export function SeverityGlyph({ score }: { score: Score }) {
  const cells = glyphCells(score);
  return (
    <span className="severity" title={formatScore(score)}>
      {cells.map((lit, i) => (
        <span key={i} data-lit={lit ? "" : undefined} />
      ))}
    </span>
  );
}
