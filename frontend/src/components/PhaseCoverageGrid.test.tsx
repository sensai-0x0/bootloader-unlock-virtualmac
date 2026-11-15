import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { PhaseCoverageGrid } from "./PhaseCoverageGrid";
import type { Initiative } from "../data/types";

afterEach(cleanup);

const initiatives: Initiative[] = [
  {
    id: "a",
    name: "Initiative A",
    kind: "vulnres_suite",
    status: "active",
    phases: { recon: "green", build: "blocked", execute: "never-run", "triage-learn": "stale", "persist-report": "in-progress" },
  },
];

describe("PhaseCoverageGrid", () => {
  test("renders one header column per phase plus the initiative name column", () => {
    const { getByText } = render(<PhaseCoverageGrid initiatives={initiatives} />);
    expect(getByText("recon")).toBeDefined();
    expect(getByText("persist-report")).toBeDefined();
    expect(getByText("Initiative A")).toBeDefined();
  });

  test("each cell's dot carries its exact state as a data attribute", () => {
    const { container } = render(<PhaseCoverageGrid initiatives={initiatives} />);
    const dots = container.querySelectorAll(".phase-dot");
    expect(dots).toHaveLength(5);
    const states = Array.from(dots).map((d) => d.getAttribute("data-state"));
    expect(states).toEqual(["green", "blocked", "never-run", "stale", "in-progress"]);
  });

  test("focusing a cell reveals the exact initiative/phase/state via the loupe", async () => {
    const { container, getByText } = render(<PhaseCoverageGrid initiatives={initiatives} />);
    const triggers = container.querySelectorAll(".loupe-trigger");
    fireEvent.focus(triggers[1]!); // build, blocked

    await waitFor(() => expect(getByText("Initiative A · build: blocked")).toBeDefined());
  });
});
