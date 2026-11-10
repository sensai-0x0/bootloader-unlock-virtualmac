import { useState } from "react";
import { ConfidenceText } from "../components/ConfidenceText";
import { Headline } from "../components/Headline";
import { Ledger, LedgerRow } from "../components/Ledger";
import { Legend } from "../components/Legend";
import { ManifestHeader } from "../components/ManifestHeader";
import { PhosphorTrace } from "../components/PhosphorTrace";
import { Rail } from "../components/Rail";
import { ScrubTimeline } from "../components/ScrubTimeline";
import { SeverityGlyph } from "../components/SeverityGlyph";
import { StatusTick } from "../components/StatusTick";
import { knowledgeEntriesRecorded, sweeps } from "../data/sampleSweep";
import type { FindingStatus } from "../data/types";
import { filterByStatus } from "../lib/filter";

const traceValues = sweeps.map((sweep) => sweep.findings.length);

export function SweepFindingsView() {
  const [activeStatuses, setActiveStatuses] = useState<FindingStatus[]>([]);
  // sweeps is a non-empty literal array, so the last index is always valid —
  // defaults to the latest sweep.
  const [selectedIndex, setSelectedIndex] = useState(sweeps.length - 1);
  const selectedSweep = sweeps[selectedIndex] ?? sweeps[sweeps.length - 1]!;

  const toggleStatus = (status: FindingStatus) => {
    setActiveStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status],
    );
  };

  const visibleFindings = filterByStatus(selectedSweep.findings, activeStatuses);
  const fixedThisSweep = selectedSweep.findings.filter((f) => f.status === "fixed").length;

  return (
    <>
      <Headline figure={selectedSweep.findings.length} label="findings opened this sweep" />
      <PhosphorTrace values={traceValues} label="findings per sweep, most recent sweep at the right" />
      <ScrubTimeline sweeps={sweeps} selectedIndex={selectedIndex} onChange={setSelectedIndex} />
      <ManifestHeader sweep={selectedSweep} />
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
          ["fixed, this sweep", String(fixedThisSweep)],
          ["knowledge entries recorded", String(knowledgeEntriesRecorded)],
        ]}
      />
    </>
  );
}
