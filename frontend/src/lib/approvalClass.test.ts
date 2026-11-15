import { describe, expect, test } from "bun:test";
import { approvalClassVisual, dispatchStatusVisual } from "./approvalClass";
import type { ApprovalClass, DispatchApprovalStatus } from "../data/types";

// StatusTick stamps "fixed"/"disclosed-upstream" with a hardcoded
// "FIXED"/"DISCLOSED" graphic the `label` override can't suppress — never
// return either from these mappers.
const STAMPING_STATUSES = new Set(["fixed", "disclosed-upstream"]);

describe("approvalClassVisual", () => {
  test("never returns a stamping status for any gate", () => {
    const gates: ApprovalClass[] = ["autonomous", "user_gated", "gated_plus_1tr"];
    for (const gate of gates) {
      expect(STAMPING_STATUSES.has(approvalClassVisual(gate))).toBe(false);
    }
  });
  test("the hardest gate (1TR) borrows the escalated-to-human visual", () => {
    expect(approvalClassVisual("gated_plus_1tr")).toBe("escalated-to-human");
  });

  test("autonomous borrows the open/safe visual", () => {
    expect(approvalClassVisual("autonomous")).toBe("open");
  });
});

describe("dispatchStatusVisual", () => {
  test("never returns a stamping status for any approval status", () => {
    const statuses: DispatchApprovalStatus[] = ["pending", "approved", "rejected"];
    for (const status of statuses) {
      expect(STAMPING_STATUSES.has(dispatchStatusVisual(status))).toBe(false);
    }
  });

  test("pending borrows escalated-to-human — it genuinely needs a human decision", () => {
    expect(dispatchStatusVisual("pending")).toBe("escalated-to-human");
  });

  test("approved borrows open, rejected borrows false-positive (ruled out, not an error)", () => {
    expect(dispatchStatusVisual("approved")).toBe("open");
    expect(dispatchStatusVisual("rejected")).toBe("false-positive");
  });
});
