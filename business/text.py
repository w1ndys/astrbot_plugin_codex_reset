# 业务层：推送和页面用的文案。展示面必须署来源。

from ..entity.constants import SOURCE_LABEL, SOURCE_URL
from ..entity.record import TimelineEvent


def attribution() -> str:
    """来源要求的署名和链接。每条对外展示都要带。"""
    return SOURCE_LABEL + "\n" + SOURCE_URL


def format_reset(event: TimelineEvent) -> str:
    """一条已宣布重置的群消息。"""
    summary = event.summary or "来源未提供摘要"
    url = event.url or SOURCE_URL
    when = event.announced_at or "来源未提供时间"
    return (
        "Codex 额度重置已宣布\n"
        + summary
        + "\n"
        + url
        + "\n时间："
        + when
        + "\n"
        + attribution()
    )


def format_forecast_move(old_at: str, new_at: str) -> str:
    """时间线没有对应宣布、但 last_reset_at 已经前移时的补充通知。"""
    return (
        "Codex 额度重置时间已前移\n上次："
        + old_at
        + "\n现在："
        + new_at
        + "\n"
        + attribution()
    )


def format_enabled() -> str:
    """本群刚被打开时发到群里的通知。"""
    return "本群已开启 Codex 重置监控。\n之后出现已宣布的重置时，会在这里推送。\n" + attribution()


def format_disabled() -> str:
    """本群刚被关掉时发到群里的通知。"""
    return "本群已关闭 Codex 重置监控。\n之后不会再推送重置消息。\n" + attribution()


def show_probability(value: object) -> str:
    """概率只给页面看。没有就写未知，避免把空值显示成 None。"""
    # 来源这轮没给概率
    if value is None:
        return "未知"
    return str(value)
