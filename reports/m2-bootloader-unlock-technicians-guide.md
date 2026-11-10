# Technician's Guide to M2 Bootloader Unlock Progress

**Audience:** a hobbyist running local models (quantized LLMs, RAG stacks) on their own Apple Silicon Mac, interested in self-hosting and hardware/OS modification.
**Report date:** 2026-11-10
**Scope:** this project's current state, specifically as it applies to the M2 generation — which happens to be the chip generation this project's own development host runs.

This guide translates `reports/build-product.md`, `reports/execution-product.md`, `reports/disposable-vm.md`, and `reports/unlocked-bootloader-evidence.md` into a single, practical read for someone who wants to know: *what does "unlocking" an M2 Mac's bootloader actually mean, where does this project stand on it, and what, if anything, can I do with that today while hosting local models?*

## 1. Read this section before anything else

**"Bootloader unlock" here is not a jailbreak, and this is not a bypass tool.** It refers to exactly one thing: the `bputil` security-mode spectrum — `Full → Reduced → Permissive` — moved through this project's custom toolchain driving `bputil`/`kmutil`/`csrutil`, by the device's owner, physically present in One True Recovery (1TR), typing their own credentials. There is no signature forgery, no Secure Enclave attack, and no way to do any of this remotely or without owning the hardware. If that's what you were hoping for, stop here — it's explicitly out of scope for this project (`spec/build-spec.md`'s "Out of scope and prohibited" section), and no extension of it will change that.

What it *is* useful for: there's a reversible path to loosen two specific restrictions, for people who need them:

| `SecurityMode` | Unlocks | Typical hobbyist reason to want it |
|---|---|---|
| `Full` (default) | — | Normal use; this is where your Mac ships |
| `Reduced` | Loading third-party (non-Apple-signed) kernel extensions | Legacy or specialty hardware drivers that need a kext, not a modern system extension |
| `Permissive` | Booting a fully custom/unsigned kernel | Running an alternative OS kernel (e.g., the kind of work the Asahi Linux project does on Apple Silicon) |

If you're hosting local models and hitting a wall that's specifically about *driver or kernel-level* access — not something a user-space tool, a Metal/Accelerate API, or a signed system extension can already do — this is the relevant mechanism. It is **not** something that speeds up inference by itself, and this project makes no performance claims of any kind; it only measures and plans a security-policy change, honestly.

## 2. The vocabulary, precisely

- **`SecurityMode`** — `Full`, `Reduced`, or `Permissive`. The thing being "unlocked" is this value, nothing else.
- **1TR (One True Recovery)** — the paired recovery environment tied to your specific Mac's Secure Enclave. Mutating commands only run here, never from ordinary macOS.
- **`bputil`** — the CLI this project's custom toolchain uses for reading and changing `SecurityMode`.
- **`kmutil`** — the CLI used for the kernel-extension/kernel-collection side of a `Permissive` custom-kernel setup.
- **`csrutil`** — the CLI used for SIP/SSV (System Integrity Protection / Signed System Volume) status, which a `SecurityMode` change interacts with.
- **Owner authorization** — a human, physically at the machine, in 1TR, typing their own credentials. No tool — this one included — stores, prompts for, or automates that step. That's a hard rule (`spec/build-spec.md` golden rule 4), not a current limitation waiting to be lifted.

## 3. Where the M2 generation specifically stands

This matters more than it might look, because of one concrete, confirmed finding from this project's own research (`reports/disposable-vm.md`, `reports/unlocked-bootloader-evidence.md` §3):

**Apple's Virtualization.framework will only let a host create a VM targeting its own chip generation or an older one — never a newer one.** This was discovered first-hand when an M6-generation restore image failed immediately (`UnsupportedRestoreImageError()`) on this project's M2 Pro development host.

The practical consequence, specifically for the M2 generation: **if your own Mac is an M2 (or M2 Pro/Max/Ultra), you are in the single best position of any chip generation to test this project's disposable-VM research path today**, because:

- You can create a macOS VM targeting your own M2-generation IPSW, or any older generation, without hitting the chip-mismatch block that stopped the M6 attempt cold.
- That means the open research question — does `bputil`'s SEP/LocalPolicy-dependent mutation path actually work inside a virtualized guest at all? — is directly answerable on M2 hardware *today*, where it currently is not on this exact host for anything newer than its own generation.
- This is exactly the path the project's own milestone log (`progress/milestones.md`, M8) is pursuing right now: retrying VM creation with `tart create --from-ipsw=latest` (or an exact `sw_vers`-matched build) instead of an unreachable newer-generation image.

As of this report, that M8 attempt is **in progress, not yet confirmed successful** — the most recent log entry describes an in-progress download, not a completed VM boot. So the honest, current answer to "has anyone actually evidenced an M2 bootloader unlock through this project" is: **not yet, on any target, real or virtual.** See `reports/execution-product.md` §5–6 for exactly what has and hasn't run.

## 4. What you can actually run today, safely

Everything below is read-only. None of it changes anything on your Mac.

```bash
git clone <this repo>
cd the-ant-experiment
cargo build

# Measure your Mac's current boot-chain trust state
cargo run -- evaluate --json

# See exactly what commands a Reduced-Security transition would run — without running them
cargo run -- plan reduced-kexts --json

# Same, for the Permissive/custom-kernel profile
cargo run -- plan permissive-custom-kernel --json

# Produce a reproducible, hash-chained evidence bundle of a session
cargo run -- report --out-dir ./my-session
```

`evaluate` run twice differs only in its timestamp — that's a tested, enforced guarantee (`reports/build-product.md` §7), not a claim. `plan` shows you the *exact* `bputil`/`kmutil` invocations a transition requires, with their consequences (SSV off, SIP change) spelled out, before anything is ever run for real. This is a genuinely useful, safe way to understand what a `Reduced` or `Permissive` transition on your own machine would actually involve, without touching anything.

Note: without a cached `sudo` credential, `evaluate`/`plan` will correctly report `security_mode: Unknown` rather than guess — this is the tool failing closed, as designed, not a bug (`reports/execution-product.md` §2).

## 5. What's not there yet, and why that's deliberate, not an oversight

`apply` and `revert` — the commands that would actually carry out a transition — print "not implemented (P3/P4)" and exit non-zero, on purpose. There is no mutation logic in this codebase at all yet. This is not a missing feature waiting on more development time in the ordinary sense: `spec/phased-plan.md`'s gate between the read-only phases (P0–P2, done) and the mutating phases (P3–P5, not started) explicitly requires a disposable scratch target — a VM or a scratch Mac nobody minds bricking — proven to round-trip `Full → Reduced → Full` before any mutation code is written at all. Shipping that logic untested against a real boot-security surface would be worse than not shipping it (see `reports/execution-product.md` §6).

So: there is currently **no way**, through this tool, to actually carry out a `SecurityMode` transition — on an M2 Mac or any other generation. The honest state of the project is a trustworthy *measurement and planning* tool, plus an *in-progress* research effort to find a safe target to prove the rest against.

## 6. If you decide to do this on your own M2 Mac anyway, outside this tool

Nothing above stops you from running `bputil`/`kmutil` directly yourself — they're not something this project gates. If you do:

- **Use a scratch APFS volume group, not your only boot volume**, exactly as `spec/phased-plan.md`'s P3 requires of this project's own testing. Loading a genuinely incompatible third-party kext or an unsigned kernel can leave a volume group unbootable; recovery from that is a real DFU/Internet-Recovery process, not a hypothetical.
- **Know the revert path before you need it.** `bputil -m -r` (back to Full Security) is the documented way back; confirm it works on a disposable volume before you ever touch one you care about.
- **A kext or custom kernel you didn't write and can't audit is the actual risk**, not the `SecurityMode` change itself. `Reduced`/`Permissive` only *permit* loading such code — they don't vet it. The signing requirement in `Full` mode exists precisely to filter out exactly what you'd be re-enabling.
- Run `cargo run -- evaluate --json` from this project before and after, even outside its own `apply`, just to get a real, structured, hash-evidenced record of what state you were in and what you moved to. The read-only half of this tool is genuinely useful standalone for that, independent of whether its own mutation pipeline ever ships.

## 7. How to track real progress, not just this guide's snapshot

- `progress/milestones.md` — the living log of the VM-research track (M0–M9), updated with dated entries, not just status flips.
- `progress/goal.md` — the precise definition of "unlocked" this whole project holds itself to, and the chip-generation finding that reframed the research track.
- `reports/disposable-vm.md` and `reports/unlocked-bootloader-evidence.md` — the full detail behind §3 above.
- `plans/extension-local-model-hosting.md` — the forward-looking plan (companion to this guide) for what happens once the VM or scratch-hardware round trip actually succeeds, specifically for people hosting local models.

## 8. FAQ

**Does this let me run unsigned/pirated software?** No. `Reduced`/`Permissive` only govern kernel extensions and the kernel itself — not application-level code signing, Gatekeeper, or notarization, none of which this project touches.

**Will this speed up my local model inference?** Not by itself, and this project makes no such claim. It's a prerequisite-enabling mechanism for driver/kernel-level work, not a performance tool.

**Can I do this remotely, or on a Mac I manage but don't physically have?** No — by design. 1TR requires physical presence and a human typing real credentials; this is a hard boundary in both the underlying implementation and this project's golden rules, not a current gap.

**Is my M2 Mac specifically more "unlockable" than other generations?** Not in terms of what's permitted — the `Full/Reduced/Permissive` spectrum is identical across Apple Silicon generations. What's specific to M2 is that it's currently the *easiest generation to research safely in a disposable VM*, for the chip-generation reason in §3 — which matters for how fast this project's own research can move, not for what you're ultimately permitted to do on your own hardware.
