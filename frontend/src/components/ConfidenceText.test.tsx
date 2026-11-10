import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { ConfidenceText } from "./ConfidenceText";

afterEach(cleanup);

describe("ConfidenceText", () => {
  test("measured renders with no wrapper at all — the honest default is to add nothing", () => {
    const { container } = render(<ConfidenceText confidence="measured">plain value</ConfidenceText>);
    expect(container.querySelector(".confidence-text")).toBeNull();
    expect(container.textContent).toBe("plain value");
  });

  test("untrusted-read and unmeasured get the degraded wrapper, with the tier recorded", () => {
    const { container: untrusted } = render(
      <ConfidenceText confidence="untrusted-read">a value</ConfidenceText>,
    );
    expect(untrusted.querySelector(".confidence-text")?.getAttribute("data-confidence")).toBe(
      "untrusted-read",
    );

    const { container: unmeasured } = render(
      <ConfidenceText confidence="unmeasured">a value</ConfidenceText>,
    );
    expect(unmeasured.querySelector(".confidence-text")?.getAttribute("data-confidence")).toBe(
      "unmeasured",
    );
  });

  test("the wrapped text content is unchanged — only presentation degrades", () => {
    const { container } = render(<ConfidenceText confidence="untrusted-read">a value</ConfidenceText>);
    expect(container.textContent).toBe("a value");
  });
});
