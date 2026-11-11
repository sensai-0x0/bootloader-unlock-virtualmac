#!/usr/bin/env python3
"""Phase-5 simulation engine — BUILD-SPEC §5.4.

Simulates each profile's decision loop: a fixed phase sequence (from
tp_profiles.phase_vector), one technique candidate per phase (drawn from
each profile's own stated preferences in ttp/profiles/*.md — reproduced
here as reviewed, diffable Python data, never invented at run time), each
step's coverage answered via db/queries/q-sim-gap-probe.sql against
ttp_mappings/staleness_clocks/capabilities. Never generates payloads, never
executes anything, never leaves the DB/briefs (§5.1/§5.5 hard boundary)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supervisor import BASE, utcnow, connect, checkpoint  # noqa: E402

GAP_PROBE_QUERY = (BASE / "db" / "queries" / "q-sim-gap-probe.sql").read_text()

# Reviewed, diffable: each profile's technique preferences per phase,
# transcribed from ttp/profiles/*.md's own "Technique preferences per
# phase" section — never invented here, this file only encodes what that
# markdown already states so the simulation can run it.
PROFILE_STEPS = {
    "patient-fleet": [
        ("persist_expand", "T1021.004",
         "SSH over an enrolled fleet Mac — this portfolio's own worked example"),
        ("persist_expand", "T1078",
         "Valid Accounts once an enrollment list exists"),
        ("persist_expand", "T1222",
         "File and Directory Permissions Modification against the "
         "boot-security surface (unattested_preference: no G1045 "
         "technique_groups row names T1222 as of this ingest)"),
    ],
    "opportunistic-supplychain": [
        ("init_recon", "T1195.001",
         "Compromise Software Dependencies against Cargo.lock/Cargo.toml"),
        ("execute", "T1195.001",
         "the same technique, at the point a poisoned dependency would execute"),
    ],
    "agent-directed": [
        ("execute", "T1698",
         "Indirect Prompt Injection via a crafted knowledge-entry hook or "
         "milestone log line"),
        ("execute", "T1699",
         "Direct Prompt Injection — recorded not_applicable: no live "
         "third-party prompt surface exists"),
        ("triage_learn", "T1608.007",
         "AI Result Poisoning — a planted artifact engineered to look like "
         "legitimate past precedent"),
        ("persist_report", "T1685.007",
         "Impair Autonomous Defenses against the vulnres-* autonomous "
         "capabilities"),
    ],
}

UNATTESTED_MARKER = "unattested_preference"


def _basis_for_step(conn, technique_id: int, attack_id: str, intent: str):
    """Returns (basis, success_predicted, rows) for one step, querying the
    gap-probe SQL for every mapped surface of this technique."""
    rows = conn.execute(GAP_PROBE_QUERY, (technique_id,)).fetchall()
    if not rows:
        return (f"deterred: {attack_id} has no ttp_mappings row for this "
                "portfolio's surfaces (selection rubric excluded it, or "
                "it isn't yet mapped)", 0, [])
    basis_bits = []
    any_live_blocker = False
    for r in rows:
        if r["verdict"] == "covered" and r["clock_state"] in (None, "live"):
            any_live_blocker = True
        basis_bits.append(f"{r['surface']}: verdict={r['verdict']}"
                          + (f", clock={r['clock_state']}" if r["clock_state"] else ""))
    basis = "; ".join(basis_bits)
    if UNATTESTED_MARKER in intent:
        basis = f"{UNATTESTED_MARKER}: {intent} | {basis}"
    success_predicted = 0 if any_live_blocker else 1
    return basis, success_predicted, [dict(r) for r in rows]


def run_scenario(conn, profile_name: str, seed: int) -> dict:
    profile = conn.execute(
        "SELECT id, phase_vector FROM tp_profiles WHERE name = ?",
        (profile_name,)).fetchone()
    if profile is None:
        raise ValueError(f"no tp_profiles row for {profile_name!r} — run "
                         "ttp_ingest.py profiles first")
    release = conn.execute(
        "SELECT id FROM attack_releases WHERE is_pinned = 1").fetchone()
    if release is None:
        raise ValueError("no pinned attack_releases row")

    steps = PROFILE_STEPS.get(profile_name, [])
    phase_sequence = [s[0] for s in steps]

    now = utcnow()
    cur = conn.execute(
        "INSERT INTO sim_scenarios(profile_id, seed, phase_sequence, "
        "release_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (profile["id"], seed, json.dumps(phase_sequence), release["id"], now))
    scenario_id = cur.lastrowid

    gap_ids: list[int] = []
    coverage_by_phase: dict[str, list[str]] = {}
    for seq, (phase, attack_id, intent) in enumerate(steps, start=1):
        tech = conn.execute(
            "SELECT id FROM techniques WHERE attack_id = ?", (attack_id,)
        ).fetchone()
        if tech is None:
            raise ValueError(f"{profile_name}: no techniques row for {attack_id}")
        basis, success_predicted, rows = _basis_for_step(
            conn, tech["id"], attack_id, intent)

        step_cur = conn.execute(
            "INSERT INTO sim_steps(scenario_id, seq, technique_id, intent, "
            "success_predicted, basis) VALUES (?, ?, ?, ?, ?, ?)",
            (scenario_id, seq, tech["id"], intent, success_predicted, basis))
        step_id = step_cur.lastrowid
        coverage_by_phase.setdefault(phase, []).append(attack_id)

        for r in rows:
            gap_worthy = (
                r["verdict"] in ("uncovered", "asserted_unproven")
                or r["clock_state"] in ("never", "invalid")
            )
            if not gap_worthy:
                continue
            if r["clock_state"] == "never":
                latency = "∞ (clock state=never, no verification has ever run)"
            elif r["clock_state"] == "invalid":
                latency = "unknown (clock state=invalid)"
            else:
                latency = "unknown (no detecting clock for this surface)"
            question = (f"{attack_id} on {r['surface']}: detection = "
                       f"{r['detect_via'] or '(none)'}; verdict={r['verdict']}. "
                       f"Gap: detection latency is {latency} under current state.")
            gap_cur = conn.execute(
                "INSERT INTO sim_gaps(scenario_id, step_id, gap_kind, "
                "question, verdict, raised_into_brief, recommendation_id) "
                "VALUES (?, ?, ?, ?, ?, 1, NULL)",
                (scenario_id, step_id, "detection_latency", question, r["verdict"]))
            gap_ids.append(gap_cur.lastrowid)
        if not rows:
            gap_cur = conn.execute(
                "INSERT INTO sim_gaps(scenario_id, step_id, gap_kind, "
                "question, verdict, raised_into_brief, recommendation_id) "
                "VALUES (?, ?, ?, ?, ?, 1, NULL)",
                (scenario_id, step_id, "no_mapping",
                 f"{attack_id}: no ttp_mappings row exists for this "
                 "portfolio's surfaces — deterred, not blind: the "
                 "selection rubric excluded it (ttp/LIBRARY.md).",
                 "uncovered"))
            gap_ids.append(gap_cur.lastrowid)

    summary = (f"{profile_name}: {len(steps)} steps simulated across phases "
              f"{phase_sequence}; {len(gap_ids)} gap probe(s) raised.")
    conn.execute(
        "INSERT INTO sim_outcomes(scenario_id, summary, top_gap_ids, "
        "coverage_by_phase) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(scenario_id) DO UPDATE SET summary=excluded.summary, "
        "top_gap_ids=excluded.top_gap_ids, "
        "coverage_by_phase=excluded.coverage_by_phase",
        (scenario_id, summary, json.dumps(gap_ids[:3]),
         json.dumps(coverage_by_phase)))

    conn.commit()
    checkpoint(conn)
    return {"scenario_id": scenario_id, "profile": profile_name,
            "steps": len(steps), "gaps": len(gap_ids), "summary": summary}


def run_all(conn, seed: int = 1) -> list[dict]:
    return [run_scenario(conn, name, seed) for name in PROFILE_STEPS]


def main(argv: list[str]) -> int:
    conn = connect()
    if argv and argv[0] != "all":
        out = [run_scenario(conn, argv[0], int(argv[1]) if len(argv) > 1 else 1)]
    else:
        out = run_all(conn)
    conn.close()
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
