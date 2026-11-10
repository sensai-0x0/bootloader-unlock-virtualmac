import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { Loupe } from "./Loupe";

afterEach(cleanup);

describe("Loupe", () => {
  test("shows the full value after a hover delay, not instantly", async () => {
    const { container, queryByText } = render(
      <Loupe display="short" full="the full, exact value" label="example" />,
    );
    const trigger = container.querySelector(".loupe-trigger")!;

    fireEvent.mouseEnter(trigger);
    expect(queryByText("the full, exact value")).toBeNull();

    await waitFor(() => expect(queryByText("the full, exact value")).not.toBeNull());
  });

  test("hides again on mouse leave, even mid-delay", async () => {
    const { container, queryByText } = render(
      <Loupe display="short" full="the full, exact value" label="example" />,
    );
    const trigger = container.querySelector(".loupe-trigger")!;

    fireEvent.mouseEnter(trigger);
    fireEvent.mouseLeave(trigger);

    await new Promise((r) => setTimeout(r, 300));
    expect(queryByText("the full, exact value")).toBeNull();
  });

  test("keyboard focus shows it too, not just mouse hover", async () => {
    const { container, queryByText } = render(
      <Loupe display="short" full="the full, exact value" label="example" />,
    );
    const trigger = container.querySelector(".loupe-trigger")!;

    fireEvent.focus(trigger);

    await waitFor(() => expect(queryByText("the full, exact value")).not.toBeNull());
  });
});
