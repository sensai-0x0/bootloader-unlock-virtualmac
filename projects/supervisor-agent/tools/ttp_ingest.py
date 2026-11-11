#!/usr/bin/env python3
"""Phase-5 TTP ingest — BUILD-SPEC §5.2, §8 phase 5.

Ingests a real MITRE ATT&CK Enterprise STIX 2.1 bundle (downloaded by a human
or an explicitly-approved session step; this module never fetches anything
itself) into attack_releases/tactics/techniques/technique_* and pins it in
`meta`. A separate pass ingests ttp/mappings.yaml into ttp_mappings, and
another seeds tp_profiles from ttp/profiles/*.md frontmatter-ish headers.

No network access, no subprocess — reads a local file path given on the
command line and writes only to the DB (same §7 invariant-1 scope as every
other tools/*.py module). The bundle itself is never committed to this repo
(§3.5 item: build-time input, not a tracked artifact) — only its URL + SHA-256
land in `meta`/`attack_releases`.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supervisor import BASE, utcnow, connect, checkpoint, add_provenance  # noqa: E402

TTP_DIR = BASE / "ttp"
MAPPINGS_PATH = TTP_DIR / "mappings.yaml"
PROFILES_DIR = TTP_DIR / "profiles"

PORTFOLIO_PLATFORMS = {"macOS", "Containers", "IaaS", "Linux"}

# 'PRE' is ATT&CK's own tag for pre-compromise/Resource-Development-stage
# techniques that apply BEFORE a specific victim platform is chosen — it is
# platform-general by MITRE's own design, never a mismatch (§3.5 item 24).
PLATFORM_AGNOSTIC_TAGS = {"PRE"}

# Surfaces that are this portfolio's OWN software/process pipeline, not an
# OS/infra-targeted surface — the platform filter (§3.3 item 5) was written
# for victim-OS-bound surfaces (Cargo.lock, a staleness clock, a capability
# that runs ON macOS/Linux/Containers/IaaS); the supervisor's own ingestion
# path and the vulnres-* autonomous-capability surface aren't OS-bound at
# all, so filtering them by MITRE's observed-usage platform tag would reject
# exactly the AI-enabled techniques BUILD-SPEC §5.2 names as first-class
# must-model items for this portfolio's own agent fleet (§3.5 item 24).
PLATFORM_FILTER_EXEMPT_SURFACES = {
    "supervisor-ingestion-path",
    "vulnres-autonomous-capabilities",
}


class TtpParseFailure(Exception):
    pass


def _attack_id(obj: dict) -> str | None:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id")
    return None


def ingest_release(conn, bundle_path: Path, tag: str, bundle_url: str,
                    released_at: str) -> dict:
    """Parses the STIX bundle at bundle_path; inserts attack_releases (if not
    already pinned at this sha) + tactics + techniques + technique_tactics/
    platforms/groups/campaigns/detcount/revisions. Re-running against the
    SAME sha is idempotent (INSERT OR IGNORE throughout); a DIFFERENT sha
    under the SAME tag is refused — re-pinning is a new tag, never a silent
    content swap under an existing one."""
    raw = bundle_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    objs = data["objects"]
    by_id = {o["id"]: o for o in objs}

    existing = conn.execute(
        "SELECT id, bundle_sha256 FROM attack_releases WHERE tag = ?", (tag,)
    ).fetchone()
    if existing and existing["bundle_sha256"] != sha:
        raise TtpParseFailure(
            f"tag {tag!r} already pinned with a different sha "
            f"({existing['bundle_sha256']}) — re-pin as a NEW tag, never a "
            "silent content swap (BUILD-SPEC §3.3 item 6 / A6)")

    prov = add_provenance(
        conn, bundle_url, "attack_stix_bundle", sha,
        f"ATT&CK {tag} ingested from a locally-downloaded, human/session- "
        "approved copy (this module performs no network access)")

    conn.execute(
        "INSERT INTO attack_releases(tag, released_at, bundle_url, "
        "bundle_sha256, is_pinned, ingested_at) VALUES (?, ?, ?, ?, 1, ?) "
        "ON CONFLICT(tag) DO NOTHING",
        (tag, released_at, bundle_url, sha, utcnow()))
    release_id = conn.execute(
        "SELECT id FROM attack_releases WHERE tag = ?", (tag,)).fetchone()["id"]
    # at most one pinned release (§3.1 comment) — demote any other
    conn.execute(
        "UPDATE attack_releases SET is_pinned = 0 WHERE tag != ?", (tag,))
    conn.execute(
        "UPDATE attack_releases SET is_pinned = 1 WHERE tag = ?", (tag,))

    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('attack_pin_tag', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (tag,))
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('attack_pin_url', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (bundle_url,))
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('attack_pin_sha256', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (sha,))

    results = {"tactics": 0, "techniques": 0, "technique_tactics": 0,
               "technique_platforms": 0, "technique_groups": 0,
               "technique_campaigns": 0, "technique_detcount": 0}

    tactic_short_to_id: dict[str, int] = {}
    for o in objs:
        if o["type"] != "x-mitre-tactic":
            continue
        aid = _attack_id(o)
        if not aid:
            continue
        conn.execute(
            "INSERT INTO tactics(attack_id, name, short_name) VALUES (?, ?, ?) "
            "ON CONFLICT(attack_id) DO NOTHING",
            (aid, o["name"], o["x_mitre_shortname"]))
        row = conn.execute(
            "SELECT id FROM tactics WHERE attack_id = ?", (aid,)).fetchone()
        tactic_short_to_id[o["x_mitre_shortname"]] = row["id"]
        results["tactics"] += 1

    technique_attack_id_to_id: dict[str, int] = {}
    technique_stix_to_attack_id: dict[str, str] = {}
    for o in objs:
        if o["type"] != "attack-pattern":
            continue
        aid = _attack_id(o)
        if not aid:
            continue
        is_sub = bool(o.get("x_mitre_is_subtechnique"))
        parent = aid.split(".")[0] if is_sub and "." in aid else None
        conn.execute(
            "INSERT INTO techniques(attack_id, name, is_subtechnique, "
            "parent_attack_id, description, revoked, deprecated, release_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(attack_id) DO NOTHING",
            (aid, o["name"], int(is_sub), parent, o.get("description"),
             int(bool(o.get("revoked"))), int(bool(o.get("x_mitre_deprecated"))),
             release_id))
        row = conn.execute(
            "SELECT id FROM techniques WHERE attack_id = ?", (aid,)).fetchone()
        technique_attack_id_to_id[aid] = row["id"]
        technique_stix_to_attack_id[o["id"]] = aid
        results["techniques"] += 1

        conn.execute(
            "INSERT INTO technique_revisions(technique_attack_id, release_id, "
            "version, revision_note) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(technique_attack_id, release_id) DO NOTHING",
            (aid, release_id, str(o.get("x_mitre_version", "")), None))

        for kcp in o.get("kill_chain_phases", []):
            tac_id = tactic_short_to_id.get(kcp.get("phase_name"))
            if tac_id is None:
                continue
            conn.execute(
                "INSERT INTO technique_tactics(technique_id, tactic_id) "
                "VALUES (?, ?) ON CONFLICT(technique_id, tactic_id) DO NOTHING",
                (row["id"], tac_id))
            results["technique_tactics"] += 1

        for plat in o.get("x_mitre_platforms", []):
            conn.execute(
                "INSERT INTO technique_platforms(technique_id, platform) "
                "VALUES (?, ?) ON CONFLICT(technique_id, platform) DO NOTHING",
                (row["id"], plat))
            results["technique_platforms"] += 1

    # relationships: groups/campaigns 'use' techniques; detection-strategies
    # 'detect' techniques (detcount = strategies + their bundled analytics)
    detstrat_analytic_refs: dict[str, int] = {
        o["id"]: len(o.get("x_mitre_analytic_refs", []))
        for o in objs if o["type"] == "x-mitre-detection-strategy"
    }
    detcount_acc: dict[str, list[int]] = {}  # technique attack_id -> [strategies, analytics]

    for o in objs:
        if o["type"] != "relationship":
            continue
        src = by_id.get(o.get("source_ref"))
        tgt = by_id.get(o.get("target_ref"))
        if src is None or tgt is None or tgt.get("type") != "attack-pattern":
            continue
        tgt_aid = technique_stix_to_attack_id.get(tgt["id"])
        if tgt_aid is None:
            continue
        tgt_id = technique_attack_id_to_id[tgt_aid]

        if o.get("relationship_type") == "uses" and src["type"] == "intrusion-set":
            g_aid = _attack_id(src)
            if g_aid:
                conn.execute(
                    "INSERT INTO technique_groups(technique_id, "
                    "group_attack_id, group_name, source_ref) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(technique_id, group_attack_id, source_ref) "
                    "DO NOTHING", (tgt_id, g_aid, src["name"], o["id"]))
                results["technique_groups"] += 1

        elif o.get("relationship_type") == "uses" and src["type"] == "campaign":
            c_aid = _attack_id(src)
            if c_aid:
                conn.execute(
                    "INSERT INTO technique_campaigns(technique_id, "
                    "campaign_attack_id, campaign_name, source_ref) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(technique_id, "
                    "campaign_attack_id) DO NOTHING",
                    (tgt_id, c_aid, src["name"], o["id"]))
                results["technique_campaigns"] += 1

        elif (o.get("relationship_type") == "detects"
              and src["type"] == "x-mitre-detection-strategy"):
            acc = detcount_acc.setdefault(tgt_aid, [0, 0])
            acc[0] += 1
            acc[1] += detstrat_analytic_refs.get(src["id"], 0)

    for aid, (strategies, analytics) in detcount_acc.items():
        conn.execute(
            "INSERT INTO technique_detcount(technique_id, release_id, "
            "det_strategies, analytics) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(technique_id, release_id) DO NOTHING",
            (technique_attack_id_to_id[aid], release_id, strategies, analytics))
        results["technique_detcount"] += 1

    conn.commit()
    checkpoint(conn)
    return results


# ─── mappings.yaml: a tiny, hand-rolled parser for OUR OWN fixed-shape file ─
# No PyYAML in this environment (and this project deliberately carries zero
# third-party deps) — this parses exactly the two-level structure
# tools/ttp_ingest.py itself writes and ttp/mappings.yaml itself documents:
# a top-level `TECHID:` key, each with a `- field: value` list underneath.
# Not a general YAML parser; raises TtpParseFailure on anything else.

_TOP_KEY = re.compile(r"^([A-Z][A-Za-z0-9.]*):\s*$")
_ENTRY_START = re.compile(r"^  - (\w+):\s*(.*)$")
_FIELD = re.compile(r"^    (\w+):\s*(.*)$")


def _scalar(raw: str):
    raw = raw.strip()
    if raw == "null" or raw == "":
        return None
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def parse_mappings_yaml(path: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    current_key = None
    current_entry: dict | None = None
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _TOP_KEY.match(line)
        if m:
            current_key = m.group(1)
            out[current_key] = []
            current_entry = None
            continue
        m = _ENTRY_START.match(line)
        if m:
            if current_key is None:
                raise TtpParseFailure(f"{path}:{lineno}: entry with no technique key")
            current_entry = {m.group(1): _scalar(m.group(2))}
            out[current_key].append(current_entry)
            continue
        m = _FIELD.match(line)
        if m:
            if current_entry is None:
                raise TtpParseFailure(f"{path}:{lineno}: field with no open entry")
            current_entry[m.group(1)] = _scalar(m.group(2))
            continue
        raise TtpParseFailure(f"{path}:{lineno}: unrecognized line {line!r}")
    return out


VALID_VERDICTS = {"covered", "partially_covered", "uncovered",
                   "asserted_unproven", "not_applicable"}


def ingest_mappings(conn, path: Path = MAPPINGS_PATH) -> dict:
    """Loads ttp/mappings.yaml into ttp_mappings. §3.3 item 5 (platform
    filter) + the schema's own CHECK (verdict='covered' requires
    evidence_id) are both enforced here, with a parse_failures row for a
    proposed mapping that fails either — never silently dropped, never
    silently promoted to 'covered' without real evidence."""
    entries = parse_mappings_yaml(path)
    results = {"mapped": 0, "rejected": 0}
    rel_path = str(path.relative_to(BASE.parent.parent))

    def fail_row(detail: str) -> None:
        prov = add_provenance(conn, rel_path, "ttp_mapping_rejected", None, detail)
        conn.execute(
            "INSERT INTO parse_failures(source_ref, at, detail, provenance_id) "
            "VALUES (?, ?, ?, ?)", (rel_path, utcnow(), detail, prov))

    for attack_id, rows in entries.items():
        tech = conn.execute(
            "SELECT id FROM techniques WHERE attack_id = ?", (attack_id,)
        ).fetchone()
        if tech is None:
            fail_row(f"mapping proposed for {attack_id}, which no ingested "
                     "technique row provides")
            results["rejected"] += len(rows)
            continue

        platforms = {r["platform"] for r in conn.execute(
            "SELECT platform FROM technique_platforms WHERE technique_id = ?",
            (tech["id"],))}
        platform_ok = (
            not platforms
            or bool(platforms & PORTFOLIO_PLATFORMS)
            or bool(platforms & PLATFORM_AGNOSTIC_TAGS)
        )

        for r in rows:
            if not platform_ok and r["surface"] not in PLATFORM_FILTER_EXEMPT_SURFACES:
                fail_row(f"{attack_id}/{r['surface']}: no platform in "
                         f"{sorted(platforms)} intersects this portfolio's "
                         f"surfaces {sorted(PORTFOLIO_PLATFORMS)} (§3.3 item 5) "
                         "— rejected, not mapped")
                results["rejected"] += 1
                continue

            verdict = r["verdict"]
            if verdict not in VALID_VERDICTS:
                raise TtpParseFailure(f"{attack_id}: invalid verdict {verdict!r}")

            evidence_id = None
            anchor = r.get("evidence_anchor")
            if anchor:
                ev = conn.execute(
                    "SELECT id FROM evidence WHERE source_ref LIKE ? "
                    "ORDER BY ingested_at LIMIT 1", (f"%{anchor}%",)).fetchone()
                evidence_id = ev["id"] if ev else None

            if verdict == "covered" and evidence_id is None:
                fail_row(f"{attack_id}/{r['surface']}: verdict='covered' but "
                         f"evidence_anchor {anchor!r} resolved to no real evidence "
                         "row — downgraded to 'asserted_unproven', never silently "
                         "promoted (BUILD-SPEC §3.3 item 2 / §5.5 self-check)")
                verdict = "asserted_unproven"

            cap_id = None
            if r.get("capability"):
                cap = conn.execute(
                    "SELECT id FROM capabilities WHERE agent_or_skill LIKE ?",
                    (f"%{r['capability']}%",)).fetchone()
                cap_id = cap["id"] if cap else None

            prov = add_provenance(
                conn, rel_path, "ttp_mapping", None,
                f"ttp_mappings row from ttp/mappings.yaml: {attack_id} / "
                f"{r['surface']}")
            conn.execute(
                "INSERT INTO ttp_mappings(technique_id, surface, "
                "capability_id, detect_via, limit_via, verdict, evidence_id, "
                "provenance_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(technique_id, surface) DO UPDATE SET "
                "capability_id = excluded.capability_id, "
                "detect_via = excluded.detect_via, "
                "limit_via = excluded.limit_via, "
                "verdict = excluded.verdict, "
                "evidence_id = excluded.evidence_id, "
                "provenance_id = excluded.provenance_id, "
                "ingested_at = excluded.ingested_at",
                (tech["id"], r["surface"], cap_id, r.get("detect_via"),
                 r.get("limit_via"), verdict, evidence_id, prov, utcnow()))
            results["mapped"] += 1

    conn.commit()
    checkpoint(conn)
    return results


# ─── phase_tactics: reviewed data, BUILD-SPEC §3.1's own comment, verbatim ──

PHASE_TACTICS = {
    "init_recon": ["reconnaissance", "resource-development"],
    "persist_expand": ["persistence", "privilege-escalation", "defense-evasion",
                        "discovery", "lateral-movement"],
    "execute": ["initial-access", "execution"],
    "triage_learn": ["collection", "credential-access", "exfiltration"],
    "persist_report": ["command-and-control", "impact"],
}


def seed_phase_tactics(conn) -> int:
    n = 0
    for phase, shortnames in PHASE_TACTICS.items():
        for sn in shortnames:
            row = conn.execute(
                "SELECT attack_id FROM tactics WHERE short_name = ?", (sn,)
            ).fetchone()
            if row is None:
                continue
            conn.execute(
                "INSERT INTO phase_tactics(phase, tactic_attack_id) VALUES (?, ?) "
                "ON CONFLICT(phase, tactic_attack_id) DO NOTHING",
                (phase, row["attack_id"]))
            n += 1
    conn.commit()
    checkpoint(conn)
    return n


# ─── tp_profiles: seeded from ttp/profiles/*.md's own stated fields ─────────

PROFILE_SEEDS = [
    ("patient-fleet", "Salt Typhoon / G1045-class: long-dwell, infrastructure "
     "concentration, telecom-style patience", "high", "very high",
     ["init_recon", "persist_expand", "persist_expand", "triage_learn",
      "persist_report"]),
    ("opportunistic-supplychain", "T1195.001-era: doesn't pick you, waits in "
     "the dependency path", "medium", "opportunistic (ecosystem cadence, not "
     "target-specific)", ["init_recon", "execute", "triage_learn",
                           "persist_report"]),
    ("agent-directed", "targets the agentic pipeline itself — this "
     "portfolio's own supervisor/orchestrators/reporters are the surface",
     "high (narrow band)", "low-to-medium",
     ["init_recon", "execute", "triage_learn", "persist_report"]),
]


def seed_profiles(conn) -> int:
    n = 0
    for name, desc, skill, patience, phases in PROFILE_SEEDS:
        md_path = PROFILES_DIR / f"{name}.md"
        if not md_path.exists():
            raise TtpParseFailure(f"profile seed {name!r} has no {md_path}")
        prov = add_provenance(
            conn, str(md_path.relative_to(BASE.parent.parent)), "ttp_profile",
            hashlib.sha256(md_path.read_bytes()).hexdigest(),
            "profile row mirrors ttp/profiles/*.md, which remains authoritative")
        conn.execute(
            "INSERT INTO tp_profiles(name, description, skill_level, "
            "patience, phase_vector, notes, provenance_id, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET "
            "description = excluded.description, skill_level = excluded.skill_level, "
            "patience = excluded.patience, phase_vector = excluded.phase_vector, "
            "provenance_id = excluded.provenance_id, ingested_at = excluded.ingested_at",
            (name, desc, skill, patience, json.dumps(phases),
             f"see {md_path.name}", prov, utcnow()))
        n += 1
    conn.commit()
    checkpoint(conn)
    return n


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("release", "mappings", "phase-tactics",
                                    "profiles", "all"):
        print("usage: ttp_ingest.py <release|mappings|phase-tactics|profiles|all> "
              "[bundle_path] [tag] [bundle_url] [released_at]", file=sys.stderr)
        return 2
    conn = connect()
    cmd = argv[0]
    out = {}
    if cmd in ("release", "all"):
        bundle_path, tag, bundle_url, released_at = argv[1], argv[2], argv[3], argv[4]
        out["release"] = ingest_release(conn, Path(bundle_path), tag,
                                         bundle_url, released_at)
    if cmd in ("mappings", "all"):
        out["phase_tactics"] = seed_phase_tactics(conn)
        out["mappings"] = ingest_mappings(conn)
    if cmd in ("phase-tactics",):
        out["phase_tactics"] = seed_phase_tactics(conn)
    if cmd in ("profiles", "all"):
        out["profiles"] = seed_profiles(conn)
    conn.close()
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
