import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { PlanPreview } from "./PlanPreview";
import type { PlannedTransition } from "../data/types";

afterEach(cleanup);

const plan: PlannedTransition = {
  fromMode: "Full",
  toProfile: "ReducedKexts",
  targetVolumeGroup: "TEST-VOLUME",
  commands: [["sudo", "bputil", "-m"]],
  requiresOneTrueRecoveryAndOwnerConfirmation: true,
};

describe("PlanPreview", () => {
  test("highlights both ends of the edge on the stage rule", () => {
    const { getByText } = render(<PlanPreview plan={plan} />);
    expect(getByText("Full").className).toContain("active");
    expect(getByText("ReducedKexts").className).toContain("active");
    expect(getByText("PermissiveCustomKernel").className).not.toContain("active");
  });

  test("shows the human-gate tick only when the plan requires one", () => {
    const { getByText } = render(<PlanPreview plan={plan} />);
    expect(getByText("requires 1TR + owner confirmation")).toBeDefined();

    cleanup();
    const noGate = { ...plan, requiresOneTrueRecoveryAndOwnerConfirmation: false };
    const { queryByText } = render(<PlanPreview plan={noGate} />);
    expect(queryByText("requires 1TR + owner confirmation")).toBeNull();
  });

  test("lists every command's argv in the row's detail", () => {
    const { getByText } = render(<PlanPreview plan={plan} />);
    expect(getByText("sudo bputil -m")).toBeDefined();
  });

  test("an Unknown fromMode highlights only the destination, never a guessed origin", () => {
    const unknownOrigin = { ...plan, fromMode: "Unknown" as const };
    const { getByText } = render(<PlanPreview plan={unknownOrigin} />);
    expect(getByText("ReducedKexts").className).toContain("active");
    expect(getByText("Full").className).not.toContain("active");
  });
});
