#!/usr/bin/env python3
"""SAF pipeline smoke test — validates end-to-end without OpenClaw.

Simulates a full agent session lifecycle:
  Turn 0: Bootstrap (empty message)
  Turn 1: Message with domain routing ("I have a meeting tomorrow")
  Turn 2: Agent executes morning_briefing → ledger write → dedup verified
  Turn 3: Vacation mode → relevance gate blocks actions
  Final:  Workspace validation

Usage:
    python3 scripts/smoke_test.py

Creates a temp workspace, runs the pipeline, prints briefings, and
verifies dedup/routing/relevance. No OpenClaw or agent runtime needed.
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

# Ensure imports work from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.saf_core.lib import actions, pipeline
from skills.saf_core.lib.context import SAFContext
from skills.saf_core.lib.domains import (
    ARCHETYPE_ACTIONS,
    ARCHETYPE_KEYWORDS,
    DEFAULT_PHASES,
    DEFAULT_WORK_DAYS,
)
from skills.saf_core.lib.fs import save_json
from skills.saf_core.lib.host import SAFHost
from skills.saf_core.lib.self_review import validate_workspace
from skills.saf_openclaw.renderer import render_briefing


# Fixed to Monday 8am so trigger conditions (phase=MORNING, day_of_week=0)
# are always satisfied regardless of when the smoke test runs.
_FIXED_MONDAY_MORNING = {
    "utc_time": "2026-04-06T08:00:00+00:00",
    "timezone": "UTC",
    "local_time": "2026-04-06T08:00:00+00:00",
    "hour": 8,
    "day_phase": "MORNING",
    "day_of_week": "Monday",
    "day_type": "workday",
    "iso_date": "2026-04-06",
    "weekday_number": 0,
}


def _monday_morning():
    """Patch temporal context to a fixed Monday morning."""
    return patch(
        "skills.saf_core.lib.temporal.get_temporal_context",
        return_value=_FIXED_MONDAY_MORNING,
    )


class SmokeHost:
    """Minimal SAFHost for the smoke test."""

    def __init__(self, workspace_root):
        self._root = workspace_root

    def workspace_root(self):
        return self._root

    def log(self, level, message):
        print(f"  [{level}] {message}")


passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        print(f"  PASS  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}")
        failed += 1


def setup_workspace(tmpdir):
    """Create a realistic SAF workspace programmatically."""
    shared = os.path.join(tmpdir, "memory", "shared")
    runtime = os.path.join(shared, "runtime")
    os.makedirs(runtime, exist_ok=True)

    # User state
    save_json(os.path.join(shared, "user-state.json"), {
        "timezone": "UTC",
        "work_days": DEFAULT_WORK_DAYS,
        "phases": DEFAULT_PHASES,
    })

    # Router config
    save_json(
        os.path.join(shared, "router-config.json"),
        ARCHETYPE_KEYWORDS["professional"],
    )

    # Proactive actions
    save_json(os.path.join(shared, "proactive-actions.json"), {
        "actions": ARCHETYPE_ACTIONS["professional"],
    })

    # Domain directories with sample content
    for domain_name in ("work", "projects", "infrastructure"):
        domain_dir = os.path.join(tmpdir, "memory", "domains", domain_name)
        os.makedirs(domain_dir, exist_ok=True)
        with open(os.path.join(domain_dir, "setup.md"), "w") as f:
            f.write(f"# {domain_name.title()} Domain\n\nSample content.\n")

    # _system domain
    system_dir = os.path.join(tmpdir, "memory", "domains", "_system")
    os.makedirs(system_dir, exist_ok=True)
    with open(os.path.join(system_dir, "review-queue.md"), "w") as f:
        f.write("# Review Queue\n\n_No pending items._\n")

    return tmpdir


def main():
    global passed, failed
    tmpdir = tempfile.mkdtemp(prefix="saf_smoke_")
    host = SmokeHost(setup_workspace(tmpdir))

    try:
        print("=" * 60)
        print("SAF Pipeline Smoke Test")
        print("=" * 60)
        print(f"Workspace: {tmpdir}\n")

        # ---- Turn 0: Bootstrap ----
        print("--- Turn 0: Bootstrap (empty message) ---")
        print("  (Temporal fixed to Monday 2026-04-06 08:00 UTC)\n")
        with _monday_morning():
            ctx = pipeline.process("", host)
        briefing = render_briefing(ctx)

        check("Returns SAFContext", isinstance(ctx, SAFContext))
        check("Temporal has day_phase", "day_phase" in ctx.temporal)
        check("Temporal has iso_date", "iso_date" in ctx.temporal)
        # Actions with domains (e.g., knowledge_audit → _system) may inject
        # domains even on bootstrap, but no MESSAGE-matched domains expected.
        check("Briefing generated successfully", len(briefing) > 0)
        check("Briefing contains temporal section", "## 1. Temporal Context" in briefing)

        print(f"\n  Briefing preview ({len(briefing)} chars):")
        for line in briefing.split("\n")[:8]:
            print(f"    {line}")
        print("    ...\n")

        # ---- Turn 1: Message with domain routing ----
        print("--- Turn 1: Domain routing ('I have a meeting tomorrow') ---")
        with _monday_morning():
            ctx = pipeline.process("I have a meeting tomorrow", host)
        briefing = render_briefing(ctx)

        domain_names = [c.name for c in ctx.candidate_domains]
        check("'work' domain routed", "work" in domain_names)
        check("Domain has files", len(ctx.candidate_domains[0].files) > 0 if ctx.candidate_domains else False)
        check("Available actions present", len(ctx.available_actions) > 0)
        check("Briefing mentions 'work'", "work" in briefing)

        action_ids = [a.id for a in ctx.available_actions]
        print(f"  Available actions: {action_ids}")
        print(f"  Routed domains: {domain_names}\n")

        # ---- Turn 2: Agent executes action → dedup ----
        print("--- Turn 2: Execute morning_briefing → verify dedup ---")

        # Simulate: agent responded with an action tag.
        # Patch time.gmtime so the ledger timestamp matches our fixed date.
        import time as _time
        _fixed_struct = _time.strptime("2026-04-06T08:05:00", "%Y-%m-%dT%H:%M:%S")
        with patch("time.gmtime", return_value=_fixed_struct):
            pipeline.record_action("morning_briefing", "sent", host)
        print("  Recorded: morning_briefing → sent (at 2026-04-06T08:05:00Z)")

        # Next pipeline run should block it
        with _monday_morning():
            ctx = pipeline.process("Good morning", host)
        check("morning_briefing is blocked", "morning_briefing" in ctx.blocked_actions)
        check(
            "Block reason is dedup",
            ctx.blocked_actions.get("morning_briefing", "").startswith("already_done"),
        )
        check(
            "morning_briefing NOT in available",
            all(a.id != "morning_briefing" for a in ctx.available_actions),
        )
        print(f"  Blocked actions: {ctx.blocked_actions}\n")

        # ---- Turn 3: Relevance gate — vacation mode ----
        print("--- Turn 3: Set vacation mode → verify relevance gate ---")

        save_json(
            os.path.join(tmpdir, "memory", "shared", "user-state.json"),
            {
                "timezone": "UTC",
                "work_days": DEFAULT_WORK_DAYS,
                "phases": DEFAULT_PHASES,
                "mode": "vacation",
            },
        )
        print("  Set mode: vacation")

        with _monday_morning():
            ctx = pipeline.process("Any updates?", host)

        # Actions with skip_modes=["vacation"] should be blocked
        vacation_blocked = [
            aid for aid, reason in ctx.blocked_actions.items()
            if "vacation" in reason
        ]
        check("At least one action blocked by vacation mode", len(vacation_blocked) > 0)
        print(f"  Vacation-blocked: {vacation_blocked}")
        print(f"  All blocked: {ctx.blocked_actions}\n")

        # ---- Validation ----
        print("--- Validation: workspace config integrity ---")
        result = validate_workspace(tmpdir)
        check("Workspace is valid", result.valid)
        if result.errors:
            for e in result.errors:
                print(f"  ERROR: {e}")
        if result.warnings:
            for w in result.warnings:
                print(f"  WARNING: {w}")

        # ---- Summary ----
        print("\n" + "=" * 60)
        total = passed + failed
        print(f"Results: {passed}/{total} passed, {failed} failed")
        if failed == 0:
            print("ALL CHECKS PASSED")
        else:
            print("SOME CHECKS FAILED")
        print("=" * 60)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
