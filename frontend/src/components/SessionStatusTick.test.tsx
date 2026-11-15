import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { SessionStatusTick } from "./SessionStatusTick";

afterEach(cleanup);

describe("SessionStatusTick", () => {
  test("renders every status with its own data attribute and label", () => {
    for (const status of ["active", "idle", "disconnected", "closed"] as const) {
      const { container, getByText } = render(<SessionStatusTick status={status} />);
      expect(container.querySelector(".session-status")?.getAttribute("data-status")).toBe(status);
      expect(getByText(status)).toBeDefined();
      cleanup();
    }
  });
});
