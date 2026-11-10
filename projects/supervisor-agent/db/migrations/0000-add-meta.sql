-- Migration 0000 — phase 0: the meta table.
-- Idempotent by construction (BUILD-SPEC phase-0 acceptance: migrations apply
-- twice, cleanly). The matching cumulative DDL lives in db/schema.sql.

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
