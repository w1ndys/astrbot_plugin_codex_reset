# 测试：WebUI 群数据的校验、默认关和推送目标。

import asyncio
import tempfile
import unittest
from pathlib import Path

from astrbot_plugin_codex_reset.business.groups import (
    add_group,
    build_umo,
    delete_group,
    push_targets,
    session_umo,
    stored_enabled,
    switch_notice_text,
    update_group,
)
from astrbot_plugin_codex_reset.data.group_store import GroupStore
from astrbot_plugin_codex_reset.entity.record import GroupRow


class GroupTest(unittest.TestCase):
    """群号校验和推送目标。"""

    def setUp(self):
        """每个用例用一块临时库，避免互相污染。"""
        self.tmp = tempfile.TemporaryDirectory()
        self.store = GroupStore(Path(self.tmp.name) / "codex_reset.db")

    def tearDown(self):
        """关掉临时目录。"""
        self.tmp.cleanup()

    def test_empty_store_has_no_targets(self):
        """没记录就等于关，没有推送目标。"""
        self.assertEqual(push_targets(self.store.list_rows(), "napcat"), [])

    def test_reject_non_digit_group_id(self):
        """非数字群号不入库。"""
        result = asyncio.run(add_group(self.store, "abc", "", True))
        self.assertEqual(result.error, "群号只能是数字")
        self.assertEqual(self.store.list_rows(), [])

    def test_add_and_disable(self):
        """新增后默认能按平台 ID 推送；关掉后不再推。"""
        added = asyncio.run(add_group(self.store, "123456", "测试群", True))
        self.assertEqual(added.error, "")
        targets = push_targets(self.store.list_rows(), "napcat")
        self.assertEqual(targets, [("123456", "napcat:GroupMessage:123456")])
        updated = asyncio.run(update_group(self.store, "123456", "测试群", False))
        self.assertEqual(updated.error, "")
        self.assertEqual(push_targets(self.store.list_rows(), "napcat"), [])

    def test_duplicate_add_does_not_overwrite(self):
        """重复添加不覆盖已记下的会话。"""
        asyncio.run(add_group(self.store, "123456", "", True))
        asyncio.run(self.store.save(GroupRow("123456", "", True, "napcat:GroupMessage:123456")))
        again = asyncio.run(add_group(self.store, "123456", "新备注", True))
        self.assertEqual(again.error, "这个群已经在列表里")
        self.assertEqual(self.store.get("123456").umo, "napcat:GroupMessage:123456")

    def test_delete_removes_target(self):
        """删除后不再推送。"""
        asyncio.run(add_group(self.store, "123456", "", True))
        deleted = asyncio.run(delete_group(self.store, "123456"))
        self.assertEqual(deleted.error, "")
        self.assertIsNone(self.store.get("123456"))

    def test_platform_id_with_colon_is_not_used(self):
        """平台 ID 含冒号时不拼会话，避免拆错。"""
        self.assertEqual(build_umo("bad:id", "123456"), "")


    def test_enable_notice_only_on_change(self):
        """从关到开有开启文案，再保存同一开关不再发。"""
        self.assertIn("已开启", switch_notice_text(False, True))
        self.assertIn("已关闭", switch_notice_text(True, False))
        self.assertEqual(switch_notice_text(True, True), "")

    def test_closed_group_still_has_session_for_notice(self):
        """关掉之后仍能定位会话，否则关闭通知发不出去。"""
        row = GroupRow("123456", "", False, "")
        self.assertEqual(session_umo(row, "napcat"), "napcat:GroupMessage:123456")
        self.assertFalse(stored_enabled(self.store, "123456"))


if __name__ == "__main__":
    unittest.main()
