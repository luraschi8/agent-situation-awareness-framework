"""Tests for saf_core.lib.relevance — the Relevance Gate."""

import json
import os
import shutil
import tempfile
import unittest

from skills.saf_core.lib.context import ProactiveAction
from skills.saf_core.lib import relevance


def _action(action_id, domains=None, frequency="daily"):
    return ProactiveAction(
        id=action_id,
        description=f"Test action {action_id}",
        domains=domains or [],
        frequency=frequency,
    )


class _WorkspaceFixture(unittest.TestCase):
    """Base providing a temp workspace with helpers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "memory", "shared"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write_user_state(self, data):
        path = os.path.join(self.tmpdir, "memory", "shared", "user-state.json")
        with open(path, "w") as f:
            json.dump(data, f)


class TestLoadUserState(_WorkspaceFixture):
    """Tests for relevance.load_user_state()."""

    def test_defaults_when_no_file(self):
        state = relevance.load_user_state(self.tmpdir)
        self.assertEqual(state["mode"], "normal")
        self.assertEqual(state["suppressed_actions"], [])

    def test_reads_mode_from_file(self):
        self.write_user_state({"mode": "vacation"})
        state = relevance.load_user_state(self.tmpdir)
        self.assertEqual(state["mode"], "vacation")

    def test_reads_suppressed_actions(self):
        self.write_user_state({"suppressed_actions": ["morning_briefing"]})
        state = relevance.load_user_state(self.tmpdir)
        self.assertEqual(state["suppressed_actions"], ["morning_briefing"])

    def test_ignores_temporal_fields(self):
        self.write_user_state({
            "timezone": "Europe/Berlin",
            "work_days": [0, 1, 2, 3, 4],
            "mode": "focus",
        })
        state = relevance.load_user_state(self.tmpdir)
        self.assertNotIn("timezone", state)
        self.assertNotIn("work_days", state)
        self.assertEqual(state["mode"], "focus")


class TestCheckRelevance(_WorkspaceFixture):
    """Tests for relevance.check_relevance()."""

    def test_normal_mode_blocks_nothing(self):
        self.write_user_state({"mode": "normal"})
        actions = [_action("morning_briefing"), _action("weekly_review")]
        defs = {
            "morning_briefing": {"skip_modes": ["vacation"]},
            "weekly_review": {"skip_modes": ["vacation"]},
        }
        blocked = relevance.check_relevance(actions, defs, self.tmpdir)
        self.assertEqual(blocked, {})

    def test_mode_blocks_matching_action(self):
        self.write_user_state({"mode": "vacation"})
        actions = [_action("morning_briefing")]
        defs = {"morning_briefing": {"skip_modes": ["vacation", "dnd"]}}
        blocked = relevance.check_relevance(actions, defs, self.tmpdir)
        self.assertIn("morning_briefing", blocked)
        self.assertEqual(blocked["morning_briefing"], "blocked_by_mode:vacation")

    def test_mode_passes_non_matching_action(self):
        self.write_user_state({"mode": "vacation"})
        actions = [_action("morning_briefing")]
        defs = {"morning_briefing": {"skip_modes": ["focus"]}}
        blocked = relevance.check_relevance(actions, defs, self.tmpdir)
        self.assertEqual(blocked, {})

    def test_suppressed_action_blocked(self):
        self.write_user_state({"suppressed_actions": ["weekly_review"]})
        actions = [_action("weekly_review")]
        defs = {"weekly_review": {}}
        blocked = relevance.check_relevance(actions, defs, self.tmpdir)
        self.assertIn("weekly_review", blocked)
        self.assertEqual(blocked["weekly_review"], "suppressed_by_user")

    def test_suppression_takes_priority_over_mode(self):
        self.write_user_state({
            "mode": "vacation",
            "suppressed_actions": ["morning_briefing"],
        })
        actions = [_action("morning_briefing")]
        defs = {"morning_briefing": {"skip_modes": ["vacation"]}}
        blocked = relevance.check_relevance(actions, defs, self.tmpdir)
        self.assertEqual(blocked["morning_briefing"], "suppressed_by_user")

    def test_missing_skip_modes_defaults_to_empty(self):
        self.write_user_state({"mode": "vacation"})
        actions = [_action("morning_briefing")]
        defs = {"morning_briefing": {"description": "no skip_modes key"}}
        blocked = relevance.check_relevance(actions, defs, self.tmpdir)
        self.assertEqual(blocked, {})

    def test_empty_applicable_list(self):
        self.write_user_state({"mode": "vacation"})
        blocked = relevance.check_relevance([], {}, self.tmpdir)
        self.assertEqual(blocked, {})

    def test_mixed_blocked_and_available(self):
        self.write_user_state({"mode": "dnd"})
        actions = [_action("morning_briefing"), _action("weekly_review")]
        defs = {
            "morning_briefing": {"skip_modes": ["dnd", "vacation"]},
            "weekly_review": {"skip_modes": ["vacation"]},
        }
        blocked = relevance.check_relevance(actions, defs, self.tmpdir)
        self.assertIn("morning_briefing", blocked)
        self.assertNotIn("weekly_review", blocked)


if __name__ == "__main__":
    unittest.main()
