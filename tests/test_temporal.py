import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from skills.saf_core.lib.domains import DEFAULT_PHASES, DEFAULT_WORK_DAYS
from skills.saf_core.lib.temporal import (
    _resolve_phase,
    get_temporal_context,
    load_user_state,
)


def _utc(year, month, day, hour, minute=0):
    """Helper to create a UTC datetime for test injection."""
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@contextmanager
def _patched_user_state(state_dict):
    """Writes a temporary user-state.json and patches USER_STATE_PATH to point to it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "user-state.json")
        with open(config_path, 'w') as f:
            json.dump(state_dict, f)
        with patch("skills.saf_core.lib.temporal.USER_STATE_PATH", config_path):
            yield


class TestPhaseDetection(unittest.TestCase):
    """Verifies phase boundaries map correctly for default and custom phase configs."""

    def test_night_before_dawn(self):
        self.assertEqual(_resolve_phase(3, DEFAULT_PHASES), "NIGHT")

    def test_night_upper_boundary(self):
        self.assertEqual(_resolve_phase(5, DEFAULT_PHASES), "NIGHT")

    def test_morning_lower_boundary(self):
        self.assertEqual(_resolve_phase(6, DEFAULT_PHASES), "MORNING")

    def test_morning_upper_boundary(self):
        self.assertEqual(_resolve_phase(11, DEFAULT_PHASES), "MORNING")

    def test_afternoon_lower_boundary(self):
        self.assertEqual(_resolve_phase(12, DEFAULT_PHASES), "AFTERNOON")

    def test_afternoon_upper_boundary(self):
        self.assertEqual(_resolve_phase(16, DEFAULT_PHASES), "AFTERNOON")

    def test_evening_lower_boundary(self):
        self.assertEqual(_resolve_phase(17, DEFAULT_PHASES), "EVENING")

    def test_evening_upper_boundary(self):
        self.assertEqual(_resolve_phase(20, DEFAULT_PHASES), "EVENING")

    def test_night_late_lower_boundary(self):
        self.assertEqual(_resolve_phase(21, DEFAULT_PHASES), "NIGHT_LATE")

    def test_night_late_upper_boundary(self):
        self.assertEqual(_resolve_phase(23, DEFAULT_PHASES), "NIGHT_LATE")

    def test_midnight_is_night(self):
        self.assertEqual(_resolve_phase(0, DEFAULT_PHASES), "NIGHT")

    def test_custom_wrap_around_phases(self):
        # Night-shift worker: "morning" starts at 18:00, wraps past midnight
        custom = {"SLEEP": [6, 18], "ACTIVE": [18, 6]}
        self.assertEqual(_resolve_phase(10, custom), "SLEEP")
        self.assertEqual(_resolve_phase(20, custom), "ACTIVE")
        self.assertEqual(_resolve_phase(2, custom), "ACTIVE")


class TestDayType(unittest.TestCase):
    """Verifies workday vs rest_day detection with default and custom configs."""

    def test_monday_is_workday(self):
        ctx = get_temporal_context(_now_override=_utc(2026, 4, 6, 10))
        self.assertEqual(ctx["day_type"], "workday")

    def test_saturday_is_rest_day(self):
        ctx = get_temporal_context(_now_override=_utc(2026, 4, 4, 10))
        self.assertEqual(ctx["day_type"], "rest_day")

    def test_sunday_is_rest_day(self):
        ctx = get_temporal_context(_now_override=_utc(2026, 4, 5, 10))
        self.assertEqual(ctx["day_type"], "rest_day")

    def test_custom_work_days_sunday_through_thursday(self):
        custom_state = {
            "timezone": "UTC",
            "work_days": [6, 0, 1, 2, 3],
            "phases": DEFAULT_PHASES,
        }
        with _patched_user_state(custom_state):
            # Saturday (weekday=5) → rest_day
            ctx = get_temporal_context(_now_override=_utc(2026, 4, 4, 10))
            self.assertEqual(ctx["day_type"], "rest_day")
            # Sunday (weekday=6) → workday
            ctx = get_temporal_context(_now_override=_utc(2026, 4, 5, 10))
            self.assertEqual(ctx["day_type"], "workday")


class TestTimezoneConversion(unittest.TestCase):
    """Verifies UTC-to-local conversion produces correct hours and dates."""

    def test_utc_to_berlin_summer(self):
        with _patched_user_state({"timezone": "Europe/Berlin"}):
            ctx = get_temporal_context(_now_override=_utc(2026, 7, 15, 14, 0))
        self.assertEqual(ctx["hour"], 16)
        self.assertEqual(ctx["timezone"], "Europe/Berlin")

    def test_utc_to_tokyo(self):
        with _patched_user_state({"timezone": "Asia/Tokyo"}):
            ctx = get_temporal_context(_now_override=_utc(2026, 1, 10, 23, 0))
        # 23:00 UTC = 08:00 next day in Tokyo (UTC+9)
        self.assertEqual(ctx["hour"], 8)
        self.assertEqual(ctx["iso_date"], "2026-01-11")

    def test_date_rolls_over_with_positive_offset(self):
        with _patched_user_state({"timezone": "Asia/Tokyo"}):
            ctx = get_temporal_context(_now_override=_utc(2026, 1, 10, 23, 30))
        self.assertEqual(ctx["iso_date"], "2026-01-11")
        self.assertEqual(ctx["day_of_week"], "Sunday")


class TestConfigLoading(unittest.TestCase):
    """Verifies config loading with present, missing, and partial configs."""

    def test_missing_config_uses_defaults(self):
        with patch("skills.saf_core.lib.temporal.USER_STATE_PATH", "/nonexistent/path.json"):
            state = load_user_state()
        self.assertEqual(state["timezone"], "UTC")
        self.assertEqual(state["work_days"], DEFAULT_WORK_DAYS)
        self.assertEqual(state["phases"], DEFAULT_PHASES)

    def test_partial_config_fills_defaults(self):
        with _patched_user_state({"timezone": "US/Eastern"}):
            state = load_user_state()
        self.assertEqual(state["timezone"], "US/Eastern")
        self.assertEqual(state["work_days"], DEFAULT_WORK_DAYS)
        self.assertEqual(state["phases"], DEFAULT_PHASES)

    def test_full_config_overrides_all(self):
        custom = {
            "timezone": "Pacific/Auckland",
            "work_days": [0, 1, 2, 3],
            "phases": {"DAY": [6, 18], "NIGHT": [18, 6]},
        }
        with _patched_user_state(custom):
            state = load_user_state()
        self.assertEqual(state["timezone"], "Pacific/Auckland")
        self.assertEqual(state["work_days"], [0, 1, 2, 3])
        self.assertEqual(state["phases"], {"DAY": [6, 18], "NIGHT": [18, 6]})

    def test_defaults_not_mutated_by_caller(self):
        with patch("skills.saf_core.lib.temporal.USER_STATE_PATH", "/nonexistent/path.json"):
            state = load_user_state()
        state["work_days"].append(99)
        state["phases"]["CUSTOM"] = [0, 24]
        # Load again — defaults should be unaffected
        with patch("skills.saf_core.lib.temporal.USER_STATE_PATH", "/nonexistent/path.json"):
            fresh = load_user_state()
        self.assertNotIn(99, fresh["work_days"])
        self.assertNotIn("CUSTOM", fresh["phases"])


class TestAntiSimulation(unittest.TestCase):
    """Verifies the gate uses the real system clock when no override is given."""

    def test_real_clock_produces_current_time(self):
        ctx = get_temporal_context()
        utc_now = datetime.now(timezone.utc)
        returned = datetime.fromisoformat(ctx["utc_time"])
        delta = abs((utc_now - returned).total_seconds())
        self.assertLess(delta, 2.0)

    def test_override_does_not_use_real_clock(self):
        fixed = _utc(2020, 6, 15, 3, 0)
        ctx = get_temporal_context(_now_override=fixed)
        self.assertTrue(ctx["utc_time"].startswith("2020-06-15"))
        self.assertEqual(ctx["day_phase"], "NIGHT")


if __name__ == '__main__':
    unittest.main()
