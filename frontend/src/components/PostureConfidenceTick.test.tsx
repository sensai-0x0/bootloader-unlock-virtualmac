import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { PostureConfidenceTick } from "./PostureConfidenceTick";

afterEach(cleanup);

describe("PostureConfidenceTick", () => {
  test("renders the exact confidence tier as both the data attribute and the label", () => {
    for (const confidence of ["measured", "untrusted-read", "unmeasured"] as const) {
      const { container, getByText } = render(<PostureConfidenceTick confidence={confidence} />);
      expect(container.querySelector(".posture-confidence")?.getAttribute("data-confidence")).toBe(
        confidence,
      );
      expect(getByText(confidence)).toBeDefined();
      cleanup();
    }
  });
});
