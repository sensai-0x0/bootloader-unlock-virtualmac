# Knowledge index

One line per entry, most relevant/recent first. Read this before starting any sweep.
Each agent that learns something durable (not a finding — see `README.md`) appends a line
here and writes the corresponding file.

<!-- Format: - [title](file.md) — one-line hook (updated: YYYY-MM-DD) -->

- [build-test-clippy-fmt-clean-2026-11-10](./build-test-clippy-fmt-clean-2026-11-10.md) — build/test/clippy/fmt all clean at commit `1b37d16` (updated: 2026-11-10)
- [owner-credentials-field-reviewed-cleared](./owner-credentials-field-reviewed-cleared.md) — `plan.rs`'s `owner_credentials: bool` is not a credential-storage violation (updated: 2026-11-10)
- [command-enum-name-collision-tool-note](./command-enum-name-collision-tool-note.md) — `main.rs`'s `Command` enum textually collides with `std::process::Command` in grep output, not a real guard gap (updated: 2026-11-10)
- [cargo-audit-cargo-deny-not-installed](./cargo-audit-cargo-deny-not-installed.md) — installed with approval; `cargo audit` clean, 0 vulnerabilities across 66 crates (updated: 2026-11-10)

No `environment` entries yet — no disposable VM/container has been created. No
`target-status` entries for fuzz targets yet — `02-fuzzing-harness-agent.md` hasn't been
executed.
