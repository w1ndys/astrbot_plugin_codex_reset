# 测试：已见位置落库后，新进程还能读到，避免重启重复推。

import asyncio
import tempfile
import unittest
from pathlib import Path

from astrbot_plugin_codex_reset.data.seen_store import SeenStore
from astrbot_plugin_codex_reset.entity.record import SeenState


class SeenStoreTest(unittest.TestCase):
    """last_seen_id 持久化。"""

    def test_save_survives_new_store(self):
        """写入后重新打开库，读到同一位置。"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "codex_reset.db"
            store = SeenStore(db_path)
            self.assertIsNone(store.get())
            asyncio.run(
                store.save(
                    SeenState(
                        "2103911959544610829",
                        "2026-09-26T18:17:54.000Z",
                        "2026-09-26T18:17:54.000Z",
                    )
                )
            )
            again = SeenStore(db_path)
            seen = again.get()
            self.assertEqual(seen.last_seen_id, "2103911959544610829")
            self.assertEqual(seen.last_reset_at, "2026-09-26T18:17:54.000Z")


if __name__ == "__main__":
    unittest.main()
