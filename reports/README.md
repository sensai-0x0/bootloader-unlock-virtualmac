# Reports

Technical reports summarizing `bputil-eval`'s build and execution state, and the disposable-VM research track. Each report is self-contained and dated; see its own header for scope and source material.

- [`build-product.md`](./build-product.md) — architecture, module layout, dependencies, spec deviations, and test coverage of the Rust binary as built (P0–P2).
- [`execution-product.md`](./execution-product.md) — what running the binary actually produces: CLI surface, exit codes, evidence model, and the precise line between what's been verified on real hardware versus specified-but-unexecuted.
- [`disposable-vm.md`](./disposable-vm.md) — the simulated-research track: Track A (static IPSW ground truth) and Track B (a real macOS VM), what's been attempted, what blocked it, and host-impact disclosure.
- [`unlocked-bootloader-evidence.md`](./unlocked-bootloader-evidence.md) — precisely what "unlocked" means in this project, the four-step evidence chain required to demonstrate it, and why the VM's chip generation must match or be older than the host's own before that chain can even be attempted.

All four reports are documentation only — no mutating commands were run against this host or any device to produce them, beyond the local, reversible `cargo build`/`cargo test` already covered by `reports/execution-product.md` §2.
