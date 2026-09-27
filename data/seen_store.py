# 数据层：记住上次已推送的重置位置。没有记录表示还没建立基线。

import asyncio
from pathlib import Path

from .._shared.db import connect, create_table
from ..entity.record import SeenState

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS seen_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_seen_id TEXT NOT NULL,
    last_announced_at TEXT NOT NULL,
    last_reset_at TEXT NOT NULL
)
"""


class SeenStore:
    """全局一行已见状态。轮询热路径读内存。"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._seen: SeenState | None = None
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()
        self._load_snapshot()

    def _setup(self) -> None:
        """首次启动建表。"""
        conn = connect(self.db_path)
        try:
            create_table(conn, CREATE_TABLE_SQL)
        finally:
            conn.close()

    def _load_snapshot(self) -> None:
        """把唯一一行读进内存。没有行就保持未基线。"""
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT last_seen_id, last_announced_at, last_reset_at FROM seen_state WHERE id = 1"
            ).fetchone()
        finally:
            conn.close()
        # 还没轮询成功过，不能把历史重置当成新重置
        if row is None:
            self._seen = None
            return
        self._seen = SeenState(str(row[0]), str(row[1]), str(row[2]))

    def get(self) -> SeenState | None:
        """当前已见位置。None 表示还没建立基线。"""
        return self._seen

    async def save(self, seen: SeenState) -> None:
        """先落库再改内存。落库失败时内存保持旧值。"""
        async with self._lock:
            await asyncio.to_thread(self._save_sync, seen)
        self._seen = seen

    def _save_sync(self, seen: SeenState) -> None:
        """用固定 id=1 保证全局只有一行。"""
        conn = connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO seen_state(id, last_seen_id, last_announced_at, last_reset_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    last_seen_id = excluded.last_seen_id,
                    last_announced_at = excluded.last_announced_at,
                    last_reset_at = excluded.last_reset_at
                """,
                (seen.last_seen_id, seen.last_announced_at, seen.last_reset_at),
            )
            conn.commit()
        finally:
            conn.close()
