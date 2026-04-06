"""Relevance Gate — deterministic user-state filtering of proactive actions.

Evaluates each applicable action against the user's current state (mode,
explicit suppressions) and returns blocked actions with reasons. This is
Step 3 of the SAF pipeline.

This module never calls an LLM and never reads domain content.
"""

from typing import Dict, List

from skills.saf_core.lib import paths
from skills.saf_core.lib.context import ProactiveAction
from skills.saf_core.lib.fs import load_json


def load_user_state(workspace_root=None):
    """Load relevance-specific fields from user-state.json.

    Returns only the fields the relevance gate cares about, with defaults
    for missing keys. Does NOT return temporal fields (timezone, phases,
    work_days) — those are handled by temporal.load_user_state().
    """
    path = paths.resolve(paths.USER_STATE_FILE, workspace_root)
    state = load_json(path, default={})
    return {
        "mode": state.get("mode", "normal"),
        "suppressed_actions": state.get("suppressed_actions", []),
    }


def check_relevance(
    applicable: List[ProactiveAction],
    action_defs: dict,
    workspace_root: str = None,
) -> Dict[str, str]:
    """Evaluate relevance rules for applicable actions.

    Returns a dict mapping blocked action_id to reason string.
    """
    user_state = load_user_state(workspace_root)
    blocked = {}
    current_mode = user_state["mode"]
    suppressed = set(user_state["suppressed_actions"])

    for action in applicable:
        if action.id in suppressed:
            blocked[action.id] = "suppressed_by_user"
            continue

        skip_modes = action_defs.get(action.id, {}).get("skip_modes", [])
        if current_mode in skip_modes:
            blocked[action.id] = f"blocked_by_mode:{current_mode}"
            continue

    return blocked
