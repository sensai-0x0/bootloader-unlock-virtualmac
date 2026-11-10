# Decision log

Regenerated view of `decision_log` in `state/portfolio.db` — never edited
by hand. If this mirror and the database disagree, the database wins and
the mismatch goes to `sync_violations` (§3.2).

## 2026-11-10T14:32:45Z — phase-verification — pass

Phase 0 verified: DB opens; migrations 0000,0001 applied idempotently (init run twice, ledger intact); provenance-null = 0 across provenance-bearing tables (none carry provenance_id yet — vacuous at phase 0, enforced from phase 1); self-audit v1 PASS on empty scaffold.

## 2026-11-10T14:32:45Z — self-audit — pass

[]

## 2026-11-10T14:33:49Z — self-audit — pass

[]
