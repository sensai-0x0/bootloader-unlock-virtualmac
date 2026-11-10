import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { ScrubTimeline } from "./ScrubTimeline";
import type { Sweep } from "../data/types";

afterEach(cleanup);

const sweeps: Sweep[] = [
  { id: "a", label: "first", durationMinutes: 1, agentsRun: [], environment: "x", findings: [] },
  { id: "b", label: "second", durationMinutes: 1, agentsRun: [], environment: "x", findings: [] },
  { id: "c", label: "third", durationMinutes: 1, agentsRun: [], environment: "x", findings: [] },
];

describe("ScrubTimeline", () => {
  test("the range input spans the full sweep index range", () => {
    const { container } = render(<ScrubTimeline sweeps={sweeps} selectedIndex={2} onChange={() => {}} />);
    const input = container.querySelector('input[type="range"]') as HTMLInputElement;
    expect(input.min).toBe("0");
    expect(input.max).toBe("2");
    expect(input.value).toBe("2");
  });

  test("dragging the range input reports the new index", () => {
    const onChange = mock();
    const { container } = render(<ScrubTimeline sweeps={sweeps} selectedIndex={2} onChange={onChange} />);
    const input = container.querySelector('input[type="range"]')!;

    fireEvent.change(input, { target: { value: "0" } });

    expect(onChange).toHaveBeenCalledWith(0);
  });

  test("clicking a tick label jumps directly to that sweep", () => {
    const onChange = mock();
    const { getByText } = render(<ScrubTimeline sweeps={sweeps} selectedIndex={2} onChange={onChange} />);

    fireEvent.click(getByText("first"));

    expect(onChange).toHaveBeenCalledWith(0);
  });

  test("only the selected sweep's tick label is marked active", () => {
    const { getByText } = render(<ScrubTimeline sweeps={sweeps} selectedIndex={1} onChange={() => {}} />);
    expect(getByText("second").getAttribute("data-active")).toBe("true");
    expect(getByText("first").getAttribute("data-active")).toBeNull();
    expect(getByText("third").getAttribute("data-active")).toBeNull();
  });
});
