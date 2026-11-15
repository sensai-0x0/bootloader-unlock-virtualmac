import type { ApprovalClass, DispatchApprovalStatus, FindingStatus } from "../data/types";

/**
 * Maps supervisor-agent's ApprovalClass/DispatchApprovalStatus vocabulary
 * onto StatusTick's existing visual grammar, via its `label` override —
 * reuse, not a new tick component, since the shapes (a thing that's safe/
 * default, a thing that needs a lighter human check, a thing that needs
 * the hardest gate) are the same three tiers the finding-status tick
 * already draws. Deliberately avoids "fixed"/"disclosed-upstream": those
 * two carry a hardcoded StampMark graphic ("FIXED"/"DISCLOSED") that the
 * `label` override does not suppress, which would be flatly wrong next to
 * an approval-gate label.
 */
export function approvalClassVisual(gate: ApprovalClass): FindingStatus {
  switch (gate) {
    case "autonomous":
      return "open";
    case "user_gated":
      return "false-positive";
    case "gated_plus_1tr":
      return "escalated-to-human";
  }
}

export function dispatchStatusVisual(status: DispatchApprovalStatus): FindingStatus {
  switch (status) {
    case "approved":
      return "open";
    case "pending":
      return "escalated-to-human";
    case "rejected":
      return "false-positive";
  }
}
