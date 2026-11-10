import type { Score } from "../data/types";

/** reachability × weight × blast-radius, per vuln_res/'s own scoring convention. */
export function scoreProduct(score: Score): number {
  return score.reachability * score.weight * score.blastRadius;
}

/** "9 (3×1×3)" — the literal format vuln_res/'s finding files use. */
export function formatScore(score: Score): string {
  return `${scoreProduct(score)} (${score.reachability}×${score.weight}×${score.blastRadius})`;
}

/**
 * Which of the three severity-glyph cells render lit. A factor of 1 is the
 * floor and renders dim; 2 or 3 render lit. (The static design/ mockup this
 * ported from applied this inconsistently — e.g. blast-radius 2 was drawn
 * dim once and lit once for the same value. This is the corrected, single
 * rule.)
 */
export function glyphCells(score: Score): [boolean, boolean, boolean] {
  return [score.reachability >= 2, score.weight >= 2, score.blastRadius >= 2];
}
