import { describe, expect, test } from "bun:test";
import { securityModeAsProfileLabel } from "./securityMode";

describe("securityModeAsProfileLabel", () => {
  test("Full, Reduced, and Permissive map onto their matching profile", () => {
    expect(securityModeAsProfileLabel("Full")).toBe("Full");
    expect(securityModeAsProfileLabel("Reduced")).toBe("ReducedKexts");
    expect(securityModeAsProfileLabel("Permissive")).toBe("PermissiveCustomKernel");
  });

  test("Unknown maps to no profile — never a guessed origin", () => {
    expect(securityModeAsProfileLabel("Unknown")).toBeNull();
  });
});
