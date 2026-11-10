# Agentic Serving Layer (Phase 1)

See [`PROPOSAL.md`](./PROPOSAL.md) for the architecture and phased plan, and
[`CLAUDE.md`](./CLAUDE.md) for the rules this directory adds on top of the repo's root
and `vuln_res/` constraints.

## Run it locally

```bash
cd projects/04-agentic-serving-layer
uv venv
uv pip install -e ".[dev]" --group dev
cp .tokens.local.json.example .tokens.local.json   # gitignored; edit tokens as you like
uv run uvicorn app.main:app --reload
```

## Try it

```bash
# Create a bootloader-track session
curl -s -X POST localhost:8000/sessions \
  -H "Authorization: Bearer sk-local-dev-bootloader-1" \
  -H "Content-Type: application/json" \
  -d '{"track": "bootloader"}'

# Stream its events (in another terminal), then send it a message
# ws://localhost:8000/sessions/<id>/stream?token=sk-local-dev-bootloader-1

curl -s -X POST localhost:8000/sessions/<id>/messages \
  -H "Authorization: Bearer sk-local-dev-bootloader-1" \
  -H "Content-Type: application/json" \
  -d '{"content": "evaluate the current boot posture"}'
```

## Tests

```bash
uv run pytest
```
