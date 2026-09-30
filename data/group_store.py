# 数据层：WebUI 维护的开启群。表里没有的群就是关，默认不推送。

import asyncio
from pathlib import Path

from ..entity.record import GroupRow
from .db import connect, create_table

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS monitor_group (
    group_id TEXT PRIMARY KEY,
    remark TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    umo TEXT NOT NULL
)
"""


class GroupStore:
    """开启群表。页面读写走库，记会话时先落库再改内存。"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._rows: dict[str, GroupRow] = {}
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
        """启动时把群表读进内存，热路径不再查库。"""
        conn = connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT group_id, remark, enabled, umo FROM monitor_group"
            ).fetchall()
        finally:
            conn.close()
        loaded = {}
        for row in rows:
            loaded[str(row[0])] = GroupRow(str(row[0]), str(row[1]), bool(row[2]), str(row[3]))
        self._rows = loaded

    def get(self, group_id: str) -> GroupRow | None:
        """按群号取一行。没有就是没配置。"""
        return self._rows.get(group_id)

    def list_rows(self) -> list:
        """按群号排序列出全部行，给页面和推送用。"""
        keys = sorted(self._rows.keys())
        rows = []
        for key in keys:
            rows.append(self._rows[key])
        return rows

    async def insert(self, row: GroupRow) -> None:
        """新增一行。调用方要先确认群号不存在。"""
        async with self._lock:
            await asyncio.to_thread(self._insert_sync, row)
        self._rows[row.group_id] = row

    async def save(self, row: GroupRow) -> None:
        """改备注、开关或会话。群号必须已经在表里。"""
        async with self._lock:
            await asyncio.to_thread(self._save_sync, row)
        self._rows[row.group_id] = row

    async def delete(self, group_id: str) -> None:
        """删掉一行。删掉后这个群不再推送。"""
        async with self._lock:
            await asyncio.to_thread(self._delete_sync, group_id)
        self._rows.pop(group_id, None)

    def _insert_sync(self, row: GroupRow) -> None:
        """同步插入。重复群号会抛错，事务回滚，内存不动。"""
        conn = connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO monitor_group(group_id, remark, enabled, umo) VALUES (?, ?, ?, ?)",
                (row.group_id, row.remark, 1 if row.enabled else 0, row.umo),
            )
            conn.commit()
        finally:
            conn.close()

    def _save_sync(self, row: GroupRow) -> None:
        """同步更新已有行。"""
        conn = connect(self.db_path)
        try:
            conn.execute(
                "UPDATE monitor_group SET remark = ?, enabled = ?, umo = ? WHERE group_id = ?",
                (row.remark, 1 if row.enabled else 0, row.umo, row.group_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_sync(self, group_id: str) -> None:
        """同步删除。"""
        conn = connect(self.db_path)
        try:
            conn.execute("DELETE FROM monitor_group WHERE group_id = ?", (group_id,))
            conn.commit()
        finally:
            conn.close()
