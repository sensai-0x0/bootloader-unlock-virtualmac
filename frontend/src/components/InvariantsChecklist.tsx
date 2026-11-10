import "./InvariantsChecklist.css";
import { StatusTick } from "./StatusTick";
import type { InvariantResult } from "../data/types";

/**
 * One row per global invariant (spec/contract-spec.md). A violation
 * borrows the same amber escalated-to-human tick a vuln_res finding
 * uses — accurate, not just visually convenient: contract-spec.md says a
 * violation after the tool behaved correctly "routes the finding to
 * coordinated disclosure," which is exactly what escalated-to-human means
 * on the other views. No retry affordance exists here on purpose — see
 * CLAUDE.md's "invariant violations are findings, not retryable errors."
 */
export function InvariantsChecklist({ invariants }: { invariants: readonly InvariantResult[] }) {
  return (
    <dl className="invariants">
      {invariants.map((inv) => (
        <div key={inv.name} className="invariants-row">
          <dt>{inv.name}</dt>
          <dd>
            <StatusTick status={inv.held ? "open" : "escalated-to-human"} label={inv.held ? "held" : "violated"} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
