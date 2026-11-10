import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
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

  test("the glyph itself carries no text — the exact score is behind the loupe, not inline", () => {
    const { container } = render(<SeverityGlyph score={{ reachability: 3, weight: 1, blastRadius: 3 }} />);
    expect(container.querySelector(".severity")?.textContent).toBe("");
  });

  test("focusing the glyph reveals the exact score string via the loupe", async () => {
    const { container, getByText } = render(
      <SeverityGlyph score={{ reachability: 3, weight: 1, blastRadius: 3 }} />,
    );
    const trigger = container.querySelector(".loupe-trigger");
    expect(trigger).not.toBeNull();

    fireEvent.focus(trigger!);

    await waitFor(() => expect(getByText("9 (3×1×3)")).toBeDefined());
  });

  test("defaults to measured (no degradation) when confidence is omitted", () => {
    const { container } = render(<SeverityGlyph score={{ reachability: 3, weight: 1, blastRadius: 3 }} />);
    expect(container.querySelector(".confidence-text")).toBeNull();
  });

  test("an untrusted-read score degrades both the glyph and the loupe's revealed value", async () => {
    const { container, getByText } = render(
      <SeverityGlyph score={{ reachability: 3, weight: 1, blastRadius: 3 }} confidence="untrusted-read" />,
    );
    expect(container.querySelector(".severity")?.closest(".confidence-text")).not.toBeNull();

    fireEvent.focus(container.querySelector(".loupe-trigger")!);

    await waitFor(() => {
      const revealed = getByText("9 (3×1×3)");
      expect(revealed.closest(".confidence-text")?.getAttribute("data-confidence")).toBe(
        "untrusted-read",
      );
    });
  });
});
