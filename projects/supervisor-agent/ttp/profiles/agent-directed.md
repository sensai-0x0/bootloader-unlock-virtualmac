# Profile: agent-directed

**Class modeled:** the ATT&CK v20.1 novelty — an adversary whose techniques target
the agentic pipeline itself, not a human operator. Per BUILD-SPEC §5.3 item 3. This is
the profile whose persona is *this portfolio's own supervisor, orchestrators, and
reporters* — the only one of the three profiles that treats the thing running this
simulation as the attack surface, which is also why its guardrails matter most:
every technique here stays a decision-model question about evidence, never generated
attack content (§5.1, §5.5 hard boundary, restated here because this is the profile
most tempting to over-build).

## Skill level
High in a narrow band: doesn't need traditional intrusion tradecraft, needs fluency in
exactly what a parsing/ingestion pipeline will treat as data versus instruction.

## Patience
Low-to-medium. Prompt-injection-class techniques are opportunistic per-ingestion
events, not long-dwell — the "patience" that matters here is persistence of a planted
artifact (a poisoned knowledge file, fixture, or sweep report) sitting in the corpus
until some future ingestion run reads it, not patience in the Salt Typhoon sense.

## Primary interest
The supervisor's own read paths: `vuln_res/knowledge/INDEX.md` and linked files,
`vuln_res/sweep-reports/`, `progress/milestones.md`, each parsed verbatim into
`evidence`/`milestone_log` rows that downstream scoring and brief generation treat as
trusted fact. Its gaps feed the supervisor's own self-hardening honestly, exactly as
BUILD-SPEC §5.3 item 3 frames it: "an indirect prompt injection in a parsed knowledge
file could steer briefs — which capability validates ingestion?"

## Phase vector
`init_recon -> execute -> triage_learn -> persist_report`
(JSON: `["init_recon","execute","triage_learn","persist_report"]`)

## Technique preferences per phase
- `init_recon`: identify which of the supervisor's own parsed sources accept free-text
  bodies the parser doesn't constrain beyond its documented regex/footer rules (the
  knowledge entry `hook` text, milestone `detail`/`next_up` free text, a sweep report's
  prose) — these are the candidate injection surfaces.
- `execute`: **T1698** (Indirect Prompt Injection) via a crafted knowledge-entry hook
  or milestone log line that `tools/parsers.py` would ingest verbatim into `evidence`/
  `milestone_log.detail`, reasoning that downstream consumption is by an LLM-driven
  brief/decision step, not just a human reading markdown. **T1699** (Direct Prompt
  Injection) is recorded `not_applicable` for this portfolio today — there is no
  surface where an external party supplies a prompt directly to this supervisor's own
  model context; every parsed source is this repo's own committed content, read via
  the audited `tools/parsers.py` path, not a live third-party feed.
- `triage_learn`: **T1608.007** (Stage Capabilities: AI Result Poisoning) — a planted
  artifact engineered to look like a legitimate *past* finding/measurement (not an
  instruction), so a future triage/scoring pass treats fabricated precedent as real.
  This is the technique this profile is best attested for under real-usage framing
  (ATT&CK v20.1's own stated target: AI-enabled adversary operations against
  agent-driven defensive pipelines "like this portfolio's own agent fleet" — BUILD-SPEC
  §5.2's own words, not invented here).
- `persist_report`: **T1685.007** (Disable or Modify Tools: Impair Autonomous
  Defenses) against the `vulnres-*` autonomous capabilities (`vulnres-disclosure`,
  `vulnres-exploit-dev`, `vulnres-triage` — the three with `approval_class=
  'autonomous'`) — if an upstream injection or poisoning step succeeded, this is the
  technique that would try to quiet the capability that would otherwise have caught it.

## Stop conditions
- A gap probe finds a capability that already validates ingestion content (parses
  with a bounded grammar, rejects unexpected structure, or otherwise doesn't hand raw
  text to a downstream model untouched) — the profile records that surface `covered`
  and moves on.
- Every candidate surface resolves `covered` or `not_applicable` — scenario ends; this
  would be the strongest possible outcome for this portfolio and is recorded as such,
  not downgraded to manufacture a gap that doesn't exist.

## Expected honest gap (today's real state)
`tools/parsers.py` parses knowledge/milestone/sweep-report free text into `evidence`/
`milestone_log` rows with no content-classification step between "this is data I'm
recording" and "this is an instruction I should act on" — there is no capability in
`capabilities` whose `trigger_contract` names ingestion-content validation as its job.
That is this profile's honest gap probe: *which capability validates ingestion?*
(BUILD-SPEC §5.3's own question) — today, none does; this simulation surfaces that as
a finding for the human, never as a reason to self-modify.
