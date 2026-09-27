# 业务层：一轮轮询。拉数据、判定、落已见位置。不直接发消息。

from datetime import datetime, timezone

from ..data.seen_store import SeenStore
from ..entity.record import MonitorStatus
from .judge import plan_updates
from .wait import next_wait


def now_text() -> str:
    """当前 UTC 时间，给页面看最近一轮是什么时候。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def run_once(client: object, seen_store: SeenStore, status: MonitorStatus, poll_seconds: int) -> tuple:
    """拉一轮并返回要推的文案和等待秒数。失败不改已见位置。"""
    loaded = await client.load()
    polled_at = now_text()
    # 来源失败时不推进 last_seen，下一轮还能补推
    if loaded.error:
        status.note_error(polled_at, loaded.error)
        return [], next_wait(poll_seconds, loaded.cache_max_age, loaded.retry_after)
    plan = plan_updates(loaded.events or [], loaded.forecast, seen_store.get())
    # 基线或新位置都要先落库，避免重启后重复推
    if plan.should_save and plan.next_seen is not None:
        await seen_store.save(plan.next_seen)
    status.note_ok(polled_at, len(plan.messages))
    return plan.messages, next_wait(poll_seconds, loaded.cache_max_age, loaded.retry_after)


def status_payload(seen_store: SeenStore, status: MonitorStatus, forecast: object) -> dict:
    """页面上的轮询状态。概率只展示，不代表已经重置。"""
    seen = seen_store.get()
    last_seen_id = ""
    last_reset_at = ""
    # 还没建立基线时页面要明确写出来
    if seen is not None:
        last_seen_id = seen.last_seen_id
        last_reset_at = seen.last_reset_at
    rounded_24h = None
    rounded_48h = None
    # 没有缓存的预测时不编概率
    if forecast is not None:
        rounded_24h = forecast.rounded_24h
        rounded_48h = forecast.rounded_48h
    return {
        "baselined": seen is not None,
        "last_seen_id": last_seen_id,
        "last_reset_at": last_reset_at,
        "rounded_24h": rounded_24h,
        "rounded_48h": rounded_48h,
        "last_error": status.last_error,
        "last_poll_at": status.last_poll_at,
        "last_message_count": status.last_message_count,
        "source_label": "Data: codex-reset.com",
        "source_url": "https://codex-reset.com",
    }
