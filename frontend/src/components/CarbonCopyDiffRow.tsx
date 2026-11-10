import "./CarbonCopyDiffRow.css";
import type { DiffEntry } from "../data/types";

export function CarbonCopyDiffRow({ entry }: { entry: DiffEntry }) {
  return (
    <div className="diff-row">
      <span className="path">{entry.path}</span>
      <span className="before">{entry.before}</span>
      <span className="after">{entry.after}</span>
    </div>
  );
}

export function DiffLedger({ entries }: { entries: readonly DiffEntry[] }) {
  return (
    <div className="diff-ledger">
      {entries.map((entry) => (
        <CarbonCopyDiffRow key={entry.path} entry={entry} />
      ))}
    </div>
  );
}
