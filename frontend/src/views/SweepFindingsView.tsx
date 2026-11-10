import { useState } from "react";
import { Headline } from "../components/Headline";
import { Ledger, LedgerRow } from "../components/Ledger";
import { Legend } from "../components/Legend";
import { ManifestHeader } from "../components/ManifestHeader";
import { Rail } from "../components/Rail";
import { SeverityGlyph } from "../components/SeverityGlyph";
import { StatusTick } from "../components/StatusTick";
import { currentSweep, knowledgeEntriesRecorded, sweepHistory } from "../data/sampleSweep";
import type { FindingStatus } from "../data/types";
import { filterByStatus } from "../lib/filter";

export function SweepFindingsView() {
  const [activeStatuses, setActiveStatuses] = useState<FindingStatus[]>([]);

  const toggleStatus = (status: FindingStatus) => {
    setActiveStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status],
    );
  };

  const visibleFindings = filterByStatus(currentSweep.findings, activeStatuses);

  return (
    <>
      <Headline figure={currentSweep.findings.length} label="findings opened this sweep" />
      <ManifestHeader sweep={currentSweep} />
      <Legend active={activeStatuses} onToggle={toggleStatus} />
      <Ledger variant="findings">
        {visibleFindings.map((finding) => (
          <LedgerRow
            key={finding.id}
            columns={[
              <span className="col-target">{finding.target}</span>,
              <span className="col-src">{finding.source}</span>,
              <span className="col-score">
                <SeverityGlyph score={finding.score} />
              </span>,
              <span className="col-status">
                <StatusTick status={finding.status} />
              </span>,
            ]}
            detail={[
              { label: "id", value: finding.id },
              { label: "technical detail", value: finding.technicalDetail },
              ...(finding.reproduction ? [{ label: "reproduction", value: finding.reproduction }] : []),
              { label: "classification", value: finding.classification },
              ...(finding.chainingNotes ? [{ label: "chaining notes", value: finding.chainingNotes }] : []),
              ...(finding.resolution ? [{ label: "resolution", value: finding.resolution }] : []),
            ]}
          />
        ))}
      </Ledger>
      <Rail
        rows={[
          ["sweep history", "findings"],
          ...sweepHistory.map(
            (entry): [string, string] => [entry.sweepId, `${entry.fixedCount} fixed`],
          ),
          ["knowledge entries recorded", String(knowledgeEntriesRecorded)],
        ]}
      />
    </>
  );
}
