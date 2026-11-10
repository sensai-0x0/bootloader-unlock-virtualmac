#!/usr/bin/env python3
"""Supervisor agent parsers — BUILD-SPEC §2, ontology/SCHEMA.md parser contracts.

Phase-2 scope adds sources 3–7 (sweep reports, environments, project lifecycle,
git history, capability registry) plus staleness-clock seeding and the
reviewed-SQL implication run (db/queries/r1-*.sql, r2-*.sql).

Rules implemented (each traces to ontology/SCHEMA.md):
  P1 parse failures are first-class (parse_failures row + authority 0 for the run)
  P2 newer dated entries outrank older ones and nothing else does
  P3 milestone refs are append-only; renumbering/insertion is a parse failure
  P4 knowledge entry kind is parsed data (footer-declared, not guessed)
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supervisor import ROOT, utcnow, connect  # noqa: E402

MILESTONES_PATH = ROOT / "progress/milestones.md"
GOAL_PATH = ROOT / "progress/goal.md"
KNOWLEDGE_PATH = ROOT / "vuln_res/knowledge/INDEX.md"
SWEEPS_PATH = ROOT / "vuln_res/sweep-reports/INDEX.md"
FINDINGS_PATH = ROOT / "vuln_res/sweep-reports/findings-index.md"
EXPLOITS_PATH = ROOT / "vuln_res/sweep-reports/exploits-index.md"
ENVIRONMENTS_PATH = ROOT / "vuln_res/knowledge/environments/INDEX.md"
CADENCE_PATHS = ((ROOT / "reports/daily/INDEX.md", "daily"),
                 (ROOT / "reports/weekly/INDEX.md", "weekly"),
                 (ROOT / "reports/monthly/INDEX.md", "monthly"))
AGENTS_GLOB = ROOT / ".claude/agents/vulnres-*.md"
SKILLS_GLOB = ROOT / ".claude/skills/vulnres-*/SKILL.md"

# git window: phase-2 events are file-level from the earliest date any parsed
# claim itself asserts (the knowledge entries' 2026-11-10 `updated:` dates).
# Extending the window = extending what can invalidate, a reviewed change.
GIT_SINCE = "2026-11-10"

# contract-defined initiatives: slug → (kind, name, proposal_ref)
CONTRACT_INITIATIVES = {
    "vm_sec_research": ("vm_sec_research", "Simulated-macOS bootloader research",
                        "progress/goal.md"),
    "vulnres_suite": ("vulnres_suite", "vuln_res static-analysis sweep suite",
                      "vuln_res/README.md"),
    "project1_fuzz": ("project1_fuzz", "Project 1 — Continuous Fuzz Bug Hunter",
                      "projects/01-continuous-fuzz-bug-hunter/PROPOSAL.md"),
    "project2_mutation": ("project2_mutation", "Project 2 — Gated Mutation Engine",
                          "projects/02-gated-mutation-engine/PROPOSAL.md"),
    "project3_drift": ("project3_drift", "Project 3 — Fleet Drift Watch",
                       "projects/03-fleet-drift-watch/PROPOSAL.md"),
    "supervisor": ("supervisor", "Portfolio Supervisor (supervizor)",
                   "projects/supervisor-agent/PROPOSAL.md"),
}

# milestone refs each anchored initiative owns (mirrors ontology/sources.yaml
# `milestone_anchors`; §3.5 item 7 — registering a range is what BINDS a source)
MILESTONE_ANCHORS = {"vm_sec_research": (0, 10)}

TABLE_ROW = re.compile(r"^\|\s*(M\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
ENTRY_LINK = re.compile(
    r"^- \[([^\]]+)\]\(([^)]+)\)\s+—\s+(.*?)\s+\(updated:\s*(\d{4}-\d{2}-\d{2})\)\s*$")
M_REF = re.compile(r"\bM(\d+)\b")
SWEEP_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}-\d{3}-.+?)\s*$")
BULLET = re.compile(r"^- \*\*(.+?):\*\*\s*(.+)$")
INDEX_ROW = re.compile(r"^- \[([^\]]+)\]\(([^)]+)\)\s+—\s+(.*)$")
FINDING_ROW = re.compile(
    r"^\|\s*\[`([^`]+)`\]\(([^)]+)\)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
    r"\s*\[([^]]+)\]\(([^)]+)\)\s*\|\s*$")
ENV_ROW = re.compile(r"^- \[([\w-]+)\]\(([^)]+)\)\s+—\s+(.*?)\s+"
                     r"\(updated:\s*(\d{4}-\d{2}-\d{2})\)\s*$")
CURRENCY_RE = re.compile(
    r"\b(clean|cleared|zero\s+vulnerabilities|0\s+vulnerabilities|"
    r"not\s+a\s+(real\s+)?guard\s+gap)\b", re.IGNORECASE)


class ParseFailure(Exception):
    """Raised by any parser that cannot honestly proceed; converted into a
    parse_failures row by the caller (the failure is data, never a skip)."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


# ─── shared helpers ──────────────────────────────────────────────────────────

def add_provenance(conn, source_ref: str, source_type: str,
                   source_sha: str | None, note: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO provenance(source_ref, source_sha, source_type, note) "
        "VALUES (?, ?, ?, ?)",
        (source_ref, source_sha, source_type, note))
    return cur.lastrowid


def fail_row(conn, source_ref: str, source_type: str, detail: str) -> None:
    path = ROOT / source_ref
    sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    prov_id = add_provenance(conn, source_ref, source_type, sha,
                             "parse failure record — this row IS the failure report")
    conn.execute(
        "INSERT INTO parse_failures(source_ref, at, detail, provenance_id) "
        "VALUES (?, ?, ?, ?)", (source_ref, utcnow(), detail, prov_id))


