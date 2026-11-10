#!/usr/bin/env python3
"""Supervisor agent parsers — BUILD-SPEC §2, ontology/SCHEMA.md parser contracts.

Phase-1 scope: sources `milestones` (progress/goal.md + progress/milestones.md)
and `knowledge` (vuln_res/knowledge/INDEX.md), plus contract-initiative seeding.

Rules implemented (each traces to ontology/SCHEMA.md):
  P1 parse failures are first-class (parse_failures row + authority 0 for the run)
  P2 newer dated entries outrank older ones and nothing else does
  P3 milestone refs are append-only; renumbering/insertion is a parse failure
  P4 knowledge entry kind is parsed data (footer-declared, not guessed)
"""

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supervisor import ROOT, utcnow, connect  # noqa: E402

MILESTONES_PATH = ROOT / "progress/milestones.md"
GOAL_PATH = ROOT / "progress/goal.md"
KNOWLEDGE_PATH = ROOT / "vuln_res/knowledge/INDEX.md"

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


class ParseFailure(Exception):
    """Raised by any parser that cannot honestly proceed; converted into a
    parse_failures row by the caller (the failure is data, never a skip)."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


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


def initiative_id(conn, slug: str) -> int:
    row = conn.execute("SELECT id FROM initiatives WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ParseFailure(f"initiative slug not found: {slug}")
    return row["id"]


def initiative_for_m_ref(m_ref: str) -> str:
    n = int(m_ref[1:])
    for slug, (lo, hi) in MILESTONE_ANCHORS.items():
        if lo <= n <= hi:
            return slug
    raise ParseFailure(
        f"{m_ref} outside every registered anchor range (§3.5 item 7: register "
        "the range in ontology/sources.yaml before binding rows)")


# ─── source 1: milestones ────────────────────────────────────────────────────

def split_sections(text: str) -> dict[str, list[str]]:
    """Split the file by '## ' headings into line-lists."""
    sections: dict[str, list[str]] = {}
    section = None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            sections.setdefault(section, [])
        if section is not None:
            sections[section].append(line)
    return sections


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

    sections = split_sections(text)
    if "Status" not in sections or "Log" not in sections:
        raise ParseFailure("missing '## Status' and/or '## Log' sections")

    # P3 — table refs must be the registered anchor range, ascending, contiguous.
    seen_refs: list[str] = []
    for line in sections["Status"]:
        m = TABLE_ROW.match(line)
        if m and not line.startswith("| #") and "---" not in line and "|" in line[1:]:
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
        if not m or line.startswith("| #") or "---" in line:
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

    # Log section: '### DATE [flag] — heading' + one body per entry.
    prov_log = add_provenance(
        conn, f"{rel}#log", source_type, sha,
        "dated log entries; 'Next up' paragraphs parsed verbatim as "
        "decision-engine input, never treated as prose")
    log_lines = sections["Log"]
    entries: list[dict] = []
    current: dict | None = None
    seen_heading_dates = False
    for line in log_lines:
        hm = re.match(r"^###\s+(.+)$", line)
        if hm:
            seen_heading_dates = True
            if current:
                entries.append(current)
            current = {"heading": hm.group(1).strip(), "body": []}
        elif current is not None:
            current["body"].append(line)
    if current:
        entries.append(current)

    if self_test and not entries:
        # A mangled fixture with no parseable log entries is itself a failure.
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
        unknown = [r for r in refs
                   if not any(int(r[1:]) <= hi and int(r[1:]) >= lo
                              for lo, hi in MILESTONE_ANCHORS.values())]
        if unknown:
            raise ParseFailure(
                f"log entry #{seq} touches unregistered milestone refs "
                f"{unknown} (§3.5 item 7)")

        next_up = None
        nm = re.search(
            r"\*\*Next up:\*\*\s*(.*?)(?:\n\n|\Z)", body, re.DOTALL)
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
                "source_ref, provenance_id, ingested_at) VALUES (?, 'milestone', ?, ?, ?, ?, ?) "
                "ON CONFLICT(source_ref, content_hash) DO NOTHING",
                (ini_id, "dated_log_entry", content_hash,
                 f"{rel}#{seq}-{occurred_at}", ev_prov, utcnow()))
            if cur2.rowcount:
                results["evidence"] += 1
                ev_id = cur2.lastrowid

                for r in refs:
                    mrow = conn.execute(
                        "SELECT id FROM milestones WHERE m_ref = ? AND initiative_id = ?",
                        (r, ini_id)).fetchone()
                    if mrow is None:
                        raise ParseFailure(
                            f"log entry #{seq} references {r}, which the status "
                            "table has not defined — the log can only bear on "
                            "milestones the table declares")
                    conn.execute(
                        "INSERT OR IGNORE INTO links(src_type, src_id, dst_type, "
                        "dst_id, link_type, weight, provenance_id, ingested_at) "
                        "VALUES ('milestone_log', ?, 'milestone', ?, 'bears-on', 1.0, ?, ?)",
                        (conn.execute("SELECT id FROM milestone_log WHERE entry_key = ?",
                                      (entry_key,)).fetchone()[0],
                         mrow["id"], prov_log, utcnow()))
                    results["links"] += 1

    return results


# ─── source 2: knowledge ─────────────────────────────────────────────────────

FOOTER_ABSENT = re.compile(r"^No [`']?([\w-]+)[`'s]* entries", re.IGNORECASE)


def parse_knowledge(conn, path: Path) -> dict:
    """One line per entry per the file's own documented format (§2.2 source 2):
    '- [title](file.md) — hook (updated: YYYY-MM-DD)'. Kind is parsed data (P4):
    unless the file's footer declares such entries exist, an entry is 'general'.
    Footer entries claiming presence absent from the list are parse failures."""
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    source_type = "knowledge"
    sha = hashlib.sha256(text.encode()).hexdigest()
    results = {"source": source_type, "entries": 0, "evidence": 0,
               "footer_flags": []}

    ini_id = initiative_id(conn, "vulnres_suite")

    # footer-first: which kinds does the file itself declare ABSENT/declared?
    declared_absent: set[str] = set()
    for line in text.splitlines():
        fm = FOOTER_ABSENT.match(line)
        if fm:
            declared_absent.add(fm.group(1).lower())
    results["footer_flags"] = sorted(declared_absent)

    entries: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        em = ENTRY_LINK.match(line)
        if em:
            entries.append(em.groups())

    # P4 sanity: an INDEX with zero listed entries but a footer declaring none
    # is consistent; a footer declaring absent kinds must never coincide with
    # entries classified into those kinds (classification below), and an entry
    # whose tile-file is unresolvable is a failure, never a silent skip.
    for title, file_ref, hook, updated in entries:
        if title.startswith("TEMPLATE"):
            raise ParseFailure(f"template row leaked into the live index: {title!r}")
        target = path.parent / file_ref
        if not target.exists():
            raise ParseFailure(
                f"entry '{title}' links to missing file: {file_ref}")

    prov = add_provenance(
        conn, f"{rel}#entries", source_type, sha,
        "one row per index line; kind=general because the file's own footer "
        "declares no environment/target-status entries exist "
        f"(footer flags: {results['footer_flags']})")
    for title, file_ref, hook, updated in entries:
        entry_abs_ref = path.parent / file_ref
        entry_sha = hashlib.sha256(entry_abs_ref.read_bytes()).hexdigest()
        content_hash = hashlib.sha256(
            f"{title}|{hook}|{updated}".encode()).hexdigest()
        conn.execute(
            "INSERT INTO evidence(initiative_id, kind, verdict_class, content_hash, "
            "source_ref, provenance_id, ingested_at) "
            "VALUES (?, 'knowledge', 'general', ?, ?, ?, ?) "
            "ON CONFLICT(source_ref, content_hash) DO NOTHING",
            (ini_id, content_hash, f"{rel}#-[{title}]({file_ref})", prov, utcnow()))
        results["entries"] += 1
    results["evidence"] = conn.execute(
        "SELECT count(*) FROM evidence WHERE kind = 'knowledge'").fetchone()[0]

    # P4: an entry classified into a kind the footer declared absent means the
    # indexer and the parser disagree — surface it, never reconcile silently.
    # (Classification above defaults entries to 'general'; the only way an entry
    # becomes 'environment'/'target-status' is a footer-declared kind match,
    # parsed from the footer, never inferred.)
    return results


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
