# 测试：重置判定。用已观察到的字段形状，不连真实接口。

import unittest

from astrbot_plugin_codex_reset.business.judge import is_announced_reset, plan_updates
from astrbot_plugin_codex_reset.entity.record import ForecastSnapshot, SeenState, TimelineEvent


def event(event_id, group="reset", state="announced", announced_at="2026-09-26T18:17:54.000Z"):
    """造一条和 /api/timeline 字段对应的事件。"""
    return TimelineEvent(event_id, group, state, "Resets all propagated.", "https://x.com/example", announced_at)


class JudgeTest(unittest.TestCase):
    """已宣布重置、基线和预测前移。"""

    def test_missing_state_is_not_reset(self):
        """缺 announcement_state 不算重置。"""
        raw = event("1", state="")
        self.assertFalse(is_announced_reset(raw))

    def test_other_group_is_not_reset(self):
        """credits 即使写了 announced 也不算重置。"""
        raw = event("1", group="credits")
        self.assertFalse(is_announced_reset(raw))

    def test_first_plan_does_not_push_history(self):
        """第一次只记基线，不把已有宣布推出去。"""
        forecast = ForecastSnapshot("2026-09-26T18:17:54.000Z", 12, 20)
        plan = plan_updates([event("2103911959544610829")], forecast, None)
        self.assertEqual(plan.messages, [])
        self.assertTrue(plan.should_save)
        self.assertEqual(plan.next_seen.last_seen_id, "2103911959544610829")

    def test_new_announced_reset_is_pushed_once(self):
        """比已见位置新的已宣布重置要推，并带署名。"""
        seen = SeenState("1", "2026-09-26T18:17:54.000Z", "2026-09-26T18:17:54.000Z")
        newer = event("2", announced_at="2026-09-27T01:00:00.000Z")
        forecast = ForecastSnapshot("2026-09-27T01:00:00.000Z", 80, 90)
        plan = plan_updates([newer, event("1")], forecast, seen)
        self.assertEqual(len(plan.messages), 1)
        self.assertIn("Data: codex-reset.com", plan.messages[0])
        self.assertIn("https://codex-reset.com", plan.messages[0])
        self.assertEqual(plan.next_seen.last_seen_id, "2")

    def test_same_event_is_not_pushed_again(self):
        """同一条已见事件再出现，不推。"""
        seen = SeenState("2", "2026-09-27T01:00:00.000Z", "2026-09-27T01:00:00.000Z")
        forecast = ForecastSnapshot("2026-09-27T01:00:00.000Z", 90, 95)
        plan = plan_updates([event("2", announced_at="2026-09-27T01:00:00.000Z")], forecast, seen)
        self.assertEqual(plan.messages, [])
        self.assertFalse(plan.should_save)

    def test_probability_rise_is_not_reset(self):
        """last_reset_at 没动时，概率升高不产生文案。"""
        seen = SeenState("2", "2026-09-27T01:00:00.000Z", "2026-09-27T01:00:00.000Z")
        forecast = ForecastSnapshot("2026-09-27T01:00:00.000Z", 99, 99)
        plan = plan_updates([event("2", announced_at="2026-09-27T01:00:00.000Z")], forecast, seen)
        self.assertEqual(plan.messages, [])

    def test_forecast_move_without_event_is_pushed(self):
        """时间没变的事件列表里，last_reset_at 前移仍要推一条。"""
        seen = SeenState("2", "2026-09-27T01:00:00.000Z", "2026-09-27T01:00:00.000Z")
        forecast = ForecastSnapshot("2026-09-27T03:00:00.000Z", 10, 10)
        plan = plan_updates([event("2", announced_at="2026-09-27T01:00:00.000Z")], forecast, seen)
        self.assertEqual(len(plan.messages), 1)
        self.assertIn("已前移", plan.messages[0])
        self.assertEqual(plan.next_seen.last_reset_at, "2026-09-27T03:00:00.000Z")


if __name__ == "__main__":
    unittest.main()
