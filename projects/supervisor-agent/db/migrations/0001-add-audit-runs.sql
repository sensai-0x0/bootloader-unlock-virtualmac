-- Migration 0001 — phase 0: audit_runs.
-- BUILD-TIME AMENDMENT (recorded in BUILD-SPEC §3.5): the phase-0 text named
-- only meta/provenance/runs/decision_log, but §7 ("records EVERY run, pass and
-- fail — a silent pass is as unpublishable as a loud fail") and §3.4's map both
-- require the self-audit to have its own table from the first run. Shipping it
-- with phase 0 rather than papering audits into decision_log-only storage.
-- Idempotent by construction.

CREATE TABLE IF NOT EXISTS audit_runs (
    id                 INTEGER PRIMARY KEY,
    run_id             INTEGER NULL REFERENCES runs(id),
    checklist_version  TEXT NOT NULL,
    passed             INTEGER NOT NULL,
    violations         TEXT NOT NULL,   -- JSON list; empty list = clean pass
    at                 TEXT NOT NULL
);
