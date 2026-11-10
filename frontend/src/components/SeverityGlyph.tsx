import "./SeverityGlyph.css";
import { Loupe } from "./Loupe";
import { formatScore, glyphCells } from "../lib/score";
import type { Score } from "../data/types";

export function SeverityGlyph({ score }: { score: Score }) {
  const cells = glyphCells(score);
  const formatted = formatScore(score);
  return (
    <Loupe
      label={`severity score ${formatted}`}
      display={
        <span className="severity">
          {cells.map((lit, i) => (
            <span key={i} data-lit={lit ? "" : undefined} />
          ))}
        </span>
      }
      full={formatted}
    />
  );
}
