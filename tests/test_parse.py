# 测试：按真实响应里见过的字段解析，并检查等待下限。

import unittest

from astrbot_plugin_codex_reset.business.wait import next_wait
from astrbot_plugin_codex_reset.data.client import read_max_age, read_retry_after
from astrbot_plugin_codex_reset.data.parse import parse_events, parse_forecast


class ParseTest(unittest.TestCase):
    """时间线和预测的字段映射。"""

    def test_parse_observed_reset_event(self):
        """已观察到的已宣布 reset 能读出判定要用的字段。"""
        body = {
            "events": [
                {
                    "id": "2103911959544610829",
                    "group": "reset",
                    "summary": "Resets all propagated. That will be all. Have a fantastic weekend.",
                    "url": "https://x.com/thsottiaux/status/2103911959544610829",
                    "announced_at": "2026-09-26T18:17:54.000Z",
                    "announcement_state": "announced",
                }
            ]
        }
        events = parse_events(body)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_id, "2103911959544610829")
        self.assertEqual(events[0].announcement_state, "announced")

    def test_missing_state_becomes_empty(self):
        """接口没给 announcement_state 时收成空串，不当成已宣布。"""
        events = parse_events({"events": [{"id": "1", "group": "reset"}]})
        self.assertEqual(events[0].announcement_state, "")

    def test_forecast_last_reset_at(self):
        """预测只取 last_reset_at 和展示用概率。"""
        snapshot = parse_forecast(
            {
                "last_reset_at": "2026-09-26T18:17:54.000Z",
                "probabilities": {"rounded_24h": 12, "rounded_48h": 20},
            }
        )
        self.assertEqual(snapshot.last_reset_at, "2026-09-26T18:17:54.000Z")
        self.assertEqual(snapshot.rounded_24h, 12)

    def test_wait_respects_floor_and_retry_after(self):
        """配置再小也不能快于 60，429 更长时听 Retry-After。"""
        self.assertEqual(next_wait(1, 0, 0), 60)
        self.assertEqual(next_wait(60, 60, 0), 60)
        self.assertEqual(next_wait(60, 60, 120), 120)
        self.assertEqual(read_max_age("public, max-age=60"), 60)
        self.assertEqual(read_retry_after("90"), 90)


if __name__ == "__main__":
    unittest.main()
