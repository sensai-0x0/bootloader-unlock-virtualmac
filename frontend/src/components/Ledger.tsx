import "./Ledger.css";
import { Fragment, type ReactNode } from "react";

export function Ledger({
  variant,
  children,
}: {
  variant: "findings" | "exploits" | "boot-objects";
  children: ReactNode;
}) {
  return <div className={`ledger cols-${variant}`}>{children}</div>;
}

interface DetailEntry {
  label: string;
  value: ReactNode;
}

interface LedgerRowProps {
  columns: ReactNode[];
  detail: DetailEntry[];
}

/**
 * One ledger entry, built on native <details>/<summary> — clicking anywhere
 * on the row expands it, no button, full keyboard support for free. Filter
 * rows by omitting them from the list passed in, rather than hiding them
 * here.
 */
export function LedgerRow({ columns, detail }: LedgerRowProps) {
  return (
    <details>
      <summary>
        {columns.map((col, i) => (
          <Fragment key={i}>{col}</Fragment>
        ))}
      </summary>
      <dl className="detail">
        {detail.map(({ label, value }) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
