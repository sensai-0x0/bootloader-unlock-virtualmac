import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { CarbonCopyDiffRow, DiffLedger } from "./CarbonCopyDiffRow";
import type { DiffEntry } from "../data/types";

afterEach(cleanup);

const entry: DiffEntry = { path: "other_containers", before: "1 entry", after: "2 entries" };

describe("CarbonCopyDiffRow", () => {
  test("the old value is struck through, not removed — the carbon copy, not an edit", () => {
    const { getByText } = render(<CarbonCopyDiffRow entry={entry} />);
    const before = getByText("1 entry");
    expect(before.className).toBe("before");
    expect(getByText("2 entries").className).toBe("after");
  });
});

describe("DiffLedger", () => {
  test("renders one row per diff entry", () => {
    const entries: DiffEntry[] = [
      entry,
      { path: "target_container.security_mode", before: "Full", after: "Reduced" },
    ];
    const { getByText } = render(<DiffLedger entries={entries} />);
    expect(getByText("other_containers")).toBeDefined();
    expect(getByText("target_container.security_mode")).toBeDefined();
  });
});
