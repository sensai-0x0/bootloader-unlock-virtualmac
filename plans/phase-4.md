# Phase 4 — Permissive path, revert, and control surface: not started

Do not start this until every box in `phase-3.md`'s exit criteria is checked — the
Reduced-Security round trip is the least-invasive mutating path, and it needs to be fully
proven (including revert) before the riskier Permissive/custom-kernel path is exercised.
Same hardware caveat as `phase-3.md`: scratch Mac or scratch container only, human present
and driving 1TR throughout.

## 1. Resolve the custom boot object path first

`src/plan.rs`'s `commands_for(PermissiveCustomKernel, ...)` currently emits a literal
placeholder, `<custom-boot-object-path>`, for `kmutil configure-boot -c <path>`. Before
this phase can run for real, decide:
- What the actual custom boot object is for your test (a minimal custom kernel/kernelcache
  built for this purpose, or an existing one you have rights to use for testing).
- Where it lives on the scratch volume, and replace the placeholder in `commands_for` with
  a real parameter threaded through from the CLI or a config file — not another hardcoded
  string.

## 2. Permissive enrolment

With `authorize`/`execute`/`verify` already implemented in `phase-3.md`:
1. `cargo run --release -- plan permissive-custom-kernel --json > plan.json` from the
   scratch container in macOS.
2. Reboot to 1TR, `apply --plan plan.json`.
3. Back in macOS, `verify` and confirm: `security_mode == Permissive`,
   `ssv_enabled == false`, the custom boot object appears in `enrolled_objects` with
   `signer == SepLocalPolicy` (this needs `phase-1.md` item 1's IMG4-into-`collect` wiring
   done first — you can't verify the enrolled object's signer without it).

## 3. `revert` from Permissive

Implement/extend `src/execute.rs` and `src/plan.rs` so `revert` works from *either*
mutating state back to `Full`, not just the `Reduced -> Full` path exercised in
`phase-3.md`. Confirm via `verify`:
- `security_mode == Full`
- `sip.status == Enabled` (per `spec/contract-spec.md`'s `revert` postcondition — note
  `CLAUDE.md`'s deviations list doesn't resolve where exactly `sip.status` lives in
  `BootState`; resolve that now if you haven't already, since `revert`'s own contract
  depends on it)
- no `CustomBootObject` remains in `enrolled_objects`

## 4. The control surface

Per `spec/build-spec.md`'s "Operate specification": build the interactive flow an
operate-agent-or-human drives — `evaluate` -> `plan` (autonomous, no gate), then an
explicit hand-off message telling the human to reboot to 1TR and authenticate, then
`apply` -> `verify`. Concretely:
- A CLI mode (or a flag on the existing subcommands) that, after printing a `plan`, prints
  something like "Reboot into 1TR, open Terminal, and run: `bputil-eval apply --plan
  <path>`" rather than attempting to continue automatically.
- **The autonomy-boundary test**, which `spec/phased-plan.md`'s P4 exit gate requires
  explicitly: write a test proving that a fully agent-driven run (no human stdin, no 1TR)
  cannot reach `apply`'s mutation regardless of what plan or confirmation input it's fed.
  This is really `phase-3.md`'s `is_mutation_allowed`/`authorize::confirm` guarantees,
  re-asserted at the CLI/control-surface level rather than just the library level.

## Exit criteria

- [ ] `full -> permissive -> full` round trip verified on the scratch container.
- [ ] The autonomy-boundary test passes: an agent-driven run cannot reach `apply` without
      the human gate.
- [ ] `revert` works from both `Reduced` and `Permissive`.
