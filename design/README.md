# vuln_res dashboard — design system

A static design system for the `vuln_res/` suite (the vulnerability
researcher / exploit-dev agent pipeline that hunts bugs in bputil-eval's own
code — never Apple's platform). Two views:

- **`view-1-sweep-findings.html`** — grounded in `vuln_res/`'s real on-disk
  vocabulary: sweeps, findings, the `reachability × weight × blast-radius`
  score, and the `open | fixed | disclosed-upstream | false-positive |
  escalated-to-human` status set.
- **`view-2-campaign-overview.html`** — deliberately more atmospheric;
  exploit chains in flight, not tied as tightly to the exact schema.

All row content is **illustrative sample data** assembled from real finding
slugs and vocabulary seen in the repo (e.g.
`security-mode-full-contains-whole-blob`), not a snapshot of the live
findings store. Nothing here reads from or writes to `vuln_res/`'s actual
files.

## Files

| File | Purpose |
|---|---|
| `tokens.css` | Color, type, spacing custom properties |
| `shared.css` | Ledger table/row mechanics, severity glyph, status tick, view dial, stage rule |
| `components.md` | Spec for each custom component and why it exists instead of a default (card, badge, button) |
| `AESTHETIC.md` | The "neuropunk paper" aesthetic itself — the paper/signal premise, material vocabulary, and interaction grammar everything else here is built from |
| `FEATURE-PLAN.md` | Maps `spec/contract-spec.md`'s `BootState`/`PlannedTransition`/`Report` contracts onto this design system |
| `view-1-sweep-findings.html` | Sweep &amp; findings ledger |
| `view-2-campaign-overview.html` | Campaign / exploit-chain overview |

## Preview

No build step — open either HTML file directly, or serve the folder:

```
bunx serve design
```

## Design principles

See `AESTHETIC.md` for the aesthetic itself and `components.md` for the
component-level spec. At a glance: ledger rows instead of cards, hierarchy
by hue (paper-white / signal-green / signal-green-muted) instead of size,
severity as a spatial glyph instead of a colored badge, and no `<button>`
anywhere — every interaction is a native disclosure (`<details>`),
checkbox, or anchor styled to not look like one.
