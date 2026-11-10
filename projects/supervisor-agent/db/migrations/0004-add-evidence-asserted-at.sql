-- Migration 0004 — phase 2: evidence.asserted_at.
-- The phase-2 parsers key chronology off the date each claim itself asserts
-- (`updated:` lines / sweep dates); R2 needs that as a first-class column
-- (claim_anchors covers knowledge rows; this covers every evidence kind).
-- Ledger-guarded ALTER: safe to run once per database; the cumulative snapshot
-- (db/schema.sql) already carries the column, and apply_ddl seeds the ledger
-- without replaying migrations on a fresh snapshot-built DB.
ALTER TABLE evidence ADD COLUMN asserted_at TEXT NULL;
