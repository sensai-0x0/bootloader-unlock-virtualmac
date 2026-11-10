import { describe, expect, test } from "bun:test";
import { formatScore, glyphCells, scoreProduct } from "./score";

describe("scoreProduct", () => {
  test("multiplies the three factors", () => {
    expect(scoreProduct({ reachability: 3, weight: 1, blastRadius: 3 })).toBe(9);
    expect(scoreProduct({ reachability: 1, weight: 1, blastRadius: 1 })).toBe(1);
  });
});

describe("formatScore", () => {
  test("matches vuln_res/'s own format", () => {
    expect(formatScore({ reachability: 3, weight: 1, blastRadius: 3 })).toBe("9 (3×1×3)");
  });
});

describe("glyphCells", () => {
  test("a factor of 1 is dim, 2 or 3 are lit", () => {
    expect(glyphCells({ reachability: 3, weight: 1, blastRadius: 3 })).toEqual([true, false, true]);
    expect(glyphCells({ reachability: 2, weight: 1, blastRadius: 2 })).toEqual([true, false, true]);
    expect(glyphCells({ reachability: 1, weight: 1, blastRadius: 1 })).toEqual([false, false, false]);
  });

  test("equal factors render the same, unlike the static mockup's inconsistent version", () => {
    const a = glyphCells({ reachability: 2, weight: 1, blastRadius: 2 });
    expect(a[0]).toBe(a[2]);
  });
});
