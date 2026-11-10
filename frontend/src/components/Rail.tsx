import "./Rail.css";
import type { ReactNode } from "react";

export function Rail({ rows }: { rows: [ReactNode, ReactNode][] }) {
  return (
    <div className="rail">
      {rows.map(([label, value], i) => (
        <div key={i} className="rail-row">
          <span>{label}</span>
          <span>{value}</span>
        </div>
      ))}
    </div>
  );
}
