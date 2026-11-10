import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { SeverityGlyph } from "./SeverityGlyph";

afterEach(cleanup);

describe("SeverityGlyph", () => {
  test("renders one cell per score factor, lit per glyphCells' rule", () => {
    const { container } = render(<SeverityGlyph score={{ reachability: 3, weight: 1, blastRadius: 3 }} />);
    const cells = container.querySelectorAll(".severity span");
    expect(cells).toHaveLength(3);
    expect(cells[0]?.hasAttribute("data-lit")).toBe(true);
    expect(cells[1]?.hasAttribute("data-lit")).toBe(false);
    expect(cells[2]?.hasAttribute("data-lit")).toBe(true);
  });

  test("exposes the exact score string via title, not inline text", () => {
    const { container } = render(<SeverityGlyph score={{ reachability: 3, weight: 1, blastRadius: 3 }} />);
    const glyph = container.querySelector(".severity");
    expect(glyph?.getAttribute("title")).toBe("9 (3×1×3)");
    expect(glyph?.textContent).toBe("");
  });
});
