import { useState } from "react";
import { ConfidenceText } from "../components/ConfidenceText";
import { Headline } from "../components/Headline";
import { Ledger, LedgerRow } from "../components/Ledger";
import { Legend } from "../components/Legend";
import { ManifestHeader } from "../components/ManifestHeader";
import { PhosphorTrace } from "../components/PhosphorTrace";
import { Rail } from "../components/Rail";
import { SeverityGlyph } from "../components/SeverityGlyph";
import { StatusTick } from "../components/StatusTick";
import { currentSweep, knowledgeEntriesRecorded, sweepHistory } from "../data/sampleSweep";
import type { FindingStatus } from "../data/types";
import { filterByStatus } from "../lib/filter";

// Oldest first, left to right — sweepHistory itself is newest-first (for the
// rail list below), so this view reverses it for the trace.
const traceValues = [...sweepHistory].reverse().map((h) => h.fixedCount).concat(
  currentSweep.findings.length,
);

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
      <PhosphorTrace values={traceValues} label="findings per sweep, most recent sweep at the right" />
      <ManifestHeader sweep={currentSweep} />
      <Legend active={activeStatuses} onToggle={toggleStatus} />
      <Ledger variant="findings">
        {visibleFindings.map((finding) => (
          <LedgerRow
            key={finding.id}
            columns={[
              <span className="col-target">
                <ConfidenceText confidence={finding.confidence}>{finding.target}</ConfidenceText>
              </span>,
              <span className="col-src">{finding.source}</span>,
              <span className="col-score">
                <SeverityGlyph score={finding.score} confidence={finding.confidence} />
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
              { label: "confidence", value: finding.confidence },
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
