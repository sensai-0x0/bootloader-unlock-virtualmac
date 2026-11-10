import "./StageRule.css";

const STAGES = ["recon", "fuzz-harness", "environment-runner", "triage", "exploit-dev", "disclosure"];

export function StageRule({ activeStages }: { activeStages: readonly string[] }) {
  return (
    <div className="stage-rule">
      {STAGES.map((stage) => (
        <div key={stage} className={activeStages.includes(stage) ? "stage active" : "stage"}>
          {stage}
        </div>
      ))}
    </div>
  );
}
