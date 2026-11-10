---
sweep_id: <YYYY-MM-DD>-<NNN>-<short-label>
date: <YYYY-MM-DD>
agents_run: [vulnres-recon, ...]
environments_used: [<env-id from knowledge/environments/>, ...]   # or [] if static-only
duration: <wall-clock>
---

## What this sweep did and why

One or two sentences of context — what triggered this sweep (new code, scheduled check,
explicit request), and what it covered.

## Commands actually run

```
<every command actually executed, with real exit codes — not a description of what
would run. This is what makes a sweep report verifiable rather than a narrative.>
```

## Findings produced

- [<finding-slug>.md](./<finding-slug>.md) — one-line hook, score if applicable

(or "none — everything checked came back clean / already known")

## Knowledge entries written or updated

- [<slug>](../../knowledge/<slug>.md) — one-line hook

## Blocked on / escalated to human

Anything the one-subagent-maximum rule couldn't resolve, any environment-approval ask
still pending, or any finding scored severe enough to need a human verdict before the
pipeline continues.
