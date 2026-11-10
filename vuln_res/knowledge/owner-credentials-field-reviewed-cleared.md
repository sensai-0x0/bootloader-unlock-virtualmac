---
name: owner-credentials-field-reviewed-cleared
type: parsing-pattern
description: plan.rs's owner_credentials bool is not a credential-storage violation, confirmed by review
updated: 2026-11-10
---

An independent, broader grep for credential-shaped tokens (`grep -riE
'(password|passwd|credential|secret|owner_pin|recovery_key)'`) flags
`src/plan.rs:43,123,255,309,313` — the `Requires.owner_credentials: bool` field and its
test/construction sites. This is **not** a violation of golden rule 4 /
`NoCredentialHandling`: it's a boolean flag meaning "does this planned transition require
the owner to supply credentials at apply-time," never a place where an actual credential
value is stored. `scripts/ci_guards.sh`'s own Guard 2 correctly doesn't flag it, because
its type (`bool`) isn't one of the credential-shaped types (`String`/`&str`/`Vec<u8>`/
`[u8]`) the guard checks for.

Recorded so a future sweep's broader/independent credential grep doesn't re-flag this as
new and spend time re-deriving the same conclusion. If `Requires` or a similar struct
ever gains a field of a credential-shaped *type* alongside a credential-shaped *name*,
that would be a real finding — this entry doesn't pre-clear anything beyond the current
`bool` field.
