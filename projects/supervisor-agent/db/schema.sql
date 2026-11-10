-- supervisor-agent fused portfolio database — CUMULATIVE DDL, versioned as code.
-- Implements BUILD-SPEC.md §3.1. Every statement is idempotent (IF NOT EXISTS) so
-- the full script replays safely on any database, alongside the numbered migrations
-- in db/migrations/ (see BUILD-SPEC §3.5 build-time rule below the file inventory).
--
-- Phase status of this snapshot: phase 0 (meta / provenance / runs / decision_log only).
-- Later phases extend this file with their tables (§3.1 core fused state,
-- staleness/implication/ranking, TTP layer, human outputs) and add the matching
-- numbered migration.

PRAGMA journal_mode = WAL;

-- ─── meta / provenance backbone ──────────────────────────────────────────────
-- Every substantive row that asserts a PORTFOLIO fact carries provenance_id
-- (non-nullable). Self-governance tables (meta, runs, decision_log, and later
-- audit_runs) are the exception by construction: each row's provenance IS the
-- run that wrote it, so the §7 provenance-null check scopes to tables that
-- actually have a provenance_id column.

CREATE TABLE IF NOT EXISTS provenance (
    id           INTEGER PRIMARY KEY,
    source_ref   TEXT NOT NULL,   -- file path + anchor (file.md#heading or file:line)
    source_sha   TEXT,            -- blob hash when the source is committed content
    source_type  TEXT NOT NULL,   -- registry id from ontology/sources.yaml
    derived_from BLOB,            -- JSON: which upstream rows/queries produced this
    note         TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id               INTEGER PRIMARY KEY,
    started_at       TEXT,
    ended_at         TEXT,
    trigger          TEXT,
    sources_parsed   TEXT,   -- JSON list of registry ids parsed this run
    degraded_sources TEXT,   -- JSON list of registry ids degraded to authority 0
    db_version       INTEGER,
    schema_hash      TEXT,
    outcome          TEXT
);

CREATE TABLE IF NOT EXISTS decision_log (
    id        INTEGER PRIMARY KEY,
    at        TEXT NOT NULL,
    kind      TEXT NOT NULL,
    brief_id  INTEGER NULL,
    ticket_id INTEGER NULL,
    outcome   TEXT NOT NULL,
    detail    TEXT NOT NULL
);
