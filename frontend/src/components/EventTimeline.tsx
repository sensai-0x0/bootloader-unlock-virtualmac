import "./EventTimeline.css";
import { formatEventTime } from "../lib/formatEventTime";
import type { SessionEvent } from "../data/types";

/**
 * A session's recent event frames (projects/04-agentic-serving-layer/'s
 * WebSocket contract), rendered as a ledger, not a debug console — each
 * row is a human synopsis of one frame, not its raw payload.
 */
export function EventTimeline({ events }: { events: readonly SessionEvent[] }) {
  return (
    <ul className="event-timeline">
      {events.map((event, i) => (
        <li key={i} data-event={event.type}>
          <span className="event-type">{event.type}</span>
          <span className="event-summary">{event.summary}</span>
          <span className="event-ts">{formatEventTime(event.ts)}</span>
        </li>
      ))}
    </ul>
  );
}
