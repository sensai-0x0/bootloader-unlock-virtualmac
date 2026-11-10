import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { StampMark } from "./StampMark";

afterEach(cleanup);

describe("StampMark", () => {
  test("renders the label text inside the svg", () => {
    const { getByText } = render(<StampMark label="FIXED" />);
    expect(getByText("FIXED")).toBeDefined();
  });

  test("widens for a longer label rather than clipping it", () => {
    const { container: short } = render(<StampMark label="OK" />);
    const { container: long } = render(<StampMark label="DISCLOSED" />);
    const shortWidth = Number(short.querySelector("svg")?.getAttribute("width"));
    const longWidth = Number(long.querySelector("svg")?.getAttribute("width"));
    expect(longWidth).toBeGreaterThan(shortWidth);
  });
});
