-- Migration 0002 — phase 1: two-source fusion core.
-- Tables: parse_failures, initiatives, evidence, milestones, milestone_log, links
-- (BUILD-SPEC §3.1). Build-time amendment recorded here and in §3.5 item 6:
-- initiatives.kind adds 'vm_sec_research' — progress/milestones.md's M0–M10 track
-- belongs to the pre-vuln_res bootloader-research program (progress/goal.md), which
-- none of the original five kinds describe. Honest schema beats a wrong CHECK.
-- Idempotent by construction.

CREATE TABLE IF NOT EXISTS parse_failures (
    id            INTEGER PRIMARY KEY,
    source_ref    TEXT NOT NULL,
    at            TEXT NOT NULL,
    detail        TEXT NOT NULL,
    provenance_id INTEGER NOT NULL REFERENCES provenance(id)
);

CREATE TABLE IF NOT EXISTS initiatives (
    id              INTEGER PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN (
        'project1_fuzz', 'project2_mutation', 'project3_drift',
        'vulnres_suite', 'supervisor', 'vm_sec_research')),
    status          TEXT NOT NULL,
    phase_coverage  TEXT,
    owner_gate      TEXT,
    proposal_ref    TEXT,
    status_file_ref TEXT NULL,          -- NULL until a project's phase-1 file exists
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    id             INTEGER PRIMARY KEY,
    initiative_id  INTEGER NOT NULL REFERENCES initiatives(id),
    kind           TEXT NOT NULL CHECK (kind IN (
        'knowledge', 'sweep_summary', 'finding', 'exploit', 'milestone',
        'measurement', 'rollup', 'environment_entry', 'fuzz_result', 'commit_event')),
    verdict_class  TEXT,
    content_hash   TEXT,
    source_ref     TEXT NOT NULL,
    provenance_id  INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at    TEXT NOT NULL,
    UNIQUE(source_ref, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_evidence_initiative ON evidence(initiative_id);
CREATE INDEX IF NOT EXISTS idx_evidence_kind ON evidence(kind);

CREATE TABLE IF NOT EXISTS milestones (
    id             INTEGER PRIMARY KEY,
    initiative_id  INTEGER NOT NULL REFERENCES initiatives(id),
    m_ref          TEXT NOT NULL,               -- 'M8' …
    title          TEXT NOT NULL,               -- verbatim from the table row
    status         TEXT NOT NULL,               -- verbatim from the table row
    evidence_ref   TEXT,
    provenance_id  INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at    TEXT NOT NULL,
    UNIQUE(initiative_id, m_ref)                -- invariant: never renumbered/inserted
);
CREATE INDEX IF NOT EXISTS idx_milestones_initiative ON milestones(initiative_id);
CREATE INDEX IF NOT EXISTS idx_milestones_ref ON milestones(m_ref);

CREATE TABLE IF NOT EXISTS milestone_log (
    id              INTEGER PRIMARY KEY,
    initiative_id   INTEGER NOT NULL REFERENCES initiatives(id),
    occurred_at     TEXT NOT NULL,              -- the dated entries BEHIND the table;
    sequence        INTEGER NOT NULL,           -- source order, 1-based within file
    heading         TEXT NOT NULL,              -- verbatim heading after '--'
    m_refs_touched  TEXT,                       -- JSON list of 'M8'-style refs
    detail          TEXT NOT NULL,
    next_up         TEXT,                       -- 'Next up' lines: decision-engine input
    entry_key       TEXT NOT NULL UNIQUE,
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mlog_initiative ON milestone_log(initiative_id);

CREATE TABLE IF NOT EXISTS links (
    id            INTEGER PRIMARY KEY,
    src_type      TEXT NOT NULL,
    src_id        INTEGER NOT NULL,
    dst_type      TEXT NOT NULL,
    dst_id        INTEGER NOT NULL,
    link_type     TEXT NOT NULL,
    weight        REAL DEFAULT 1.0,
    provenance_id INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at   TEXT NOT NULL,
    UNIQUE(src_type, src_id, dst_type, dst_id, link_type)
);
CREATE INDEX IF NOT EXISTS idx_links_src ON links(src_type, src_id);
CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst_type, dst_id);
