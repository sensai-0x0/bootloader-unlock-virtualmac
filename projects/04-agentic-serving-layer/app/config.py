"""Phase 1 config: everything path-related resolves under the repo, never /tmp or the host.

See ../CLAUDE.md and ../PROPOSAL.md — this is a prototype's config, not a production
settings layer (no env-specific profiles, no secrets manager integration).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# projects/04-agentic-serving-layer/
SERVICE_ROOT = Path(__file__).resolve().parent.parent

# the-ant-experiment/ repo root
REPO_ROOT = SERVICE_ROOT.parent.parent

SESSIONS_ROOT = SERVICE_ROOT / "var" / "sessions"

VULN_RES_ROOT = REPO_ROOT / "vuln_res"
ENVIRONMENTS_DIR = VULN_RES_ROOT / "knowledge" / "environments"

SUPERVISOR_SCRIPT = REPO_ROOT / "projects" / "supervisor-agent" / "tools" / "supervisor.py"

# Which build of the CLI to shell out to. Configurable per the plan's open decision #4 —
# not hardcoded to one profile. Defaults to release if present, else debug.
_BPUTIL_EVAL_PROFILE = os.environ.get("BPUTIL_EVAL_PROFILE", "release")


def bputil_eval_binary() -> Path:
    candidate = REPO_ROOT / "target" / _BPUTIL_EVAL_PROFILE / "bputil-eval"
    if candidate.exists():
        return candidate
    # Fall back to the other profile rather than failing outright on a fresh checkout
    # that only built one of them.
    other = "debug" if _BPUTIL_EVAL_PROFILE == "release" else "release"
    fallback = REPO_ROOT / "target" / other / "bputil-eval"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"bputil-eval binary not found under target/{_BPUTIL_EVAL_PROFILE} or target/{other} "
        "— run `cargo build` (or `cargo build --release`) in the repo root first."
    )


# Disconnect/reconnect grace period before a session's ClaudeSDKClient is torn down.
DISCONNECT_GRACE_SECONDS = int(os.environ.get("SESSION_DISCONNECT_GRACE_SECONDS", "600"))

# Bounded per-session event replay buffer (see sessions/registry.py).
EVENT_BUFFER_MAXLEN = int(os.environ.get("SESSION_EVENT_BUFFER_MAXLEN", "500"))

_TOKENS_PATH = Path(
    os.environ.get("AGENTIC_SERVICE_TOKENS_PATH", str(SERVICE_ROOT / ".tokens.local.json"))
)


def load_token_table() -> dict[str, dict]:
    """token -> {"principal": str, "allowed_tracks": [str, ...]}.

    Gitignored local file or an env var path — explicitly a prototype auth mechanism,
    not real secrets management. See PROPOSAL.md's "Open risks" section.
    """
    if not _TOKENS_PATH.exists():
        return {}
    return json.loads(_TOKENS_PATH.read_text())