def initiative_id(conn, slug: str) -> int:
    row = conn.execute("SELECT id FROM initiatives WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ParseFailure(f"initiative slug not found: {slug}")
    return row["id"]


def sect(text: str, start_re: str) -> dict[str, list[str]]:
    """Split a file into named sections keyed by a heading regex's group(1)."""
    out: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        hm = re.match(start_re, line)
        if hm:
            current = hm.group(1)
            out.setdefault(current, [])
        if current is not None:
            out[current].append(line)
    return out


def bullets(lines: list[str]) -> dict[str, str]:
    """The fielded bullets format ('- **Agents run:** …') this suite uses."""
    out: dict[str, str] = {}
    last = None
    for line in lines:
        m = BULLET.match(line.strip())
        if m:
            last = m.group(1).lower()
            out[last] = m.group(2).strip()
        elif out and line.strip().startswith(("  ", "\t")) and last:
            out[last] += " " + line.strip()
    return out


# ─── contract initiatives ────────────────────────────────────────────────────

def seed_initiatives(conn) -> int:
    for slug, (kind, name, proposal_ref) in CONTRACT_INITIATIVES.items():
        prov_id = add_provenance(
            conn, proposal_ref, "contract_initiatives", None,
            "initiative row seeded from the BUILD-SPEC §3.1 contract; status is "
            "inference-with-provenance until a real status file exists "
            "(status_file_ref stays NULL)")
        conn.execute(
            "INSERT INTO initiatives(slug, name, kind, status, proposal_ref, "
            "owner_gate, provenance_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(slug) DO NOTHING",
            (slug, name, kind,
             "active" if kind in ("vulnres_suite", "vm_sec_research") else "pre-build",
             proposal_ref,
             "user_gated" if kind.startswith("project") else None,
             prov_id, utcnow()))
    return len(CONTRACT_INITIATIVES)


def initiative_for_m_ref(m_ref: str) -> str:
    n = int(m_ref[1:])
    for slug, (lo, hi) in MILESTONE_ANCHORS.items():
        if lo <= n <= hi:
            return slug
    raise ParseFailure(
        f"{m_ref} outside every registered anchor range (§3.5 item 7: register "
        "the range in ontology/sources.yaml before binding rows)")


# ─── source 1: milestones ────────────────────────────────────────────────────

def parse_milestones(conn, path: Path, self_test: bool = False) -> dict:
    """Status table → milestones (verbatim projection, upsert by natural key).
    Dated log → milestone_log (append) + evidence(kind=milestone) + 'bears-on'
    links. §3.5 item 8: a self-test run reads a flagged mangled fixture and
    records what fails, touching no real row."""
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    source_type = "milestones"
    sha = hashlib.sha256(text.encode()).hexdigest()
    results = {"source": source_type, "table_rows": 0, "log_entries": 0,
               "evidence": 0, "links": 0}

    sections = sect(text, r"^##\s+(.+)$")
    if "Status" not in sections or "Log" not in sections:
        raise ParseFailure("missing '## Status' and/or '## Log' sections")

    # P3 — table refs must be the registered anchor range, ascending.
    seen_refs: list[str] = []
    for line in sections["Status"]:
        m = TABLE_ROW.match(line)
        if m and not line.startswith("| #") and "---" not in line:
            seen_refs.append(m.group(1))
    nums = [int(r[1:]) for r in seen_refs]
    if nums != sorted(nums):
        raise ParseFailure(f"milestone refs not in ascending source order: {seen_refs}")
    unanchored = [r for r in seen_refs
                  if not any(lo <= int(r[1:]) <= hi
                             for lo, hi in MILESTONE_ANCHORS.values())]
    if unanchored:
        raise ParseFailure(
            f"milestone refs outside every registered anchor range: "
            f"{unanchored} (§3.5 item 7)")

    ini_id = initiative_id(conn, "vm_sec_research")
    prov_status = add_provenance(
        conn, f"{rel}#status-table", source_type, sha,
        "verbatim copy of the status table rows; ref set is append-only per P3")
    for line in sections["Status"]:
        m = TABLE_ROW.match(line)
        if not m:
            continue
        m_ref, title, status, evidence_ref = [g.strip() for g in m.groups()]
        conn.execute(
            "INSERT INTO milestones(initiative_id, m_ref, title, status, evidence_ref, "
            "provenance_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(initiative_id, m_ref) DO UPDATE SET "
            "title = excluded.title, status = excluded.status, "
            "evidence_ref = excluded.evidence_ref, "
            "provenance_id = excluded.provenance_id, ingested_at = excluded.ingested_at",
            (ini_id, m_ref, title, status, evidence_ref or None, prov_status, utcnow()))
        results["table_rows"] += 1

    prov_log = add_provenance(
        conn, f"{rel}#log", source_type, sha,
        "dated log entries; 'Next up' paragraphs parsed verbatim as "
        "decision-engine input, never treated as prose")
    log_lines = sections["Log"]
    entries: list[dict] = []
    current: dict | None = None
    for line in log_lines:
        hm = re.match(r"^###\s+(.+)$", line)
        if hm:
            if current:
                entries.append(current)
            current = {"heading": hm.group(1).strip(), "body": []}
        elif current is not None:
            current["body"].append(line)
    if current:
        entries.append(current)

    if not entries:
        raise ParseFailure("log section contains no '### ' dated headings")

    for seq, entry in enumerate(entries, 1):
        body = "\n".join(entry["body"]).strip()
        hm = re.match(
            r"^(\d{4}-\d{2}-\d{2})(?:\s*\((?:continued|follow-up)\))?\s*[—–-]\s+(.+)$",
            entry["heading"])
        if not hm:
            raise ParseFailure(
                f"log entry #{seq} heading is not 'YYYY-MM-DD — summary': "
                f"{entry['heading']!r}")
        occurred_at, heading_text = hm.group(1), hm.group(2).strip()
        refs = sorted({f"M{g}" for g in M_REF.findall(heading_text)},
                      key=lambda r: int(r[1:]))
        unknown = [r for r in refs if not initiative_for_m_ref_maybe(r)]
        if unknown:
            raise ParseFailure(
                f"log entry #{seq} touches unregistered milestone refs {unknown}: "
                f"{entry['heading']!r}")

        next_up = None
        nm = re.search(r"\*\*Next up:\*\*\s*(.*?)(?:\n\n|\Z)", body, re.DOTALL)
        if nm:
            next_up = " ".join(nm.group(1).split())

        entry_key = hashlib.sha256(
            f"{occurred_at}|{heading_text}".encode()).hexdigest()
        content_hash = hashlib.sha256(
            f"{occurred_at}|{heading_text}|{body}".encode()).hexdigest()

        cur = conn.execute(
            "INSERT INTO milestone_log(initiative_id, occurred_at, sequence, heading, "
            "m_refs_touched, detail, next_up, entry_key, provenance_id, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(entry_key) DO NOTHING",
            (ini_id, occurred_at, seq, heading_text,
             json.dumps(refs), body, next_up, entry_key, prov_log, utcnow()))
        if cur.rowcount:
            results["log_entries"] += 1

            ev_prov = add_provenance(
                conn, f"{rel}#log:{occurred_at}:{heading_text[:60]}", source_type,
                content_hash, "log entry ingested as evidence (kind=milestone)")
            cur2 = conn.execute(
                "INSERT INTO evidence(initiative_id, kind, verdict_class, content_hash, "
                "asserted_at, source_ref, provenance_id, ingested_at) "
                "VALUES (?, 'milestone', ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(source_ref, content_hash) DO NOTHING",
                (ini_id, "dated_log_entry", content_hash, occurred_at,
                 f"{rel}#{seq}-{occurred_at}", ev_prov, utcnow()))
            if cur2.rowcount:
                results["evidence"] += 1

            log_row = conn.execute(
                "SELECT id FROM milestone_log WHERE entry_key = ?", (entry_key,)
            ).fetchone()
            for r in refs:
                mrow = conn.execute(
                    "SELECT id FROM milestones WHERE m_ref = ? AND initiative_id = ?",
                    (r, ini_id)).fetchone()
                if mrow is None:
                    raise ParseFailure(
                        f"log entry #{seq} references {r}, which the status "
                        "table has not defined — the log can only bear on "
                        "milestones the table declares")
                cur3 = conn.execute(
                    "INSERT OR IGNORE INTO links(src_type, src_id, dst_type, "
                    "dst_id, link_type, weight, provenance_id, ingested_at) "
                    "VALUES ('milestone_log', ?, 'milestone', ?, 'bears-on', 1.0, ?, ?)",
                    (log_row["id"], mrow["id"], prov_log, utcnow()))
                if cur3.rowcount:
                    results["links"] += 1

    return results


def initiative_for_m_ref_maybe(m_ref: str) -> bool:
    try:
        initiative_for_m_ref(m_ref)
        return True
    except ParseFailure:
        return False


# ─── source 1b: goal peg ─────────────────────────────────────────────────────

def parse_goal_peg(conn) -> int:
    """§3.4: 'Portfolio goal → initiatives (or meta peg + evidence)'. The goal
    text defines vm_sec_research; record the peg honestly in meta with a
    provenance pointer (meta is self-governance, exempt from the row-level rule)."""
    if not GOAL_PATH.exists():
        raise ParseFailure("progress/goal.md not found")
    sha = hashlib.sha256(GOAL_PATH.read_bytes()).hexdigest()
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('portfolio_goal_sha256', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (sha,))
    add_provenance(conn, "progress/goal.md", "milestones", sha,
                   "meta peg: portfolio goal statement (vm_sec_research's "
                   "defining contract)")
    return 0


# ─── source 2: knowledge ─────────────────────────────────────────────────────

FOOTER_ABSENT = re.compile(r"^No [`']?([\w-]+)[`'s]* entries", re.IGNORECASE)
KNOWLEDGE_ENTRY = re.compile(
    r"^- \[([^\]]+)\]\(([^)]+)\)\s+—\s+(.*?)\s+\(updated:\s*(\d{4}-\d{2}-\d{2})\)\s*$")


def parse_knowledge(conn, path: Path) -> dict:
    """One line per entry per the file's own documented format (§2.2 source 2):
    '- [title](file.md) — hook (updated: YYYY-MM-DD)'. Kind is parsed data (P4):
    unless the file's footer declares such entries exist, an entry is 'general'.
    A hook that asserts a currency state (clean/cleared/zero vulnerabilities)
    is verdict_class='currency_claim' — R2's join criterion. Its `updated:`
    date lands in claim_anchors."""
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    source_type = "knowledge"
    sha = hashlib.sha256(text.encode()).hexdigest()
    results = {"source": source_type, "entries": 0, "evidence": 0,
               "currency_claims": 0, "footer_flags": []}

    ini_id = initiative_id(conn, "vulnres_suite")

    declared_absent: set[str] = set()
    for line in text.splitlines():
        fm = FOOTER_ABSENT.match(line)
        if fm:
            declared_absent.add(fm.group(1).lower())
    results["footer_flags"] = sorted(declared_absent)

    entries = [e for e in (KNOWLEDGE_ENTRY.match(l) for l in text.splitlines()) if e]
    for title, file_ref, hook, updated in (e.groups() for e in entries):
        if title.startswith("TEMPLATE"):
            raise ParseFailure(f"template row leaked into the live index: {title!r}")
        if not (path.parent / file_ref).exists():
            raise ParseFailure(f"entry '{title}' links to missing file: {file_ref}")

    prov = add_provenance(
        conn, f"{rel}#entries", source_type, sha,
        "one row per index line; kind general/currency per P4 hook parse; the "
        f"file's footer declares these kinds absent: {results['footer_flags']}")
    for title, file_ref, hook, updated in (e.groups() for e in entries):
        verdict = "currency_claim" if CURRENCY_RE.search(hook) else "general"
        content_hash = hashlib.sha256(f"{title}|{hook}|{updated}".encode()).hexdigest()
        source_ref = f"{rel}#-[{title}]({file_ref})"
        # verdict_class/asserted_at are the parse PROJECTION of the (unchanged)
        # hook — a classification rule change is applied on reparse with its own
        # provenance row; the raw claim row is never deleted (§3.2).
        prov_upd = add_provenance(
            conn, f"{rel}#-[{title}]({file_ref})", source_type, sha,
            f"reparsed projection: verdict_class={verdict} (P4 hook rule), "
            f"claim anchored at {updated}")
        conn.execute(
            "INSERT INTO evidence(initiative_id, kind, verdict_class, content_hash, "
            "asserted_at, source_ref, provenance_id, ingested_at) "
            "VALUES (?, 'knowledge', ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(source_ref, content_hash) DO UPDATE SET "
            "verdict_class = excluded.verdict_class, "
            "asserted_at = excluded.asserted_at, "
            "provenance_id = excluded.provenance_id, "
            "ingested_at = excluded.ingested_at",
            (ini_id, verdict, content_hash, updated, source_ref, prov_upd,
             utcnow()))
        results["entries"] += 1
        row = conn.execute(
            "SELECT id FROM evidence WHERE source_ref = ? AND content_hash = ?",
            (source_ref, content_hash)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO claim_anchors(evidence_id, asserted_at) "
            "VALUES (?, ?)",
            (row["id"], updated))
        if verdict == "currency_claim":
            results["currency_claims"] += 1
    results["evidence"] = conn.execute(
        "SELECT count(*) FROM evidence WHERE kind = 'knowledge'").fetchone()[0]

    # P4 cross-check note: an entry classified into a kind the footer declares
    # absent would mean the indexer and the parser disagree. The classification
    # rule above never maps an entry to 'environment'/'target-status' without a
    # footer declaration; the flags are recorded for the clock cross-check that
    # seeds staleness state (phase 2) — a declared-absent kind gaining a listed
    # entry is a future parse failure, never a silent reconciliation.
    return results


# ─── source 3: sweep reports ────────────────────────────────────────────────

def parse_sweeps(conn) -> dict:
    """Sweep ledger (append, never rewrite — the ledger says so itself). Kind
    is parsed data from the Environment bullet ('none' ⇒ static ⇒ 'recon')."""
    text = SWEEPS_PATH.read_text(encoding="utf-8")
    rel = SWEEPS_PATH.relative_to(ROOT)
    sha = hashlib.sha256(text.encode()).hexdigest()
    results = {"sweeps": 0, "sweep_evidence": 0}
    ini_id = initiative_id(conn, "vulnres_suite")

    sections = sect(text, r"^##\s+(\d{4}-\d{2}-\d{2}-\d{3}-.+?)\s*$")
    if not sections:
        raise ParseFailure("sweep INDEX has no '## <date>-<nnn>-<name>' sections")

    for sweep_id, lines in sections.items():
        bl = bullets(lines)
        env = bl.get("environment(s)", "").lower()
        kind = "recon" if "none" in env else "environment_run"
        body = "\n".join(lines[1:]).strip()
        started_at = sweep_id[:10]
        findings_line = bl.get("new findings", "")

        prov = add_provenance(
            conn, f"{rel}#{sweep_id}", "sweep_reports", sha,
            f"sweep ledger row; kind={kind} from the Environment bullet "
            f"({env!r}); never rewrites history per the ledger's own header")
        conn.execute(
            "INSERT INTO sweeps(initiative_id, sweep_id, kind, report_dir, "
            "started_at, outcome, agents_invoked, provenance_id, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(sweep_id) DO NOTHING",
            (ini_id, sweep_id, kind, f"vuln_res/sweep-reports/{sweep_id}/",
             started_at, findings_line, json.dumps(bl.get("agents run", "")),
             prov, utcnow()))
        results["sweeps"] += 1

        content_hash = hashlib.sha256(f"sweep|{sweep_id}|{body}".encode()).hexdigest()
        conn.execute(
            "INSERT INTO evidence(initiative_id, kind, verdict_class, content_hash, "
            "asserted_at, source_ref, provenance_id, ingested_at) "
            "VALUES (?, 'sweep_summary', ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(source_ref, content_hash) DO NOTHING",
            (ini_id, kind, content_hash, started_at, f"{rel}#{sweep_id}",
             prov, utcnow()))
        results["sweep_evidence"] += 1

    return results


def parse_findings(conn) -> dict:
    """Cross-sweep findings index (authority medium-high: findings with
    committed evidence outrank prose claims). Score and status are kept
    verbatim; CAST(score AS INTEGER) drives the R2 join. The index's own
    footer declares 'no fuzzer-confirmed findings yet' — recorded, so an
    exploit row appearing here without an exploits-index entry would be a
    parse failure on a later run."""
    text = FINDINGS_PATH.read_text(encoding="utf-8")
    rel = FINDINGS_PATH.relative_to(ROOT)
    sha = hashlib.sha256(text.encode()).hexdigest()
    results = {"findings": 0, "finding_evidence": 0}
    ini_id = initiative_id(conn, "vulnres_suite")

    never_fuzzed = re.search(
        r"No fuzzer-confirmed or exploit-dev findings yet", text)
    rows = [m for m in (FINDING_ROW.match(l) for l in text.splitlines()) if m]
    if not rows and not never_fuzzed:
        raise ParseFailure(
            "findings-index table has no rows and no 'none yet' declaration — "
            "an index this suite guarantees to be apppendable cannot be empty "
            "without its own footer saying so")

    prov = add_provenance(
        conn, f"{rel}#table", "sweep_reports", sha,
        "findings verbatim from the cross-sweep index; fuzzer-confirmed absence "
        f"declared by the index footer itself: {bool(never_fuzzed)}")
    for slug, path_ref, score, status, _sweep_text, sweep_link in \
            (m.groups() for m in rows):
        # sweep_label from the row's own Sweep-column link target
        sweep_dir = str(Path(sweep_link).parent)
        sweep_label = re.sub(r"^\./|/$", "", sweep_dir) or sweep_link
        sweep_row = conn.execute(
            "SELECT id, started_at FROM sweeps WHERE sweep_id = ?",
            (sweep_label,)).fetchone()
        if sweep_row is None:
            raise ParseFailure(
                f"finding '{slug}' references sweep {sweep_label!r}, "
                "which the sweep ledger has not defined — findings resolve to "
                "sweep rows the ledger declares, never to loose labels")

        finding_ref = f"{rel}#{slug}"
        content_hash = hashlib.sha256(f"{slug}|{score}|{status}".encode()).hexdigest()
        conn.execute(
            "INSERT INTO findings(sweep_id, sweep_label, finding_ref, title, score, "
            "disposition, provenance_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(finding_ref) DO NOTHING",
            (sweep_row["id"], sweep_label, finding_ref, slug,
             score, status, prov, utcnow()))
        results["findings"] += 1

        fprov = add_provenance(
            conn, finding_ref, "sweep_reports", sha,
            f"finding evidence; sweep dated {sweep_row['started_at']}")
        conn.execute(
            "INSERT INTO evidence(initiative_id, kind, verdict_class, content_hash, "
            "asserted_at, source_ref, provenance_id, ingested_at) "
            "VALUES (?, 'finding', ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(source_ref, content_hash) DO NOTHING",
            (ini_id, score, content_hash, sweep_row["started_at"],
             finding_ref, fprov, utcnow()))
        results["finding_evidence"] += 1

    return results


def parse_exploits(conn) -> dict:
    """Exploit-PoC index: only findings that reached a working engineered PoC.
    Zero rows is honest ('(none yet)' is declared by the file itself)."""
    text = EXPLOITS_PATH.read_text(encoding="utf-8")
    rel = EXPLOITS_PATH.relative_to(ROOT)
    sha = hashlib.sha256(text.encode()).hexdigest()
    results = {"exploits": 0}

    rows = [l for l in text.splitlines()
            if l.startswith("|") and "`" in l and "---" not in l
            and not l.startswith("| Exploit")
            and "(none yet)" not in l]
    prov = add_provenance(
        conn, f"{rel}#table", "sweep_reports", sha,
        f"exploit-PoC index rows; declared '(none yet)' today: {len(rows) == 0}")
    for line in rows:
        cells = [c.strip() for c in line.strip("|").split("|")]
        name = cells[0].strip("`[]()")
        frow = conn.execute(
            "SELECT id FROM findings WHERE finding_ref = ?",
            (f"{FINDINGS_PATH.relative_to(ROOT)}#{name}",)).fetchone()
        outcome = "our_code"          # every PoC targets bputil-eval per that index's scope line
        conn.execute(
            "INSERT INTO exploits(finding_id, outcome_class, artifact_ref, "
            "provenance_id, ingested_at) VALUES (?, ?, ?, ?, ?)",
            (frow["id"] if frow else None, outcome,
             f"{rel}#{name}", prov, utcnow()))
        results["exploits"] += 1
    return results


# ─── source 4: environments (read-only mirror, forever) ─────────────────────

def parse_environments(conn) -> dict:
    """Registry rows are ingested read-only with their OWN documented fields
    (environments/SCHEMA.md, verbatim). 'No environments registered yet' is the
    honest zero that blocks every execute-phase claim (§4.2's state fact)."""
    if not ENVIRONMENTS_PATH.exists():
        raise ParseFailure("environments INDEX not found")
    text = ENVIRONMENTS_PATH.read_text(encoding="utf-8")
    rel = ENVIRONMENTS_PATH.relative_to(ROOT)
    sha = hashlib.sha256(text.encode()).hexdigest()
    results = {"environments": 0}

    rows = [m for m in (ENV_ROW.match(l) for l in text.splitlines()) if m]
    declared_empty = "No environments registered yet" in text
    if not rows and not declared_empty:
        raise ParseFailure(
            "environments INDEX has neither entries nor its 'none yet' declaration")

    entries: list[dict] = []
    for env_id, file_ref, fields, updated in (m.groups() for m in rows):
        registry_md = ENVIRONMENTS_PATH.parent / file_ref
        if not registry_md.exists():
            raise ParseFailure(
                f"environment '{env_id}' linked but its profile file is missing: {file_ref}")
        entries.append(parse_environment_profile(env_id, registry_md, updated))

    prov = add_provenance(
        conn, f"{rel}#registry", "environments_registry", sha,
        "read-only mirror of the environments registry (its SCHEMA.md fields); "
        "zero rows is the fact that blocks the execute phase until the user "
        "approves a first environment")
    for e in entries:
        conn.execute(
            "INSERT INTO environments(env_id, provider, lifecycle, status, "
            "created_at, created_by, approved_for, approved_by, network, "
            "resource_caps, provenance_id, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(env_id) DO NOTHING",
            (e["id"], e["provider"], e["lifecycle"], e["status"], e["created_at"],
             e["created_by"], e["approved_for"], e["approved_by"], e["network"],
             e["resource_caps"], prov, utcnow()))
        results["environments"] += 1
    return results


def parse_environment_profile(env_id: str, md: Path, updated: str) -> dict:
    text = md.read_text(encoding="utf-8")
    fields = {}
    fm = re.search(r"^---\n(.*?)^---", text, re.DOTALL | re.MULTILINE)
    for line in (fm.group(1).splitlines() if fm else []):
        km = re.match(r"^(\w+):\s*(.*)$", line.strip())
        if km:
            fields[km.group(1)] = km.group(2).strip().strip('"[]')
    return {
        "id": env_id or fields.get("id", ""),
        "provider": fields.get("provider", "unknown"),
        "lifecycle": fields.get("lifecycle", "unknown"),
        "status": fields.get("status", "unknown"),
        "created_at": fields.get("created_at") or updated,
        "created_by": fields.get("created_by", ""),
        "approved_for": fields.get("approved_for", ""),
        "approved_by": fields.get("approved_by", ""),
        "network": fields.get("network", "unknown"),
        "resource_caps": fields.get("resource_caps", ""),
    }


# ─── cadence reports (§3.4 map row; source = the reporting skill's own ledger)

def parse_cadence_reports(conn) -> dict:
    text_total = 0
    results = {"cadence_reports": 0, "files": 0}
    ini_id = initiative_id(conn, "vulnres_suite")
    prov = add_provenance(
        conn, "reports/{daily,weekly,monthly}/INDEX.md", "sweep_reports", None,
        "cadence report ledgers; zero rows = no vulnres-reporting rollup yet")
    for path, cadence in CADENCE_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        sha = hashlib.sha256(text.encode()).hexdigest()
        text_total += len(text)
        rel = path.relative_to(ROOT)
        entries = 0
        for line in text.splitlines():
            m = INDEX_ROW.match(line)
            if not m:
                continue
            title, file_ref, hook = m.groups()
            cr_sha = hashlib.sha256(f"{cadence}|{title}|{hook}".encode()).hexdigest()
            conn.execute(
                "INSERT INTO cadence_reports(initiative_id, cadence, path, "
                "created_at, provenance_id, ingested_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(path, created_at) DO NOTHING",
                (ini_id, cadence, f"{rel}#-{title}({file_ref})",
                 title if re.match(r"^\d{4}-\d{2}-\d{2}$", title) else utcnow(),
                 prov, utcnow()))
            entries += 1
        results["cadence_reports"] += entries
        results["files"] += 1
    # OnConflict dedupe uses (path, created_at) — backed by the UNIQUE index
    # cadence_reports_path created in migration 0003.
    return results


# ─── source 5: project lifecycle ────────────────────────────────────────────

# owner_gate classification (phase 4): verbatim phrase markers in each
# project's own PROPOSAL.md, checked in this priority order since a document
# can legitimately mention both ("enrolled" wins for project 3 even though
# its drift-watch false-positive-risk section also says "1TR" once, about a
# legitimate 1TR change IT detects — not a gate ON project 3 itself).
#   contains "enrolled" (case-insensitive)  -> real fleet hardware required
#   contains "1TR"                          -> real 1TR owner round trip required
#   neither                                 -> software-only; ordinary user
#                                               approval to begin is the only gate
# Verified against the real text at commit time: project 1 has zero matches
# for either marker, project 2 has "1TR" (x2) and zero "enrolled", project 3
# has "enrolled" (x8) and one incidental "1TR" mention (§3.5 item 19).
OWNER_GATE_MARKERS = (
    (re.compile(r"enrolled", re.IGNORECASE), "user_gated_fleet_hardware"),
    (re.compile(r"1TR"), "user_gated_plus_1tr"),
)


def classify_owner_gate(proposal_text: str) -> str:
    for pattern, gate in OWNER_GATE_MARKERS:
        if pattern.search(proposal_text):
            return gate
    return "user_gated"


def parse_project_lifecycle(conn) -> dict:
    """Projects 1–3: a phase-1 status file may not exist yet; absence means
    phase = pre-build, recorded as inference-with-provenance, never as fact
    (§2.2 source 5). The parser asserts the PROPOSAL each initiative cites is
    really there and parses 'not-yet-executed' markers honestly. Phase 4 adds
    content-aware owner_gate classification (§3.5 item 19): the seed-time
    blanket 'user_gated' for every project kind couldn't distinguish a
    software-only project from one that structurally needs 1TR or enrolled
    fleet hardware to make real progress — exactly the distinction a brief's
    required_gate field exists to report honestly."""
    results = {"projects_checked": 3, "status_files": 0}
    for slug in ("project1_fuzz", "project2_mutation", "project3_drift"):
        row = conn.execute(
            "SELECT id, proposal_ref, status_file_ref FROM initiatives WHERE slug = ?",
            (slug,)).fetchone()
        if row is None:
            raise ParseFailure(f"contract initiative missing: {slug}")
        proposal = ROOT / row["proposal_ref"]
        if not proposal.exists():
            raise ParseFailure(
                f"{slug}'s proposal_ref points at a missing file: {row['proposal_ref']}")
        proposal_text = proposal.read_text(encoding="utf-8")
        phase1_ref = re.search(
            r"[Pp]hase\s*1[^\n]{0,120}", proposal_text)   # context, verbatim quote kept
        gate = classify_owner_gate(proposal_text)
        marker = next((p.pattern for p, g in OWNER_GATE_MARKERS if g == gate), None)
        conn.execute(
            "UPDATE initiatives SET owner_gate = ? WHERE id = ?", (gate, row["id"]))
        # initiatives carries one provenance_id for the whole row (the seed
        # source); owner_gate's own basis is a reparsed projection recorded
        # the same way phase1_plan_note is below — in meta, keyed per slug,
        # never by clobbering the row's seed attribution.
        conn.execute(
            "INSERT INTO meta(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (f"owner_gate_basis:{slug}",
             f"owner_gate={gate}; matched marker={marker!r}; source="
             f"{row['proposal_ref']} (§3.5 item 19)"))
        results[f"owner_gate:{slug}"] = gate
        if row["status_file_ref"] is None:
            still = add_provenance(
                conn, row["proposal_ref"], "project_lifecycle",
                hashlib.sha256(proposal_text.encode()).hexdigest(),
                "phase check: no phase-1 status file exists for this project yet "
                "— status 'pre-build' is an inference from this file's plan, not "
                "a fact from a status file (status_file_ref stays NULL)")
            if phase1_ref:
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (f"phase1_plan_note:{slug}", phase1_ref.group(0)[:120]))
        else:
            results["status_files"] += 1
    return results


