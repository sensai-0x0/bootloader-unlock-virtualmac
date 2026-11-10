import { Ledger, LedgerRow } from "./Ledger";
import { StageRule } from "./StageRule";
import { StatusTick } from "./StatusTick";
import { securityModeAsProfileLabel } from "../lib/securityMode";
import type { PlannedTransition } from "../data/types";

const PROFILE_STAGES = ["Full", "ReducedKexts", "PermissiveCustomKernel"] as const;

/**
 * `plan()` is always a dry run, even in macOS (spec/contract-spec.md) — this
 * never becomes an Apply/Revert control, see frontend/CLAUDE.md. The
 * "requires 1TR + owner confirmation" tick borrows StatusTick's
 * escalated-to-human look: it's the same semantic, a human gate, not a
 * problem with the plan itself.
 */
export function PlanPreview({ plan }: { plan: PlannedTransition }) {
  const fromAsProfile = securityModeAsProfileLabel(plan.fromMode);
  const activeStages = fromAsProfile ? [fromAsProfile, plan.toProfile] : [plan.toProfile];

  return (
    <>
      <StageRule stages={PROFILE_STAGES} activeStages={activeStages} />
      <Ledger variant="boot-objects">
        <LedgerRow
          columns={[
            <span className="col-target">
              {plan.fromMode} {"→"} {plan.toProfile}
            </span>,
            <span className="col-src">{plan.targetVolumeGroup}</span>,
            <span className="col-score">
              {plan.requiresOneTrueRecoveryAndOwnerConfirmation && (
                <StatusTick status="escalated-to-human" label="requires 1TR + owner confirmation" />
              )}
            </span>,
          ]}
          detail={plan.commands.map((argv, i) => ({
            label: `command ${i + 1}`,
            value: argv.join(" "),
          }))}
        />
      </Ledger>
    </>
  );
}
