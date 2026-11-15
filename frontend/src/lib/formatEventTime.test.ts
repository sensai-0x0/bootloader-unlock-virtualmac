import { describe, expect, test } from "bun:test";
import { formatEventTime } from "./formatEventTime";

describe("formatEventTime", () => {
  test("extracts just the time-of-day from an ISO timestamp", () => {
    expect(formatEventTime("2026-11-15T01:06:44Z")).toBe("01:06:44");
  });

  test("falls back to the raw string for anything unparseable, never 'Invalid Date'", () => {
    expect(formatEventTime("not-a-date")).toBe("not-a-date");
  });
});
