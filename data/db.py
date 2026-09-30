# 数据层：本插件 SQLite 怎么连、怎么建表。
# 表结构和业务 SQL 留在各自的 data/*_store.py 里。

import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    """打开 SQLite。WAL 让页面保存和轮询写入不容易互相堵住。"""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def create_table(conn: sqlite3.Connection, create_sql: str) -> None:
    """建表。表已存在就跳过，建完立刻提交。"""
    conn.execute(create_sql)
    conn.commit()
