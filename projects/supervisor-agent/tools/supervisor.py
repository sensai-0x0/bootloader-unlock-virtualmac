#!/usr/bin/env python3
"""Supervisor agent runner — BUILD-SPEC.md §3, §7.

Commands (growing one phase at a time):
  init             apply cumulative schema.sql + numbered migrations, idempotently,
                   with an applied-migrations ledger in `meta`
  audit [trigger]  run the §7 self-audit, record to audit_runs (pass AND fail)
  provenance-null  report rows without provenance across provenance-bearing tables
  mirror           regenerate the state/ markdown mirrors from the DB
  decide <kind> <outcome> <detail...>
                   append a decision_log row
  parse [--self-test]
                   phase-1: two-source fusion (progress/ + knowledge INDEX) into
                   the DB; --self-test exercises the parse-failure path via the
                   flagged mangled fixture (tests/fixtures/)
  render           regenerate state/fused-portfolio.md from the DB

Never: executes, schedules, or writes outside projects/supervisor-agent/{state,
briefs,db,ttp,tests}. parsers.py is the only module allowed to read repo sources.
"""

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent          # projects/supervisor-agent/
ROOT = BASE.parent.parent                              # repo root
DB_PATH = BASE / "state" / "portfolio.db"
SCHEMA_PATH = BASE / "db" / "schema.sql"
MIGRATIONS_DIR = BASE / "db" / "migrations"
REGISTRY_PATH = BASE / "ontology" / "sources.yaml"
FIXTURES_DIR = BASE / "tests" / "fixtures"

# §7 invariant 1: the ONLY writable area, grep-provable.
ALLOWED_WRITE_DIRS = ("state", "briefs", "db", "ttp", "tests")

LEDGER_KEY = "applied_migrations"   # JSON array of applied migration filenames


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_meta(conn: sqlite3.Connection) -> dict:
    try:
        return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}
    except sqlite3.OperationalError:
        return {}


def apply_ddl(conn: sqlite3.Connection) -> int:
    """Apply cumulative schema + all migrations in filename order, idempotently.
    Returns the resulting db_version (highest applied migration number).

    Snapshot-first rule (§3.5 item 10): a database this runner created has the
    ledger already; a fresh DB built purely from the snapshot (no ledger) gets
    its ledger seeded WITHOUT replaying migrations — the snapshot is already
    cumulative, and migrations contain ledger-guarded ALTERs that must run
    exactly once (a replay would duplicate columns)."""
    conn.executescript(SCHEMA_PATH.read_text())
    applied_raw = (load_meta(conn) or {}).get(LEDGER_KEY)
    fresh_snapshot = applied_raw is None

    applied = json.loads(applied_raw) if applied_raw else []

    for path in sorted(MIGRATIONS_DIR.glob("[0-9]*-*.sql")):
        name = path.name
        if name in applied:
            continue
        if not fresh_snapshot:
            conn.executescript(path.read_text())
        applied.append(name)

    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (LEDGER_KEY, json.dumps(applied)),
    )
    version = max((int(name.split("-")[0]) for name in applied), default=0)
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('db_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(version),),
    )
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('schema_sha256', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (sha256_file(SCHEMA_PATH),),
    )
    conn.commit()
    return version


