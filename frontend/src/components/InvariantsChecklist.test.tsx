import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { InvariantsChecklist } from "./InvariantsChecklist";
import type { InvariantResult } from "../data/types";

afterEach(cleanup);

const invariants: InvariantResult[] = [
  { name: "ReadOnlyUnlessGated", held: true },
  { name: "SingleContainerTouched", held: false },
];

describe("InvariantsChecklist", () => {
  test("renders every invariant's name", () => {
    const { getByText } = render(<InvariantsChecklist invariants={invariants} />);
    expect(getByText("ReadOnlyUnlessGated")).toBeDefined();
    expect(getByText("SingleContainerTouched")).toBeDefined();
  });

  test("a held invariant reads 'held', with the open tick's filled-green grammar", () => {
    const { getByText, container } = render(<InvariantsChecklist invariants={invariants} />);
    expect(getByText("held")).toBeDefined();
    expect(container.querySelector('[data-status="open"]')).not.toBeNull();
  });

  test("a violated invariant reads 'violated', with the escalated-to-human amber grammar — not retried, not hidden", () => {
    const { getByText, container } = render(<InvariantsChecklist invariants={invariants} />);
    expect(getByText("violated")).toBeDefined();
    expect(container.querySelector('[data-status="escalated-to-human"]')).not.toBeNull();
  });
});
