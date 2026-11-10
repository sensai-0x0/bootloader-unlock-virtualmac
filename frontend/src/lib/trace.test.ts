import { describe, expect, test } from "bun:test";
import { tracePoints } from "./trace";

describe("tracePoints", () => {
  test("empty series draws nothing", () => {
    expect(tracePoints([], 100, 20)).toBe("");
  });

  test("a single value draws a flat mid-height line", () => {
    expect(tracePoints([5], 100, 20)).toBe("0,10 100,10");
  });

  test("a flat series (no range) draws a flat mid-height line, not NaN", () => {
    const points = tracePoints([3, 3, 3], 100, 20);
    expect(points).not.toContain("NaN");
    for (const pair of points.split(" ")) {
      const y = Number(pair.split(",")[1]);
      expect(y).toBe(10);
    }
  });

  test("the minimum value sits at the bottom, the maximum at the top", () => {
    const points = tracePoints([0, 10], 100, 20).split(" ");
    const firstPoint = points[0];
    const secondPoint = points[1];
    expect(firstPoint).toBeDefined();
    expect(secondPoint).toBeDefined();
    const [, firstY] = firstPoint!.split(",").map(Number);
    const [, secondY] = secondPoint!.split(",").map(Number);
    expect(firstY).toBe(20);
    expect(secondY).toBe(0);
  });

  test("spreads points evenly across the width", () => {
    const points = tracePoints([1, 2, 3], 90, 20).split(" ");
    const xs = points.map((p) => Number(p.split(",")[0]));
    expect(xs).toEqual([0, 45, 90]);
  });
});
