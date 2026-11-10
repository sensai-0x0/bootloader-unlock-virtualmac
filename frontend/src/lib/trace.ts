/**
 * Maps a series of values onto an SVG `points` string for a drawn line (the
 * "phosphor trace" — ../../design/AESTHETIC.md: a continuous line, never a
 * filled bar/area, for anything shown over time).
 */
export function tracePoints(values: readonly number[], width: number, height: number): string {
  if (values.length === 0) {
    return "";
  }
  if (values.length === 1) {
    return `0,${height / 2} ${width},${height / 2}`;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;
  const stepX = width / (values.length - 1);

  return values
    .map((value, i) => {
      // A flat series (range 0) draws a flat mid-height line, not a
      // divide-by-zero NaN line.
      const normalized = range === 0 ? 0.5 : (value - min) / range;
      const y = height - normalized * height;
      return `${i * stepX},${y}`;
    })
    .join(" ");
}
