# 数据层：把公开接口的 JSON 收成实体。不判定是不是重置。

from ..entity.record import ForecastSnapshot, TimelineEvent


def parse_events(body: object) -> list:
    """按接口原顺序取出 events。来源是倒序，调用方不要自己重排。"""
    # 不是对象就没有事件列表，当空表，不当崩溃
    if not isinstance(body, dict):
        return []
    raw = body.get("events")
    # 缺 events 或类型不对，同样当空表
    if not isinstance(raw, list):
        return []
    events = []
    for item in raw:
        event = _one_event(item)
        # 没有 id 的项不能用来去重，丢掉
        if event is None:
            continue
        events.append(event)
    return events


def _one_event(item: object) -> TimelineEvent | None:
    """读一条事件。缺 id 返回 None。"""
    # 列表里混进非对象时跳过这一条
    if not isinstance(item, dict):
        return None
    event_id = item.get("id")
    # 没有 id 就无法和 last_seen_id 比较
    if not event_id:
        return None
    group = item.get("group") or ""
    state = item.get("announcement_state") or ""
    summary = item.get("summary") or ""
    url = item.get("url") or ""
    announced_at = item.get("announced_at") or ""
    return TimelineEvent(str(event_id), str(group), str(state), str(summary), str(url), str(announced_at))


def parse_forecast(body: object) -> ForecastSnapshot | None:
    """读 last_reset_at 和展示用概率。不是对象就当这次没有预测。"""
    # 预测接口失败时不要编一个空快照去覆盖已见时间
    if not isinstance(body, dict):
        return None
    last_reset_at = body.get("last_reset_at") or ""
    rounded_24h = None
    rounded_48h = None
    probabilities = body.get("probabilities")
    # 概率块缺失时仍保留 last_reset_at，判定不依赖概率
    if isinstance(probabilities, dict):
        rounded_24h = probabilities.get("rounded_24h")
        rounded_48h = probabilities.get("rounded_48h")
    return ForecastSnapshot(str(last_reset_at), rounded_24h, rounded_48h)
