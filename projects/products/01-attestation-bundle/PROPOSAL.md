# Product 1 — Boot-Security Attestation Bundle

**One-line pitch:** package the already-built, hash-chained evidence bundle format as a
standalone, independently-verifiable compliance artifact — "prove this fleet's boot
security posture, cryptographically, right now" — for security/compliance teams managing
Apple Silicon fleets.

## APT-mindset framing

An attacker who has weakened a device's boot security wants that fact to stay unprovable
after the fact — no attestation, no way for a third party (an auditor, a compliance
reviewer) to check the claim without trusting whoever's reporting it. The defensive
inversion is a product, not just a research artifact: sell the thing that makes "prove
your fleet's boot security state, with evidence a stranger can verify without trusting
you" a routine, cheap operation instead of a special request.

## What's reused from this repo today

- `report.rs` — the hash-chained bundle format already exists and is already proven: see
  `evidence/vm-sec-research-25D125/README.md` for a real, working example with a
  `shasum -a 256 -c` verification instruction anyone can run themselves.
- `spec/contract-spec.md`'s `EvidenceComplete` invariant — the exact completeness
  predicate this product's artifact must satisfy is already specified, not invented fresh.
- [Project 3 (Fleet Boot-State Drift Watch)](../../03-fleet-drift-watch/PROPOSAL.md) — this
  product is a thin packaging layer on top of that project's periodic per-Mac evidence,
  not a new measurement capability. It makes no sense to build before project 3 exists.

## Architecture (prose)

Each enrolled Mac's periodic evidence bundle (from project 3) gets wrapped in a real
cryptographic signature — not just the sha256 hash-chaining already in place, which proves
internal consistency but not who produced it. Signing happens with a key under the
device owner's own control (their keychain, or an enterprise KMS they already run) — this
product never generates, custodies, or sees that key itself. An independent, small
verifier (a CLI or a static page) lets an auditor check a bundle's hash chain and
signature without installing this project's tooling or trusting its vendor at all — the
same spirit as the existing bundle's own "verifying this bundle yourself" section, just
extended to include signature verification, not only hash verification.

## Guardrail mapping

| Guardrail | How this product respects it |
|---|---|
| Read-only, forever | This product only ever packages the output of `evaluate`/`verify`/`report` — it never ships `apply`/`revert` as a hosted or automated feature. That stays a human-gated, owner-present, local tool only, per golden rule 4, and is explicitly not on this product's roadmap, ever. |
| `NoCredentialHandling` | Signing-key custody stays entirely with the customer (their keychain or their own KMS) — this product never holds, transmits, or logs a signing key, mirroring the same boundary the core tool already draws around owner credentials. |
| Honesty of state | The artifact is only ever built from a genuine `report.rs` bundle — no synthetic or "representative" attestation is ever produced, even for a demo; the existing M8–M10 bundle already serves as the real worked example. |

## Phased build order

1. Internal dogfood using the existing evidence bundle format exactly as-is — no new code
   yet, just confirming the packaging story works end to end on real output.
2. Add real signing on top of the existing sha256 hash-chain (device keychain or
   enterprise KMS integration — customer's choice, never this project's own key).
3. Build the independent verifier as a separate, minimal artifact (no shared code with the
   signer, so an auditor's trust in the verifier doesn't depend on trusting the signer).
4. Packaging/pricing/go-to-market — explicitly not a build-now item; this proposal stops
   at "the artifact and its verifier work," not "this is a company."

## Open risks / what needs sign-off before any code runs

- **This product only makes sense once project 3 exists** — it's a go-to-market wrapper
  on fleet-scale measurement, not new core capability, and shouldn't be started first.
- Signing-key custody design needs real security review before any customer data (even a
  single pilot customer's) touches it — a flawed custody model would undermine the exact
  trust property this product exists to sell.
- Scope discipline: the temptation with any "compliance product" is to quietly add
  mutation/remediation features ("and we can also fix it for you") — that crosses directly
  into project 2's territory and its human-gate requirement; this product's roadmap should
  treat that as explicitly out of scope, not a natural next feature.

## Success metric

A test user in an "auditor" role can verify a sample attestation bundle's hash chain and
signature using only the published, independent verifier — with zero access to this
project's source code and zero trust placed in the vendor beyond the public key itself.
