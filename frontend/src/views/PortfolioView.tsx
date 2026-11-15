import { Headline } from "../components/Headline";
import { Ledger, LedgerRow } from "../components/Ledger";
import { PhaseCoverageGrid } from "../components/PhaseCoverageGrid";
import { StatusTick } from "../components/StatusTick";
import { dispatchTickets, initiatives, recommendations } from "../data/samplePortfolio";
import { approvalClassVisual, dispatchStatusVisual } from "../lib/approvalClass";

function initiativeName(id: string): string {
  return initiatives.find((i) => i.id === id)?.name ?? id;
}

/**
 * projects/supervisor-agent/'s decision layer: ranked "do next"
 * recommendations, phase coverage across the whole portfolio, and the
 * dispatch-ticket lifecycle (pending → approved/rejected → executed) —
 * the second genuine workflow this app surfaces, distinct from Sessions'
 * live agent conversations. supervisor-agent never executes anything
 * itself; this view stays exactly as read-only as everything else here.
 */
export function PortfolioView() {
  const pendingCount = dispatchTickets.filter((t) => t.approvalStatus === "pending").length;

  return (
    <>
      <Headline figure={pendingCount} label="dispatch tickets pending approval" />

      <div className="section-label">phase coverage</div>
      <PhaseCoverageGrid initiatives={initiatives} />

      <div className="section-label">recommendations</div>
      <Ledger variant="recommendations">
        {recommendations.map((rec) => (
          <LedgerRow
            key={rec.initiativeId}
            columns={[
              <span className="col-target">
                {rec.rank}. {initiativeName(rec.initiativeId)}
              </span>,
              <span className="col-score">{rec.scoreTotal}</span>,
              <span className="col-status">
                <StatusTick status={approvalClassVisual(rec.requiredGate)} label={rec.requiredGate} />
              </span>,
            ]}
            detail={[
              { label: "score — staleness", value: String(rec.scoreStaleness) },
              { label: "score — blast radius", value: String(rec.scoreBlast) },
              { label: "score — readiness", value: String(rec.scoreReadiness) },
              { label: "score — precedent", value: String(rec.scorePrecedent) },
            ]}
          />
        ))}
      </Ledger>

      <div className="section-label">dispatch tickets</div>
      <Ledger variant="tickets">
        {dispatchTickets.map((ticket) => (
          <LedgerRow
            key={ticket.id}
            columns={[
              <span className="col-target">{initiativeName(ticket.initiativeId)}</span>,
              <span className="col-src">
                <StatusTick status={approvalClassVisual(ticket.requiredGate)} label={ticket.requiredGate} />
              </span>,
              <span className="col-status">
                <StatusTick
                  status={dispatchStatusVisual(ticket.approvalStatus)}
                  label={ticket.approvalStatus}
                />
              </span>,
            ]}
            detail={[
              { label: "scope invariants", value: ticket.scopeInvariants },
              ...(ticket.approvedBy
                ? [{ label: "approved by", value: `${ticket.approvedBy} · ${ticket.approvedAt}` }]
                : []),
              ...(ticket.executedAt ? [{ label: "executed at", value: ticket.executedAt }] : []),
            ]}
          />
        ))}
      </Ledger>
    </>
  );
}
