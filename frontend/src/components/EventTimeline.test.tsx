import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { EventTimeline } from "./EventTimeline";
import type { SessionEvent } from "../data/types";

afterEach(cleanup);

const events: SessionEvent[] = [
  { type: "tool_use", ts: "2026-11-15T01:06:40Z", summary: "called evaluate_boot_state" },
  { type: "error", ts: "2026-11-15T01:06:42Z", summary: "something went wrong" },
];

describe("EventTimeline", () => {
  test("renders a synopsis and the time-of-day for every event, in order", () => {
    const { getAllByRole } = render(<EventTimeline events={events} />);
    const rows = getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]?.textContent).toContain("called evaluate_boot_state");
    expect(rows[0]?.textContent).toContain("01:06:40");
  });

  test("tags each row with its event type for the type-colored CSS rules", () => {
    const { getAllByRole } = render(<EventTimeline events={events} />);
    const rows = getAllByRole("listitem");
    expect(rows[0]?.getAttribute("data-event")).toBe("tool_use");
    expect(rows[1]?.getAttribute("data-event")).toBe("error");
  });
});
