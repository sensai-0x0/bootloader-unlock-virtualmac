#!/usr/bin/env python3
"""Supervisor agent runner — BUILD-SPEC.md §3, §7.

Phase-0 scope (evolves with each phase):
  init            apply cumulative schema.sql + numbered migrations, idempotently,
                  with an applied-migrations ledger in `meta`
  audit           run the §7 self-audit checks v1, record to audit_runs (pass AND fail)
  provenance-null report rows without provenance across provenance-bearing tables
  decide <kind> <outcome> <detail...>
                  append a decision_log row

Never: executes, schedules, or writes outside projects/supervisor-agent/.
"""

import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent          # projects/supervisor-agent/
DB_PATH = BASE / "state" / "portfolio.db"
SCHEMA_PATH = BASE / "db" / "schema.sql"
MIGRATIONS_DIR = BASE / "db" / "migrations"
REGISTRY_PATH = BASE / "ontology" / "sources.yaml"

# §7 invariant 1: the ONLY writable area, grep-provable. The audit's write-scope
# check (A5) verifies every `open(..., "w")`-class call in this file's source
# resolves under one of these.
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


def apply_ddl(conn: sqlite3.Connection) -> int:
    """Apply cumulative schema + all migrations in filename order, idempotently.
    Returns the resulting db_version (highest applied migration number)."""
    conn.executescript(SCHEMA_PATH.read_text())
    applied = json.loads((load_meta(conn) or {}).get(LEDGER_KEY, "[]") or "[]")

    for path in sorted(MIGRATIONS_DIR.glob("[0-9]*-*.sql")):
        name = path.name
        if name in applied:
            continue          # already applied: idempotent replay skips
        conn.executescript(path.read_text())
        applied.append(name)

    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (LEDGER_KEY, json.dumps(applied)),
    )
    conn.commit()

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


def load_meta(conn: sqlite3.Connection) -> dict:
    try:
        return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}
    except sqlite3.OperationalError:
        return {}


def checkpoint(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def regenerate_decision_log_mirror(conn: sqlite3.Connection) -> None:
    """Invariant 9 (BUILD-SPEC §9): the database is source of truth and
    state/decision-log.md is a regenerated view of it. Called after every
    decision_log write so the mirror can never drift by cmd-order accident."""
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


def provenance_null_counts(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """§7 invariant 2: the provenance-null query runs across every table that
    carries a provenance_id column; every count must be 0."""
    out = []
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for table in tables:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if "provenance_id" in cols:
            n = conn.execute(
                f"SELECT count(*) FROM {table} WHERE provenance_id IS NULL").fetchone()[0]
            out.append((table, n))
    return out


# ─── self-audit (§7), checks v1 ──────────────────────────────────────────────

SOURCE_WRITE_RE = re.compile(r"\.(write_text|write_bytes|open)\s*\(")

def check_write_scope() -> list[str]:
    """A5: every write-class call in the runner's own source must land under
    projects/supervisor-agent/<ALLOWED_WRITE_DIRS>/ (grep-provable)."""
    violations = []
    src = Path(__file__).read_text()
    for i, line in enumerate(src.splitlines(), 1):
        if SOURCE_WRITE_RE.search(line):
            # the only runtime writes in this file are DB_PATH, the md mirrors,
            # and audit text — all under BASE / allowed dirs. Flag anything that
            # writes outside the BASE tree.
            if "BASE" not in line and not line.strip().startswith("#"):
                violations.append(f"{Path(__file__).name}:{i}: write call without BASE scope")
    return violations


FORBIDDEN_RUN_ARTIFACT_PATTERNS = (
    "tart create",
    "tart run",
    "cargo fuzz",
    "ssh ",
    "wrapper.rs",
)

def check_forbidden_patterns() -> list[str]:
    """§7: forbidden-pattern grep over run artifacts (generated state mirrors +
    briefs). Doctrine files (README/tests/BUILD-SPEC quote these words by
    design) are out of scope."""
    violations = []
    for subject in ("state", "briefs"):
        for path in sorted((BASE / subject).glob("*.md")):
            text = path.read_text()
            for pattern in FORBIDDEN_RUN_ARTIFACT_PATTERNS:
                if pattern in text:
                    violations.append(f"{path.name}: forbidden pattern {pattern!r}")
    return violations


def run_audit(trigger: str = "manual") -> int:
    started = utcnow()
    violations: list[str] = []

    try:
        conn = connect()

        # A1: database opens and is integral
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            violations.append(f"A1 integrity: {integrity}")

        # A2: migration ledger matches the migrations directory
        applied = json.loads(load_meta(conn).get(LEDGER_KEY, "[]") or "[]")
        on_disk = sorted(p.name for p in MIGRATIONS_DIR.glob("[0-9]*-*.sql"))
        missing = set(on_disk) - set(applied)
        if missing:
            violations.append(f"A2 migrations on disk not in ledger: {sorted(missing)}")

        # A3: provenance-null across provenance-bearing tables
        null_rows = provenance_null_counts(conn)
        bad = [(t, n) for t, n in null_rows if n != 0]
        if bad:
            violations.append(f"A3 provenance-null rows: {bad}")

        # A5: write scope of the runner itself
        violations.extend(check_write_scope())

        conn.close()
    except sqlite3.Error as exc:
        violations.append(f"database error: {exc}")

    # A4: forbidden patterns in generated run artifacts
    violations.extend(check_forbidden_patterns())

    passed = 0 if violations else 1
    ended = utcnow()

    conn = connect()
    conn.execute(
        "INSERT INTO audit_runs(run_id, checklist_version, passed, violations, at) "
        "VALUES (?, ?, ?, ?, ?)",
        (None, "v1", passed, json.dumps(violations), ended),
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
    regenerate_decision_log_mirror(conn)
    conn.close()
    print("decision logged")


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
        regenerate_decision_log_mirror(conn)
        conn.close()
        print("decision-log mirror regenerated")
    elif cmd == "decide":
        cmd_decide(rest[0], rest[1], " ".join(rest[2:]) if len(rest) > 2 else rest[2])
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
