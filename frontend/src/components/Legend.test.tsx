import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { Legend } from "./Legend";

afterEach(cleanup);

describe("Legend", () => {
  test("clicking a status label toggles it, native checkbox drives state", () => {
    const onToggle = mock();
    const { getByLabelText } = render(<Legend active={[]} onToggle={onToggle} />);

    fireEvent.click(getByLabelText("open"));

    expect(onToggle).toHaveBeenCalledWith("open");
  });

  test("an active status renders its checkbox checked", () => {
    const { getByLabelText } = render(<Legend active={["fixed"]} onToggle={() => {}} />);
    expect((getByLabelText("fixed") as HTMLInputElement).checked).toBe(true);
    expect((getByLabelText("open") as HTMLInputElement).checked).toBe(false);
  });
});
