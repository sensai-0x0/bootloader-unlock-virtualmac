import "./StageRule.css";

/** vuln_res/'s own pipeline stages — the original use this component shipped for. */
export const VULNRES_STAGES = [
  "recon",
  "fuzz-harness",
  "environment-runner",
  "triage",
  "exploit-dev",
  "disclosure",
];

interface StageRuleProps {
  stages: readonly string[];
  activeStages: readonly string[];
}

/** A horizontal ruler with the active stage(s) lit — reused as-is for the
 * SecurityMode transition rail (Full/ReducedKexts/PermissiveCustomKernel),
 * not a second component, since it's the same shape: a small fixed set of
 * named positions with one or two lit. */
export function StageRule({ stages, activeStages }: StageRuleProps) {
  return (
    <div className="stage-rule">
      {stages.map((stage) => (
        <div key={stage} className={activeStages.includes(stage) ? "stage active" : "stage"}>
          {stage}
        </div>
      ))}
    </div>
  );
}
