# Environment profile schema

One file per registered virtual environment under `environments/<env-id>.md`, this exact
frontmatter shape, so any agent in this suite can parse the registry without guessing a
provider's specifics. This is what makes the suite **general across any virtual
environment that gets spawned** — new infrastructure gets onboarded by adding a profile,
never by teaching an agent a new provider's API.

```yaml
---
id: kebab-case-unique-id
provider: tart | docker | orbstack | remote-worktree | remote-sandbox | other
lifecycle: disposable | persistent
status: active | torn-down
created_at: YYYY-MM-DDThh:mm:ssZ
created_by: which agent or human requested it
approved_for: [fuzzing, exploit-dev, vm-hygiene-audit]   # exactly what the user approved
approved_by: human | n/a
network: isolated | host-bridged | unknown
resource_caps: { cpu: "<n> cores", mem: "<n>GB", time_budget: "<n> minutes" }
---

Free-text notes: what this environment actually is, how to reach it (a command or
connection detail — never a credential), what's been run inside it so far, and when/why
it should be torn down.
```

## Rules an agent must follow when using this registry

1. **Never execute anything without first finding or creating a matching profile.** "No
   profile" means "no approved environment" — ask the user, don't improvise with the host.
2. **`approved_for` is scoped, not blanket.** An environment approved for `fuzzing` is not
   automatically approved for `exploit-dev` — if a task needs a capability the profile
   doesn't list, ask the user before proceeding, and update the profile once they say yes.
3. **`lifecycle: persistent` environments still default to "ask before reusing."** Most
   environments this suite creates should be `disposable` — a `persistent` one is the
   exception, and reusing it for a new, different purpose than it was created for is a
   fresh ask, not an assumption.
4. **Tear-down is recorded, not silently forgotten.** When an environment is destroyed,
   flip `status: torn-down` rather than deleting the file — the history (what ran, for how
   long, what it found) is itself knowledge worth keeping.
5. **No credential, token, or secret ever goes in a profile.** "How to reach it" means a
   command or an identifier, never a password or key — same `NoCredentialHandling` spirit
   as the rest of this project.
