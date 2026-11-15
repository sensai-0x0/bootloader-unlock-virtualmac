/**
 * An event timeline packs many rows into one session's detail panel, so
 * each row shows just the time-of-day, not the full date — the session's
 * own createdAt already carries the date. Falls back to the raw string if
 * it isn't a parseable ISO timestamp, rather than showing "Invalid Date".
 */
export function formatEventTime(ts: string): string {
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) {
    return ts;
  }
  return date.toISOString().slice(11, 19);
}
