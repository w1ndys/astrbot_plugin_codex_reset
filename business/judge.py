# 业务层：什么算一次已宣布的重置，以及相对已见位置是不是新的。

from ..entity.constants import GROUP_RESET, STATE_ANNOUNCED
from ..entity.record import ForecastSnapshot, SeenState, TimelineEvent, UpdatePlan
from .text import format_forecast_move, format_reset


def is_announced_reset(event: TimelineEvent) -> bool:
    """已宣布的 reset 才算重置。缺状态、其它分组、概率升高都不算。"""
    # 不是 reset 分组，boost / credits 不能当重置推
    if event.group != GROUP_RESET:
        return False
    # 来源没标 announced 的不能当重置，包括缺字段
    if event.announcement_state != STATE_ANNOUNCED:
        return False
    return True


def is_newer_than_seen(event: TimelineEvent, seen: SeenState) -> bool:
    """这条已宣布重置是不是比已见位置更新。同一条不能再推。"""
    # 已经推过这条，再见到直接跳过
    if event.event_id == seen.last_seen_id:
        return False
    # 两边都有宣布时间时以时间先后为准，避免 id 格式变化误判
    if event.announced_at and seen.last_announced_at:
        if event.announced_at > seen.last_announced_at:
            return True
        if event.announced_at < seen.last_announced_at:
            return False
        return event.event_id > seen.last_seen_id
    # 没有时间可比较时，只认更大的事件 id
    if seen.last_seen_id and event.event_id > seen.last_seen_id:
        return True
    return False


def plan_updates(
    events: list,
    forecast: ForecastSnapshot | None,
    seen: SeenState | None,
) -> UpdatePlan:
    """给出本轮要推的文案和新的已见位置。第一次只记基线，不推历史。"""
    # 还没见过来源时，只记下当前最新位置，避免把历史重置全部推出去
    if seen is None:
        base = build_baseline(events, forecast)
        # 时间和事件都没有，这轮不落库，下一轮再试
        if base is None:
            return UpdatePlan([], None, False)
        return UpdatePlan([], base, True)
    newer = collect_newer(events, seen)
    messages = texts_for_events(newer)
    moved = forecast_move_message(seen, forecast, newer)
    # 预测时间前移、但时间线没有对应宣布时，单独推一条
    if moved:
        messages.append(moved)
    next_seen = advance_seen(seen, forecast, newer)
    should_save = seen_changed(seen, next_seen)
    # 位置没变就不写库，也不推
    if not should_save:
        return UpdatePlan([], seen, False)
    return UpdatePlan(messages, next_seen, True)


def build_baseline(events: list, forecast: ForecastSnapshot | None) -> SeenState | None:
    """用当前最新已宣布事件和 last_reset_at 做基线。两者都没有就还不能记。"""
    newest = first_announced(events)
    reset_at = ""
    # 预测里的上次重置时间也是基线的一部分
    if forecast is not None and forecast.last_reset_at:
        reset_at = forecast.last_reset_at
    # 没有任何可记的位置，下一轮再建立基线
    if newest is None and not reset_at:
        return None
    event_id = ""
    announced_at = ""
    # 有已宣布事件就把 id 记下，后面只推比它新的
    if newest is not None:
        event_id = newest.event_id
        announced_at = newest.announced_at
    return SeenState(event_id, announced_at, reset_at)


def first_announced(events: list) -> TimelineEvent | None:
    """取倒序列表里第一条已宣布重置，也就是当前最新的一条。"""
    for event in events:
        # 跳过未宣布和其它分组，继续找
        if not is_announced_reset(event):
            continue
        return event
    return None


def collect_newer(events: list, seen: SeenState) -> list:
    """收集比已见位置新的已宣布重置，并改成从旧到新，方便按时间推送。"""
    found = []
    for event in events:
        # 未宣布的不进推送列表
        if not is_announced_reset(event):
            continue
        # 不比已见位置新的不再推
        if not is_newer_than_seen(event, seen):
            continue
        found.append(event)
    found.reverse()
    return found


def texts_for_events(events: list) -> list:
    """把新事件收成推送文案。"""
    texts = []
    for event in events:
        texts.append(format_reset(event))
    return texts


def forecast_move_message(
    seen: SeenState,
    forecast: ForecastSnapshot | None,
    newer: list,
) -> str:
    """last_reset_at 向前移动、且没有对应新事件时，返回一条补充文案。"""
    # 这轮没有预测，不能用概率或空值假装重置
    if forecast is None or not forecast.last_reset_at:
        return ""
    # 还没有旧时间，这次只是补基线，不当成前移
    if not seen.last_reset_at:
        return ""
    # 时间没往前，概率升高也不算重置
    if forecast.last_reset_at <= seen.last_reset_at:
        return ""
    for event in newer:
        # 同一时间已经有宣布事件，不再重复推一条预测
        if event.announced_at == forecast.last_reset_at:
            return ""
    return format_forecast_move(seen.last_reset_at, forecast.last_reset_at)


def advance_seen(seen: SeenState, forecast: ForecastSnapshot | None, newer: list) -> SeenState:
    """把已见位置推到这轮最新的事件和重置时间。"""
    event_id = seen.last_seen_id
    announced_at = seen.last_announced_at
    reset_at = seen.last_reset_at
    # newer 已按从旧到新排过，最后一条是最新宣布
    if newer:
        event_id = newer[-1].event_id
        # 新事件没有时间时保留旧时间，避免下次比较失效
        if newer[-1].announced_at:
            announced_at = newer[-1].announced_at
        if newer[-1].announced_at and newer[-1].announced_at > reset_at:
            reset_at = newer[-1].announced_at
    # 预测时间更晚时一并记住，避免下一轮又当成前移
    if forecast is not None and forecast.last_reset_at and forecast.last_reset_at > reset_at:
        reset_at = forecast.last_reset_at
    return SeenState(event_id, announced_at, reset_at)


def seen_changed(old: SeenState, new: SeenState) -> bool:
    """三个位置有一个变了才需要写库。"""
    # id 变了说明见到新事件
    if old.last_seen_id != new.last_seen_id:
        return True
    # 宣布时间变了也要记，否则同 id 比较会反复推
    if old.last_announced_at != new.last_announced_at:
        return True
    # 只有预测时间前移时也要记，避免下一轮重复推
    if old.last_reset_at != new.last_reset_at:
        return True
    return False
