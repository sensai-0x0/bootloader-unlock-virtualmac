import { EventTimeline } from "../components/EventTimeline";
import { Headline } from "../components/Headline";
import { Ledger, LedgerRow } from "../components/Ledger";
import { Rail } from "../components/Rail";
import { SessionStatusTick } from "../components/SessionStatusTick";
import { sampleSessions } from "../data/sampleSessions";

/**
 * projects/04-agentic-serving-layer/'s live Session model — the one
 * genuinely monitorable workflow in this app. Read-only monitoring only:
 * no interrupt control here. Interrupt is safe (it cancels an in-flight
 * LLM turn, not a device mutation — see frontend/CLAUDE.md), but it would
 * be the first non-read-only affordance this app has ever needed, and
 * that's a deliberate design decision on its own, not something to add as
 * a side effect of a monitoring pass. Deferred, not forgotten.
 */
export function SessionsView() {
  const liveCount = sampleSessions.filter((s) => s.status === "active" || s.status === "idle").length;
  const byTrack = {
    bootloader: sampleSessions.filter((s) => s.track === "bootloader").length,
    "vuln-research": sampleSessions.filter((s) => s.track === "vuln-research").length,
  };

  return (
    <>
      <Headline figure={liveCount} label="sessions active or idle right now" />
      <Ledger variant="sessions">
        {sampleSessions.map((session) => (
          <LedgerRow
            key={session.id}
            columns={[
              <span className="col-target">
                {session.id} &middot; {session.track}
              </span>,
              <span className="col-src">
                <SessionStatusTick status={session.status} />
              </span>,
              <span className="col-status">{session.lastActivityAt}</span>,
            ]}
            detail={[
              { label: "created", value: session.createdAt },
              { label: "workspace", value: session.workspacePath },
              { label: "recent events", value: <EventTimeline events={session.events} /> },
            ]}
          />
        ))}
      </Ledger>
      <Rail
        rows={[
          ["bootloader sessions", String(byTrack.bootloader)],
          ["vuln-research sessions", String(byTrack["vuln-research"])],
          ["sessions total", String(sampleSessions.length)],
        ]}
      />
    </>
  );
}
