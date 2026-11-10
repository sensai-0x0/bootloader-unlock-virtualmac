import type { SecurityMode, TargetProfile } from "../data/types";

/**
 * The TargetProfile a given SecurityMode corresponds to on the
 * mode-transition rail, so one three-stage rail (Full/ReducedKexts/
 * PermissiveCustomKernel) can highlight both ends of an edge in one
 * vocabulary. `Unknown` has no corresponding profile — the rail shows only
 * the destination lit in that case, never a guessed origin.
 */
export function securityModeAsProfileLabel(mode: SecurityMode): TargetProfile | null {
  switch (mode) {
    case "Full":
      return "Full";
    case "Reduced":
      return "ReducedKexts";
    case "Permissive":
      return "PermissiveCustomKernel";
    case "Unknown":
      return null;
  }
}
