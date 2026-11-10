import "./ManifestHeader.css";
import type { Sweep } from "../data/types";

export function ManifestHeader({ sweep }: { sweep: Sweep }) {
  return (
    <div className="manifest">
      <div>
        <div className="sweep-id">{sweep.id}</div>
        <div className="sweep-label">{sweep.label}</div>
      </div>
      <div className="duration">{sweep.durationMinutes}m</div>
      <div className="agents-run">
        agents run: {sweep.agentsRun.join(", ")} &middot; environment: {sweep.environment}
      </div>
    </div>
  );
}
