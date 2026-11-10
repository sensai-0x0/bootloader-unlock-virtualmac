import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { SecurityModeTick } from "./SecurityModeTick";

afterEach(cleanup);

describe("SecurityModeTick", () => {
  test("Full is the only mode marked data-mode for the green-filled CSS rule to match", () => {
    const { container } = render(<SecurityModeTick mode="Full" />);
    expect(container.querySelector(".security-mode")?.getAttribute("data-mode")).toBe("Full");
  });

  test("Reduced, Permissive, and Unknown all carry their own label text", () => {
    for (const mode of ["Reduced", "Permissive", "Unknown"] as const) {
      const { getByText } = render(<SecurityModeTick mode={mode} />);
      expect(getByText(mode)).toBeDefined();
      cleanup();
    }
  });
});