# ─── source 6: git history (file-level events) ──────────────────────────────

def parse_git_events(conn) -> dict:
    """`git log --since=… --name-only` (read-only subprocess) → file-level
    event stream for implication analysis. Window constant GIT_SINCE covers the
    earliest assertion date any parsed claim itself makes."""
    try:
        raw = subprocess.run(
            ["git", "log", f"--since={GIT_SINCE}", "--name-only",
             "--pretty=format:%H%x00%ad%x00%s", "--date=iso-strict", "--"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError as exc:
        raise ParseFailure(f"git log failed: {exc.stderr.strip()}")
    if not raw.strip():
        raise ParseFailure(f"git log returned nothing since {GIT_SINCE}")

    results = {"events": 0, "commit_evidence": 0}
    prov = add_provenance(
        conn, f"git log --since={GIT_SINCE} --name-only", "git_history", None,
        "file-level event stream; read-only; the implication rules in "
        "db/queries/ decide what these events affect")
    commits = []
    current = None
    for line in raw.strip().split("\n"):
        if "\x00" in line:
            sha, date, subject = line.split("\x00", 2)
            current = {"sha": sha.strip(), "date": date.strip(),
                       "subject": subject.strip(), "paths": []}
            commits.append(current)
        elif current is not None and line.strip():
            current["paths"].append(line.strip())

    for c in commits:
        occurred = (c["date"].replace("+00:00", "Z") if c["date"].endswith("+00:00")
                    else c["date"])
        conn.execute(
            "INSERT OR IGNORE INTO events(kind, occurred_at, ref, paths, detail, "
            "provenance_id, ingested_at) VALUES ('commit', ?, ?, ?, ?, ?, ?)",
            (occurred, c["sha"], json.dumps(c["paths"]), c["subject"],
             prov, utcnow()))
        results["events"] += 1

        ev_hash = hashlib.sha256(f"git|{c['sha']}".encode()).hexdigest()
        conn.execute(
            "INSERT OR IGNORE INTO evidence(initiative_id, kind, verdict_class, "
            "content_hash, asserted_at, source_ref, provenance_id, ingested_at) "
            "VALUES (?, 'commit_event', 'commit', ?, ?, ?, ?, ?)",
            (initiative_id(conn, "vulnres_suite"), ev_hash,
             c["date"][:10], f"git:{c['sha']}", prov, utcnow()))
        results["commit_evidence"] += 1
    return results


# ─── source 7: capability registry ──────────────────────────────────────────

GATE_PHRASES = ("stop and ask", "ask the user", "requires the user", "user approval",
                "explicit user approval")


def parse_capabilities(conn) -> dict:
    """Every .claude/agents/vulnres-*.md and .claude/skills/vulnres-*/SKILL.md
    becomes a capability row: trigger_contract = the file's own description
    (verbatim); approval_class parsed from the file's own body by the
    documented-phrase rule v1 — a body containing any gate phrase classifies
    user_gated; otherwise autonomous. The matched phrases are recorded in
    provenance so the classification is reviewable, never asserted silently."""
    results = {"capabilities": 0}
    ini_id = initiative_id(conn, "vulnres_suite")
    specs: list[tuple[str, str, str, Path]] = []
    for p in sorted(AGENTS_GLOB.parent.glob("vulnres-*.md")):
        specs.append((p.stem, "agent", p, p))
    for p in sorted(SKILLS_GLOB.parent.glob("vulnres-*/SKILL.md")):
        specs.append((p.parent.name, "skill", p, p))
    if not specs:
        raise ParseFailure("no vulnres-* agent or skill definitions found")

    for name, kind, path, _ in specs:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        sha = hashlib.sha256(text.encode()).hexdigest()
        fm = re.search(r"^---\n(.*?)^---", text, re.DOTALL | re.MULTILINE)
        desc = ""
        fm_name = name
        if fm:
            dm = re.search(r"^name:\s*(.+)$", fm.group(1), re.MULTILINE)
            dm2 = re.search(r"^description:\s*(.+)$", fm.group(1), re.MULTILINE)
            if dm:
                fm_name = dm.group(1).strip()
            desc = dm2.group(1).strip() if dm2 else ""
        hits = [ph for ph in GATE_PHRASES if ph in text.lower()]
        approval = "user_gated" if hits else "autonomous"
        gate_note = ", ".join(hits) if hits else "none matched (no execution authority asserted)"
        prov = add_provenance(
            conn, str(rel), "capability_registry", sha,
            f"approval_class={approval} by documented-phrase rule v1; gate "
            f"phrases matched: {gate_note}")
        contract = desc[:400] if desc else f"{kind} definition at {rel}"
        conn.execute(
            "INSERT INTO capabilities(name, agent_or_skill, kind, suite, "
            "approval_class, trigger_contract, provenance_id, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(agent_or_skill) DO UPDATE SET "
            "name = excluded.name, trigger_contract = excluded.trigger_contract, "
            "approval_class = excluded.approval_class, "
            "provenance_id = excluded.provenance_id, ingested_at = excluded.ingested_at",
            (fm_name, str(rel), kind, ini_id, approval, contract, prov, utcnow()))
        results["capabilities"] += 1
    return results



# ─── staleness clocks (seeded from parsed data; states are facts) ───────────

# The seed rule set v1: one row per decaying surface. Each entry:
#   surface            unique id
#   knowledge root     evidence source_ref fragment that anchors verification
#   invalidates_on     path prefixes; an event under one invalidates (R1)
#   state              'never' when the surface has no verification event at all
CLOCK_SEEDS = [
    # knowledge currency claims — live until a postdating event touches their scope
    ("knowledge:build-test-clean", "build-test-clippy-fmt-clean", "vulnres_suite",
     ["src/", "tests/", "scripts/", "Cargo.toml", "Cargo.lock", "vuln_res/knowledge/"],
     "live", "2026-11-10",
     "commit-after-assertion invalidates: the claim is currency-bound to its "
     "updated: date and the files its hook describes"),
    ("knowledge:cargo-audit-clean", "cargo-audit-cargo-deny-not-installed",
     "vulnres_suite", ["Cargo.lock", "Cargo.toml", "vuln_res/knowledge/"],
     "live", "2026-11-10",
     "a Cargo.lock change lands => every staleness claim about dependency "
     "audit is suspect (§4.1's canonical example, as data)"),
    ("knowledge:owner-credentials-cleared", "owner-credentials-field-reviewed-cleared",
     "vulnres_suite", ["src/plan.rs", "src/", "vuln_res/knowledge/"],
     "live", "2026-11-10",
     "code change to the subject invalidates the review's currency"),
    ("knowledge:command-enum-note", "command-enum-name-collision-tool-note",
     "vulnres_suite", ["src/main.rs", "src/", "vuln_res/knowledge/"],
     "live", "2026-11-10",
     "code change to the subject invalidates the note's currency"),
    # never-clock: fuzz targets — declared by the knowledge INDEX footer itself
    ("fuzz-targets:first-built", "", "project1_fuzz",
     ["vuln_res/plans/02-fuzzing-harness-agent.md", "src/fuzz/"],
     "never", None,
     "never fuzzed: the INDEX footer declares no target-status entries and "
     "plans/02 has not been executed; this NULL is the fact phase acceptance "
     "tests lean on"),
    # never-clock: environments — the registry itself declares zero rows
    ("environments:first-registered", "", "vulnres_suite",
     ["vuln_res/knowledge/environments/"], "never", None,
     "no environment registered => every execute-phase claim is structurally "
     "blocked (§4.2's state fact, not a complaint)"),
    # never-clock: fleet enrollment — project 3 is pre-build
    ("fleet-enrollments:first-list", "", "project3_drift",
     ["projects/03-fleet-drift-watch/"], "never", None,
     "no enrollment list exists yet; a patient adversary's fleet-drift "
     "invisibility (patient-fleet.md's critique is phase 5) presumes this"),
    # live-clock: agent registry gap — the worked-around harness constraint
    ("vuln_res:agent-registry-fallback", "agent-registry-not-live-this-session",
     "vulnres_suite", [".claude/agents/", "vuln_res/plans/06-orchestration-and-scheduling.md"],
     "live", "2026-11-10",
     "root-caused with a working fallback per the finding and plans/06; a "
     "change to either invalidates the workaround's currency"),
]


def seed_clocks(conn) -> dict:
    """Insert clock rows from CLOCK_SEEDS; verification anchors resolve to the
    matching knowledge/finding evidence rows (source_ref fragment match).
    Phase 4 (§3.5 item 20): the anchor resolves to the MOST RECENTLY asserted
    matching claim (ORDER BY asserted_at DESC), not whichever happened to be
    ingested first — knowledge/INDEX.md's own
    build-test-clippy-fmt-clean-2026-11-10/-2026-11-11 pair is a real case of
    two currency claims for the same surface; anchoring to the newer one is
    the content-aware, not merely file-order-dependent, choice."""
    results = {"clocks": 0, "live": 0, "never": 0}
    for surface, anchor, slug, invalidates, state, verified, policy in CLOCK_SEEDS:
        ini = initiative_id(conn, slug)
        ev_id = None
        verified_at = verified
        if anchor:
            row = conn.execute(
                "SELECT id, asserted_at FROM evidence WHERE source_ref LIKE ? "
                "ORDER BY asserted_at DESC LIMIT 1",
                (f"%{anchor}%",)).fetchone()
            if row is None:
                raise ParseFailure(
                    f"clock {surface!r} anchors to evidence {anchor!r}, "
                    "which no parsed evidence row provides — a clock without "
                    "an anchor is a fabricated claim")
            ev_id, verified_at = row["id"], row["asserted_at"]
        prov = add_provenance(
            conn, f"parsers:CLOCK_SEEDS[{surface}]", "supervisor_rule", None,
            "clock seed: reviewed rule v1 row (CLOCK_SEEDS in tools/parsers.py "
            "diffs in git); state at seed is derived from parsed claims only")
        cur = conn.execute(
            "INSERT INTO staleness_clocks(initiative_id, surface, "
            "last_verified_at, last_verified_by, invalidates_on, policy, state, "
            "provenance_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(surface) DO NOTHING",
            (ini, surface, verified_at, ev_id, json.dumps(invalidates), policy,
             state, prov, utcnow()))
        if cur.rowcount:
            results["clocks"] += 1
            results[state] += 1
    # already-seeded: recount states honestly
    for st in ("live", "never"):
        results[st] = conn.execute(
            "SELECT count(*) FROM staleness_clocks WHERE state = ?",
            (st,)).fetchone()[0]
    results["clocks"] = conn.execute(
        "SELECT count(*) FROM staleness_clocks").fetchone()[0]
    return results


# ─── the implication run: reviewed SQL only ─────────────────────────────────

QUERIES_DIR = ROOT / "projects/supervisor-agent/db/queries"


def run_implication(conn) -> dict:
    """Executes the reviewed rule files in filename order. Rules are SQL files
    under db/queries/ — brief-facing analysis never inlines SQL, and implication
    is the same discipline applied to state changes."""
    results = {"rules_run": [], "new_invalidations": 0, "new_contradictions": 0}
    for q in sorted(QUERIES_DIR.glob("r*.sql")):
        before_i = conn.execute("SELECT count(*) FROM clock_invalidation_events").fetchone()[0]
        before_c = conn.execute("SELECT count(*) FROM contradictions").fetchone()[0]
        conn.executescript(q.read_text())
        results["rules_run"].append(q.name)
        results["new_invalidations"] += \
            conn.execute("SELECT count(*) FROM clock_invalidation_events").fetchone()[0] - before_i
        results["new_contradictions"] += \
            conn.execute("SELECT count(*) FROM contradictions").fetchone()[0] - before_c
    return results