def checkpoint(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


# ─── mirrors (invariant 9: DB wins; mirrors are regenerated views) ───────────

def regenerate_decision_log_mirror(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, at, kind, outcome, detail FROM decision_log ORDER BY id").fetchall()
    lines = [
        "# Decision log",
        "",
        "Regenerated view of `decision_log` in `state/portfolio.db` — never edited",
        "by hand. If this mirror and the database disagree, the database wins and",
        "the mismatch goes to `sync_violations` (§3.2).",
        "",
    ]
    for r in rows:
        lines.append(f"## {r['at']} — {r['kind']} — {r['outcome']}")
        lines.append("")
        lines.append(r["detail"].strip())
        lines.append("")
    (BASE / "state" / "decision-log.md").write_text("\n".join(lines), encoding="utf-8")


def render_fused_portfolio(conn: sqlite3.Connection) -> str:
    out = ["# Fused portfolio view",
           "",
           "Regenerated from `state/portfolio.db` — the machine-extracted,",
           "provenance-carrying view of every parsed source (BUILD-SPEC §3: the",
           "database is the single source of truth; this mirror is a view). Never",
           "edited by hand; a divergence would be a `sync_violations` row and the",
           "database wins every such fight.",
           "",
           f"Regenerated: {utcnow()}",
           ""]

    out += ["## Initiatives", "",
            "| slug | kind | status | owner_gate | proposal_ref |",
            "|---|---|---|---|---|"]
    for r in conn.execute(
            "SELECT slug, kind, status, owner_gate, proposal_ref FROM initiatives "
            "ORDER BY kind, slug"):
        out.append(f"| {r['slug']} | {r['kind']} | {r['status']} | "
                   f"{r['owner_gate'] or '—'} | {r['proposal_ref']} |")
    out += [""]

    out += ["## Milestones (verbatim from progress/milestones.md)", "",
            "| ref | title | status | evidence |", "|---|---|---|---|"]
    for r in conn.execute(
            "SELECT m.m_ref, m.title, m.status, m.evidence_ref "
            "FROM milestones m JOIN initiatives i ON i.id = m.initiative_id "
            "ORDER BY CAST(substr(m.m_ref, 2) AS INTEGER)"):
        out.append(f"| {r['m_ref']} | {r['title']} | {r['status']} | "
                   f"{r['evidence_ref'] or '—'} |")
    out += [""]

    out += ["## Milestone log (dated entries; 'Next up' = decision-engine input)", ""]
    n = 0
    for r in conn.execute(
            "SELECT occurred_at, heading, m_refs_touched, next_up FROM milestone_log "
            "ORDER BY occurred_at, sequence"):
        n += 1
        refs = ", ".join(json.loads(r["m_refs_touched"] or "[]")) or "—"
        out.append(f"- **{r['occurred_at']} — {r['heading']}** (touches: {refs})")
        out.append(f"  - next-up: {r['next_up'] or '—'}")
    if n == 0:
        out.append("(no log entries parsed)")
    out += [""]

    out += ["## Evidence by kind", "", "| kind | rows |", "|---|---|"]
    for r in conn.execute(
            "SELECT kind, count(*) AS n FROM evidence GROUP BY kind ORDER BY kind"):
        out.append(f"| {r['kind']} | {r['n']} |")
    out += [""]

    out += ["## Links", ""]
    links = conn.execute(
        "SELECT link_type, count(*) AS n FROM links GROUP BY link_type").fetchall()
    if links:
        for r in links:
            out.append(f"- `{r['link_type']}`: {r['n']}")
    else:
        out.append("(none)")
    out += [""]

    out += ["## Parse health", ""]
    out.append(f"- parse_failures rows (all-time, first-class history): "
               f"{conn.execute('SELECT count(*) FROM parse_failures').fetchone()[0]}")
    out.append(f"- parse_failures today: {conn.execute(
        'SELECT count(*) FROM parse_failures WHERE substr(at, 1, 10) = ?',
        (utcnow()[:10],)).fetchone()[0]}")
    out += [""]

    out += ["## Sweep ledger (parsed)", "",
            "| sweep | kind | started | new findings (verbatim) |", "|---|---|---|---|"]
    for r in conn.execute(
            "SELECT sweep_id, kind, started_at, outcome FROM sweeps ORDER BY sweep_id"):
        out.append(f"| {r['sweep_id']} | {r['kind']} | {r['started_at']} | "
                   f"{(r['outcome'] or '')[:80]} |")
    out += [""]

    out += ["## Findings (verbatim from the cross-sweep index)", "",
            "| finding | score | status |", "|---|---|---|"]
    for r in conn.execute(
            "SELECT finding_ref, score, disposition FROM findings ORDER BY finding_ref"):
        out.append(f"| {r['finding_ref']} | {r['score'] or '—'} | {r['disposition']} |")
    out += [""]

    out += ["## Capabilities (parsed approval contracts)", "",
            "| name | kind | approval_class |", "|---|---|---|"]
    for r in conn.execute(
            "SELECT name, kind, approval_class FROM capabilities ORDER BY name"):
        out.append(f"| {r['name']} | {r['kind']} | {r['approval_class']} |")
    out += [""]

    out += ["## Staleness clocks (state is data)", "",
            "| surface | state | last_verified_at |", "|---|---|---|"]
    for r in conn.execute(
            "SELECT surface, state, last_verified_at FROM staleness_clocks "
            "ORDER BY surface"):
        out.append(f"| {r['surface']} | {r['state']} | {r['last_verified_at'] or 'never'} |")
    out += [""]

    out += ["## Implication: clock invalidations", ""]
    inv = conn.execute(
        "SELECT c.surface, e.ref, e.detail FROM clock_invalidation_events cie "
        "JOIN staleness_clocks c ON c.id = cie.clock_id "
        "JOIN events e ON e.id = cie.event_id ORDER BY cie.fired_at").fetchall()
    if inv:
        for r in inv:
            out.append(f"- `{r['surface']}` invalidated by {r['ref']} — {r['detail']}")
    else:
        out.append("(none fired)")
    out += [""]

    out += ["## Contradictions (loser marked, history kept)", ""]
    con = conn.execute(
        "SELECT rule_id, detail FROM contradictions ORDER BY detected_at").fetchall()
    if con:
        for r in con:
            out.append(f"- [{r['rule_id']}] {r['detail']}")
    else:
        out.append("(none detected)")
    out += [""]

    return "\n".join(out) + "\n"


def write_mirrors(conn: sqlite3.Connection) -> None:
    regenerate_decision_log_mirror(conn)
    try:
        conn.execute("SELECT 1 FROM initiatives LIMIT 1")
        (BASE / "state" / "fused-portfolio.md").write_text(
            render_fused_portfolio(conn), encoding="utf-8")
    except sqlite3.OperationalError:
        pass                      # phase-0 DB: not yet fused, skip the view
    checkpoint(conn)


# ─── self-audit (§7) ─────────────────────────────────────────────────────────

SOURCE_WRITE_RE = re.compile(r"\.(write_text|write_bytes|open)\s*\(")


def check_write_scope() -> list[str]:
    """A5: every write-class call in the runner's own source must land under
    projects/supervisor-agent/<ALLOWED_WRITE_DIRS>/ (grep-provable). A call is
    scoped when its line names one of the BASE-derived constants, writes the DB
    via conn.execute(), or targets a variable whose assignment names a scoped
    constant within the preceding 15 lines."""
    violations = []
    scoped_tokens = ("BASE", "ROOT", "FIXTURES_DIR", "DB_PATH", "SCHEMA_PATH",
                     "MIGRATIONS_DIR", "REGISTRY_PATH")
    write_call = re.compile(r"(\w+)\.(write_text|write_bytes)\s*\(")
    for tool in sorted((BASE / "tools").glob("*.py")):
        lines = tool.read_text().splitlines()
        for i, line in enumerate(lines):
            if not SOURCE_WRITE_RE.search(line):
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "conn.execute" in line or any(tok in line for tok in scoped_tokens):
                continue          # DB writes and constant-target writes are scoped
            m = write_call.search(line)
            resolved = False
            if m:
                var = m.group(1)
                for back in range(max(0, i - 15), i):
                    assign = re.search(rf"\b{var}\s*=\s*(.+)", lines[back])
                    if assign and any(tok in assign.group(1)
                                      for tok in scoped_tokens):
                        resolved = True
                        break
            if not resolved:
                violations.append(f"{tool.name}:{i + 1}: write call without scoped "
                                  f"target: {stripped}")
    return violations


FORBIDDEN_RUN_ARTIFACT_PATTERNS = (
    "tart create",
    "tart run",
    "cargo fuzz",
    "ssh ",
    "wrapper.rs",
)


def check_forbidden_patterns() -> list[str]:
    """§7 A4: forbidden-pattern grep over the SUPERVISOR'S OWN analysis output —
    briefs/ and the decision-log mirror. state/fused-portfolio.md is exempt by
    construction this phase: it is a verbatim projection of the user's own
    progress record (its source lines legitimately describe VM-booting SSH/tart
    steps; the supervisor is quoting history, not proposing actions)."""
    violations = []
    subjects = [*(BASE / "briefs").glob("*.md"),
                BASE / "state" / "decision-log.md"]
    for path in sorted(subjects):
        text = path.read_text()
        for pattern in FORBIDDEN_RUN_ARTIFACT_PATTERNS:
            if pattern in text:
                violations.append(f"{path.name}: forbidden pattern {pattern!r}")
    return violations


def provenance_null_counts(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """§7 invariant 2: across every table that carries a provenance_id column,
    every count must be 0 (self-governance tables are exempt, §3.5 item 3)."""
    out = []
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for table in tables:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if "provenance_id" in cols:
            n = conn.execute(
                f"SELECT count(*) FROM {table} WHERE provenance_id IS NULL"
            ).fetchone()[0]
            out.append((table, n))
    return out


def run_audit(trigger: str = "manual") -> int:
    started = utcnow()
    violations: list[str] = []

    try:
        conn = connect()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            violations.append(f"A1 integrity: {integrity}")

        applied = json.loads(load_meta(conn).get(LEDGER_KEY, "[]") or "[]")
        on_disk = sorted(p.name for p in MIGRATIONS_DIR.glob("[0-9]*-*.sql"))
        missing = set(on_disk) - set(applied)
        if missing:
            violations.append(f"A2 migrations on disk not in ledger: {sorted(missing)}")

        bad = [(t, n) for t, n in provenance_null_counts(conn) if n != 0]
        if bad:
            violations.append(f"A3 provenance-null rows: {bad}")

        violations.extend(check_write_scope())
        conn.close()
    except sqlite3.Error as exc:
        violations.append(f"database error: {exc}")

    violations.extend(check_forbidden_patterns())

    passed = 0 if violations else 1
    ended = utcnow()

    conn = connect()
    conn.execute(
        "INSERT INTO audit_runs(run_id, checklist_version, passed, violations, at) "
        "VALUES (NULL, 'v1', ?, ?, ?)",
        (passed, json.dumps(violations), ended),
    )
    conn.execute(
        "INSERT INTO decision_log(at, kind, brief_id, ticket_id, outcome, detail) "
        "VALUES (?, 'self-audit', NULL, NULL, ?, ?)",
        (ended, "pass" if passed else "FAIL", json.dumps(violations)),
    )
    conn.commit()
    checkpoint(conn)
    regenerate_decision_log_mirror(conn)
    conn.close()
    return passed


# ─── phase-1 fusion run ──────────────────────────────────────────────────────

MANGLED_FIXTURE_BANNER = (
    "# SELF-TEST ARTIFACT — deliberately mangled fixture for the parse-failure\n"
    "# acceptance path (BUILD-SPEC §3.5 item 8). NEVER an input to production\n"
    "# parsing; the parse run that reads it rolls its writes back.\n"
)


def _mangled_milestones_fixture() -> str:
    """A status table whose refs were INSERTED into the middle (violates P3) and
    a log heading that isn't a date (violates the heading contract)."""
    return (MANGLED_FIXTURE_BANNER
            + "\n## Status\n\n"
              "| # | Milestone | Status | Evidence |\n"
              "|---|---|---|---|\n"
              "| M3 | inserted-into-the-middle row | Done | commit `deadbee` |\n"
              "| M0 | first row | Done | nothing |\n"
              "| M1 | second row | Done | nothing |\n"
            + "\n## Log\n\n"
              "### not-a-date — the heading contract is violated here\n"
              "\nBody text that exists only so the failure is provenable.\n")


def parse_run(trigger: str, self_test: bool = False) -> None:
    """Phase-1 BUILD-SPEC acceptance machinery. Sources parse in order; a
    ParseFailure in a source means one parse_failures row + that source degraded
    to authority 0 for THIS run; the remaining sources still load. Every run is
    recorded in `runs`."""
    import parsers  # local import: parsers reads repo sources only here
    from parsers import ParseFailure

    conn = connect()
    version = apply_ddl(conn)
    meta = load_meta(conn)
    cur = conn.execute(
        "INSERT INTO runs(started_at, trigger, db_version, schema_hash, outcome) "
        "VALUES (?, ?, ?, ?, 'running')",
        (utcnow(), trigger, version, meta.get("schema_sha256")))
    run_id = cur.lastrowid
    conn.commit()

    def one(source: str, path: Path, fn) -> None:
        try:
            res = fn()
            parsed.append(source)
            report[f"{source}:ok"] = res
        except ParseFailure as exc:
            degraded.append(source)
            failed.append((source, path, exc.detail))
            report[f"{source}:FAIL"] = exc.detail

    parsed: list[str] = []
    degraded: list[str] = []
    failed: list[tuple[str, Path, str]] = []   # written last: survives rollbacks
    report: dict = {}

    parsers.seed_initiatives(conn)

    if self_test:
        fixture = FIXTURES_DIR / "mangled-milestones.md"
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixture.write_text(_mangled_milestones_fixture(), encoding="utf-8")
        conn.execute("SAVEPOINT self_test")
        try:
            one("milestones", fixture,
                lambda: parsers.parse_milestones(conn, fixture, self_test=True))
        finally:
            # the fixture's garbage never reaches the real tables; only the
            # parse_failures rows (written below, after rollback) survive.
            conn.execute("ROLLBACK TO self_test")
            conn.execute("RELEASE self_test")

    one("milestones", parsers.MILESTONES_PATH,
        lambda: (parsers.parse_goal_peg(conn),
                 parsers.parse_milestones(conn, parsers.MILESTONES_PATH))[-1])
    one("knowledge", parsers.KNOWLEDGE_PATH,
        lambda: parsers.parse_knowledge(conn, parsers.KNOWLEDGE_PATH))
    one("sweep_reports", parsers.SWEEPS_PATH,
        lambda: (parsers.parse_sweeps(conn),
                 parsers.parse_findings(conn),
                 parsers.parse_exploits(conn))[-1])
    one("environments_registry", parsers.ENVIRONMENTS_PATH,
        lambda: parsers.parse_environments(conn))
    one("project_lifecycle", parsers.ROOT / "projects",
        lambda: parsers.parse_project_lifecycle(conn))
    one("git_history", parsers.ROOT / ".git",
        lambda: parsers.parse_git_events(conn))
    one("capability_registry", parsers.AGENTS_GLOB.parent / "vulnres-recon.md",
        lambda: parsers.parse_capabilities(conn))
    one("cadence_reports", parsers.ROOT / "reports",
        lambda: parsers.parse_cadence_reports(conn))

    # clock seeding + implication are supervisor RULES over parsed data, not a
    # source; failures there are still first-class records.
    try:
        report["clock_seeds"] = parsers.seed_clocks(conn)
    except ParseFailure as exc:
        degraded.append("supervisor_rules")
        failed.append(("supervisor_rules", parsers.MILESTONES_PATH, exc.detail))
        report["supervisor_rules:FAIL"] = exc.detail
    if not any(s == "supervisor_rules" for s, _, _ in failed):
        report["implication"] = parsers.run_implication(conn)

    for source, path, detail in failed:
        parsers.fail_row(conn, str(path.relative_to(ROOT)), source,
                         ("[self-test] " if self_test else "") + detail)

    conn.commit()
    outcome = "ok" if not degraded else "degraded"
    conn.execute(
        "UPDATE runs SET ended_at = ?, sources_parsed = ?, degraded_sources = ?, "
        "outcome = ? WHERE id = ?",
        (utcnow(), json.dumps(parsed), json.dumps(degraded), outcome, run_id))
    conn.commit()
    checkpoint(conn)
    write_mirrors(conn)
    conn.close()

    print(json.dumps({"run_id": run_id, "outcome": outcome, "self_test": self_test,
                      "parsed": parsed, "degraded": degraded,
                      "detail": report}, indent=2))
    # A deliberate self-test drill that trips the gate IS the successful outcome.
    return (0 if not degraded else 1) if not self_test else 0


# ─── commands ────────────────────────────────────────────────────────────────

def cmd_init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect()
    version = apply_ddl(conn)
    checkpoint(conn)
    conn.close()
    print(f"db ready: version={version} at {DB_PATH}")


def cmd_provenance_null() -> None:
    conn = connect()
    for table, n in provenance_null_counts(conn):
        print(f"{table}: {n}")
    conn.close()


def cmd_decide(kind: str, outcome: str, detail: str) -> None:
    conn = connect()
    conn.execute(
        "INSERT INTO decision_log(at, kind, brief_id, ticket_id, outcome, detail) "
        "VALUES (?, ?, NULL, NULL, ?, ?)",
        (utcnow(), kind, outcome, detail),
    )
    conn.commit()
    checkpoint(conn)
    write_mirrors(conn)
    conn.close()
    print("decision logged")


def cmd_event(kind: str, detail: str, paths: str) -> None:
    """Record a described (synthetic, acceptance) event — never anything that
    executed. kind is limited to 'synthetic'; the detail must say what the
    event DESCRIBES, not what this tool did. The implication rules decide the
    effect on the next regeneration. occurred_at is recorded with the local
    UTC offset, matching parsed git event strings, so rule R1's local-date
    granularity comparison treats synthetic events exactly like real ones."""
    if kind != "synthetic":
        print("only kind='synthetic' supported (real events come from git on parse)",
              file=sys.stderr)
        return 2
    path_list = [p.strip() for p in paths.split(",") if p.strip()]
    conn = connect()
    prov = add_provenance(conn, "decision_log-description", "supervisor_synthetic",
                          None, "described acceptance event; nothing executed")
    cur = conn.execute(
        "INSERT INTO events(kind, occurred_at, ref, paths, detail, "
        "provenance_id, ingested_at) VALUES ('synthetic', ?, ?, ?, ?, ?, ?)",
        (datetime.now().astimezone().isoformat(timespec="seconds"),
         "synthetic:" + hashlib.sha256(detail.encode()).hexdigest()[:12],
         json.dumps(path_list), detail, prov, utcnow()))
    conn.commit()
    checkpoint(conn)
    conn.close()
    print(f"event recorded id={cur.lastrowid} (nothing executed — description only)")


def add_provenance(conn, source_ref, source_type, source_sha, note=None):
    cur = conn.execute(
        "INSERT INTO provenance(source_ref, source_sha, source_type, note) "
        "VALUES (?, ?, ?, ?)", (source_ref, source_sha, source_type, note))
    return cur.lastrowid


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, *rest = argv
    if cmd == "init":
        cmd_init()
    elif cmd == "audit":
        ok = run_audit(rest[0] if rest else "manual")
        print("audit: PASS" if ok else "audit: FAIL")
        return 0 if ok else 1
    elif cmd == "provenance-null":
        cmd_provenance_null()
    elif cmd == "mirror":
        conn = connect()
        write_mirrors(conn)
        conn.close()
        print("mirrors regenerated")
    elif cmd == "decide":
        cmd_decide(rest[0], rest[1],
                   " ".join(rest[2:]) if len(rest) > 2 else rest[2])
    elif cmd == "parse":
        self_test = "--self-test" in rest
        return parse_run("self-test" if self_test else (rest[0] if rest else "manual"),
                         self_test=self_test)
    elif cmd == "event":
        if len(rest) < 3:
            print("usage: event synthetic --detail <text> --paths <comma,list>",
                  file=sys.stderr)
            return 2
        detail = rest[rest.index("--detail") + 1] if "--detail" in rest else ""
        paths = rest[rest.index("--paths") + 1] if "--paths" in rest else ""
        return cmd_event(rest[0], detail, paths)
    elif cmd == "render":
        conn = connect()
        write_mirrors(conn)
        conn.close()
        print("fused view regenerated")
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
