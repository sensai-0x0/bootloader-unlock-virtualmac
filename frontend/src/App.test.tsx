import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { App } from "./App";

afterEach(() => {
  cleanup();
  window.history.replaceState(null, "", "/");
});

describe("App", () => {
  test("renders the sweep & findings view by default", () => {
    const { getByText } = render(<App />);
    expect(getByText("findings opened this sweep")).toBeDefined();
  });

  test("the dial switches to the campaign overview view without a page navigation", () => {
    const { getByText } = render(<App />);

    fireEvent.click(getByText("campaign overview"));

    expect(getByText("chains with impact proven, awaiting sign-off")).toBeDefined();
    expect(window.location.pathname).toBe("/campaign");
  });

  test("the dial switches to the posture view", () => {
    const { getByText } = render(<App />);

    fireEvent.click(getByText("posture"));

    expect(getByText("target container posture")).toBeDefined();
    expect(window.location.pathname).toBe("/posture");
  });
});
