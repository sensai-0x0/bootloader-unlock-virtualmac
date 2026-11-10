import "./Headline.css";
import type { ReactNode } from "react";

export function Headline({
  figure,
  label,
  className,
}: {
  figure: ReactNode;
  label: string;
  className?: string;
}) {
  return (
    <div className={className ? `headline ${className}` : "headline"}>
      <div className="figure">{figure}</div>
      <div className="label">{label}</div>
    </div>
  );
}
