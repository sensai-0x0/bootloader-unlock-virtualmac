import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { StatusTick } from "./StatusTick";

afterEach(cleanup);

describe("StatusTick", () => {
  test("fixed and disclosed-upstream get a stamp mark", () => {
    const { container: fixed } = render(<StatusTick status="fixed" />);
    expect(fixed.querySelector(".stamp")).not.toBeNull();

    const { container: disclosed } = render(<StatusTick status="disclosed-upstream" />);
    expect(disclosed.querySelector(".stamp")).not.toBeNull();
  });

  test("open, false-positive, and escalated-to-human get no stamp", () => {
    for (const status of ["open", "false-positive", "escalated-to-human"] as const) {
      const { container } = render(<StatusTick status={status} />);
      expect(container.querySelector(".stamp")).toBeNull();
      cleanup();
    }
  });
});
