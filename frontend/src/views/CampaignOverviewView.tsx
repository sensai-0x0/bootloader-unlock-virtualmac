import { useState } from "react";
import { Headline } from "../components/Headline";
import { Ledger, LedgerRow } from "../components/Ledger";
import { Legend } from "../components/Legend";
import { Rail } from "../components/Rail";
import { StageRule, VULNRES_STAGES } from "../components/StageRule";
import { StatusTick } from "../components/StatusTick";
import { exploits } from "../data/sampleExploits";
import type { FindingStatus } from "../data/types";
import { filterByStatus } from "../lib/filter";

const ACTIVE_STAGES = ["environment-runner", "triage", "exploit-dev"];

export function CampaignOverviewView() {
  const [activeStatuses, setActiveStatuses] = useState<FindingStatus[]>([]);

  const toggleStatus = (status: FindingStatus) => {
    setActiveStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status],
    );
  };

  const visibleExploits = filterByStatus(exploits, activeStatuses);
  const provenCount = exploits.filter((e) => e.status === "escalated-to-human").length;

  return (
    <>
      <Headline
        className="waveform"
        figure={provenCount}
        label="chains with impact proven, awaiting sign-off"
      />
      <StageRule stages={VULNRES_STAGES} activeStages={ACTIVE_STAGES} />
      <Legend active={activeStatuses} onToggle={toggleStatus} />
      <Ledger variant="exploits">
        {visibleExploits.map((exploit) => (
          <LedgerRow
            key={exploit.id}
            columns={[
              <span className="col-target">{exploit.title}</span>,
              <span className="col-src">{exploit.techniqueSource}</span>,
              <span className="col-score">{exploit.impact}</span>,
              <span className="col-status">
                <StatusTick status={exploit.status} />
              </span>,
            ]}
            detail={[
              { label: "target", value: exploit.target },
              { label: "technique source", value: exploit.techniqueSource },
              { label: "sweep", value: exploit.sweepId },
              { label: "chaining notes", value: exploit.chainingNotes },
            ]}
          />
        ))}
      </Ledger>
      <Rail
        rows={[
          ["chains proven, this cycle", String(provenCount)],
          ["awaiting disclosure decision", String(provenCount)],
          ["disposable environments used", "1 active, 1 torn down"],
        ]}
      />
    </>
  );
}
