import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render } from "@testing-library/react";
import { StageRule } from "./StageRule";

afterEach(cleanup);

describe("StageRule", () => {
  test("renders every stage, marking only the active ones", () => {
    const { getByText } = render(
      <StageRule stages={["a", "b", "c"]} activeStages={["b"]} />,
    );
    expect(getByText("a").className).not.toContain("active");
    expect(getByText("b").className).toContain("active");
    expect(getByText("c").className).not.toContain("active");
  });

  test("is reusable for an arbitrary stage set, not just vuln_res's own pipeline", () => {
    const { getByText } = render(
      <StageRule stages={["Full", "ReducedKexts", "PermissiveCustomKernel"]} activeStages={["Full", "ReducedKexts"]} />,
    );
    expect(getByText("Full").className).toContain("active");
    expect(getByText("ReducedKexts").className).toContain("active");
    expect(getByText("PermissiveCustomKernel").className).not.toContain("active");
  });
});
