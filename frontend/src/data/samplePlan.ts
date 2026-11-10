import type { PlannedTransition } from "./types";

/**
 * Illustrative sample data only — see ../../../design/README.md. The
 * commands are representative of real bputil/kmutil flags documented in
 * this repo's own CLAUDE.md, not independently re-verified here. plan() is
 * always a dry run; nothing in this app ever executes this.
 */
export const samplePlan: PlannedTransition = {
  fromMode: "Full",
  toProfile: "ReducedKexts",
  targetVolumeGroup: "A1C3-7D2F-TARGET",
  commands: [
    ["sudo", "bputil", "-m"],
    ["sudo", "kmutil", "configure-boot", "--volume-root", "/"],
  ],
  requiresOneTrueRecoveryAndOwnerConfirmation: true,
};
