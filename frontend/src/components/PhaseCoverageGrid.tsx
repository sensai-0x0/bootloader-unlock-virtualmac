import "./PhaseCoverageGrid.css";
import { Loupe } from "./Loupe";
import type { Initiative, PhaseName } from "../data/types";

const PHASES: PhaseName[] = ["recon", "build", "execute", "triage-learn", "persist-report"];

export function PhaseCoverageGrid({ initiatives }: { initiatives: readonly Initiative[] }) {
  return (
    <div className="phase-grid">
      <div className="phase-grid-row phase-grid-header">
        <span />
        {PHASES.map((phase) => (
          <span key={phase} className="phase-grid-phase-label">
            {phase}
          </span>
        ))}
      </div>
      {initiatives.map((initiative) => (
        <div className="phase-grid-row" key={initiative.id}>
          <span className="phase-grid-initiative">{initiative.name}</span>
          {PHASES.map((phase) => {
            const state = initiative.phases[phase];
            return (
              <span className="phase-grid-cell" key={phase}>
                <Loupe
                  display={<span className="phase-dot" data-state={state} />}
                  full={`${initiative.name} · ${phase}: ${state}`}
                  label={`${initiative.name} ${phase} coverage: ${state}`}
                />
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
}
