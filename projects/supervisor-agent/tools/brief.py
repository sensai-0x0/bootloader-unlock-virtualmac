#!/usr/bin/env python3
"""Supervisor agent brief generator — BUILD-SPEC §4.4, §8 phase 4.

Reads score_runs/recommendations/v_phase_coverage/staleness_clocks and
writes briefs/*.md, one `briefs` row, and one `dispatch_tickets` row per
top-3 recommendation. Dispatch tickets are text-only named blocks
(`DISPATCH: <initiative>`) with scope invariants and required gate;
nothing here executes, schedules, or writes outside briefs/ and the DB
(same §7 invariant-1 scope as tools/supervisor.py)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supervisor import BASE, utcnow, connect, checkpoint  # noqa: E402

BRIEFS_DIR = BASE / "briefs"


def _latest_score_run(conn):
    return conn.execute(
        "SELECT id, computed_at, inputs_hash FROM score_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()


def render_brief(conn, score_run_id: int) -> dict:
    run = conn.execute(
        "SELECT id, computed_at, inputs_hash FROM score_runs WHERE id = ?",
        (score_run_id,)).fetchone()
    if run is None:
        raise ValueError(f"no score_run {score_run_id}")

    recs = conn.execute(
        "SELECT r.rank, r.initiative_id, i.slug, i.name, r.score_total, "
        "r.score_staleness, r.score_blast, r.score_readiness, r.score_precedent, "
        "r.required_gate "
        "FROM recommendations r JOIN initiatives i ON i.id = r.initiative_id "
        "WHERE r.score_run_id = ? ORDER BY r.rank", (score_run_id,)).fetchall()
    if not recs:
        raise ValueError(f"score_run {score_run_id} has no recommendations")

    top3 = recs[:3]
    # "needs a human" means a real pending gate, not "nothing dispatchable at
    # all" (no capability + no owner_gate) and not "no gate needed" (none…).
    needs_human = [r for r in recs if r["required_gate"].startswith("user approval")]

    clocks = conn.execute(
        "SELECT surface, state, last_verified_at FROM staleness_clocks "
        "WHERE state != 'live' ORDER BY state, surface").fetchall()
    coverage = conn.execute(
        "SELECT slug, phase, state, note FROM v_phase_coverage ORDER BY slug, phase"
    ).fetchall()

    created_at = utcnow()
    date_part = created_at[:10]
    seq = conn.execute(
        "SELECT count(*) + 1 FROM briefs WHERE path LIKE ?",
        (f"briefs/{date_part}-%",)).fetchone()[0]
    rel_path = f"briefs/{date_part}-{seq:03d}-brief.md"

    lines = [
        f"# Decision brief — {date_part}-{seq:03d}", "",
        f"Generated {created_at} from score_run {score_run_id} "
        f"(inputs_hash `{run['inputs_hash'][:12]}…`). Every claim below cites its "
        "own source; this file is machine-generated from `db/queries/` and the "
        "DB — never hand-edited (database is the single source of truth, "
        "BUILD-SPEC §3).", "",
        "## Do-next (top 3)", "",
    ]
    for r in top3:
        lines.append(
            f"{r['rank']}. **{r['slug']}** ({r['name']}) — score {r['score_total']} "
            f"[staleness {r['score_staleness']} / blast {r['score_blast']} / "
            f"readiness {r['score_readiness']} / precedent {r['score_precedent']}] "
            f"— required gate: **{r['required_gate']}** "
            f"[source: recommendations, score_run {score_run_id}]")
    lines.append("")

    lines += ["## Needs a human", ""]
    if needs_human:
        for r in needs_human:
            lines.append(
                f"- **{r['slug']}** (rank {r['rank']}) — {r['required_gate']} "
                f"[source: recommendations, score_run {score_run_id}]")
    else:
        lines.append("(none — every current recommendation is autonomous-only)")
    lines.append("")

    lines += ["## Staleness (non-live clocks)", ""]
    if clocks:
        for c in clocks:
            lines.append(
                f"- `{c['surface']}`: **{c['state']}** "
                f"(last verified: {c['last_verified_at'] or 'never'}) "
                "[source: staleness_clocks]")
        if any(c["state"] == "never" for c in clocks):
            lines.append(
                "- *(known limitation, BUILD-SPEC §3.5 item 23: a `never` "
                "clock has no transition rule yet — one listed above may "
                "already be partially stale rather than truly untouched; "
                "cross-check its surface against \"Phase coverage\" below, "
                "which reads the live registry directly.)*")
    else:
        lines.append("(every clock is live)")
    lines.append("")

    lines += ["## Phase coverage", "", "| initiative | phase | state | note |",
              "|---|---|---|---|"]
    for c in coverage:
        note = c["note"].replace("|", "/")[:160]
        lines.append(f"| {c['slug']} | {c['phase']} | {c['state']} | {note} |")
    lines.append("")

    lines += ["## Dispatch tickets", ""]
    tickets = []
    for r in top3:
        scope = (f"initiative={r['slug']}; grain=initiative (capability_id not yet "
                 "bound — a later phase decides which specific capability a "
                 "dispatch targets); recorded here as a proposal only, nothing "
                 "executed by this ticket's existence")
        lines.append(
            f"```\nDISPATCH: {r['slug']}\nrequired gate: {r['required_gate']}\n"
            f"scope: {scope}\napproval_status: pending (user, in conversation)\n```")
        tickets.append({"slug": r["slug"], "required_gate": r["required_gate"],
                        "scope": scope})
    lines.append("")

    lines += [
        "## Provenance appendix", "",
        f"- score_run {score_run_id}, computed_at {run['computed_at']}, "
        f"inputs_hash `{run['inputs_hash']}`",
        "- every recommendation's full `component_provenance` (which input rows "
        "produced each score) lives in `recommendations.component_provenance`; "
        "not reproduced in full here to keep this brief readable.", "",
    ]

    brief_md = "\n".join(lines) + "\n"

    cur = conn.execute(
        "INSERT INTO briefs(path, created_at, run_id, do_next_top3, needs_human) "
        "VALUES (?, ?, ?, ?, ?)",
        (rel_path, created_at, score_run_id,
         json.dumps([r["initiative_id"] for r in top3]),
         json.dumps([{"initiative_id": r["initiative_id"],
                     "required_gate": r["required_gate"]} for r in needs_human])))
    brief_id = cur.lastrowid

    for t in tickets:
        conn.execute(
            "INSERT INTO dispatch_tickets(brief_id, capability_id, "
            "scope_invariants, required_gate) VALUES (?, NULL, ?, ?)",
            (brief_id, t["scope"], t["required_gate"]))

    conn.execute(
        "UPDATE recommendations SET brief_id = ? "
        "WHERE score_run_id = ? AND brief_id IS NULL",
        (brief_id, score_run_id))

    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    (BASE / rel_path).write_text(brief_md, encoding="utf-8")

    conn.commit()
    checkpoint(conn)
    return {"brief_id": brief_id, "path": rel_path,
            "top3": [r["slug"] for r in top3],
            "needs_human": [r["slug"] for r in needs_human],
            "tickets": len(tickets)}


def cmd_brief(score_run_id: int | None = None) -> int:
    conn = connect()
    if score_run_id is None:
        run = _latest_score_run(conn)
        if run is None:
            print("no score_runs exist yet — run `score` first", file=sys.stderr)
            conn.close()
            return 2
        score_run_id = run["id"]
    result = render_brief(conn, score_run_id)
    conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(cmd_brief(arg))
