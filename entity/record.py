# 实体层：时间线事件、预测快照、已见状态和页面行。只放数据形状。


class TimelineEvent:
    """一条时间线事件。字段来自 /api/timeline 的 events 项。"""

    def __init__(
        self,
        event_id: str,
        group: str,
        announcement_state: str,
        summary: str,
        url: str,
        announced_at: str,
    ) -> None:
        self.event_id = event_id
        self.group = group
        self.announcement_state = announcement_state
        self.summary = summary
        self.url = url
        self.announced_at = announced_at


class ForecastSnapshot:
    """/api/forecast 里判定和展示要用的字段。概率只展示，不参与判定。"""

    def __init__(self, last_reset_at: str, rounded_24h: object, rounded_48h: object) -> None:
        self.last_reset_at = last_reset_at
        self.rounded_24h = rounded_24h
        self.rounded_48h = rounded_48h


class SeenState:
    """已经处理过的重置位置。用来避免重复推送。"""

    def __init__(self, last_seen_id: str, last_announced_at: str, last_reset_at: str) -> None:
        self.last_seen_id = last_seen_id
        self.last_announced_at = last_announced_at
        self.last_reset_at = last_reset_at


class LoadResult:
    """一次拉取的结果。events 为 None 表示时间线没拿到，不能拿来判定。"""

    def __init__(
        self,
        events: list | None,
        forecast: ForecastSnapshot | None,
        cache_max_age: int,
        retry_after: int,
        error: str,
    ) -> None:
        self.events = events
        self.forecast = forecast
        self.cache_max_age = cache_max_age
        self.retry_after = retry_after
        self.error = error


class UpdatePlan:
    """一轮判定要推的文案，以及是否落库新的已见位置。"""

    def __init__(self, messages: list, next_seen: SeenState | None, should_save: bool) -> None:
        self.messages = messages
        self.next_seen = next_seen
        self.should_save = should_save


class GroupRow:
    """WebUI 里的一行开启群。没在表里就是没开启。"""

    def __init__(self, group_id: str, remark: str, enabled: bool, umo: str) -> None:
        self.group_id = group_id
        self.remark = remark
        self.enabled = enabled
        self.umo = umo


class ActionResult:
    """增删改的结果。error 非空时页面要显示失败，不能当成功。"""

    def __init__(self, error: str, row: GroupRow | None) -> None:
        self.error = error
        self.row = row


class MonitorStatus:
    """内存里的最近一轮轮询。重启后清空，不进业务表。"""

    def __init__(self) -> None:
        self.last_error = ""
        self.last_poll_at = ""
        self.last_message_count = 0

    def note_ok(self, polled_at: str, message_count: int) -> None:
        """记录一轮成功拉取。成功时清掉上次错误，避免页面一直显示旧失败。"""
        self.last_error = ""
        self.last_poll_at = polled_at
        self.last_message_count = message_count

    def note_error(self, polled_at: str, error: str) -> None:
        """记录一轮失败。不改已见位置，下一轮还会再拉。"""
        self.last_error = error
        self.last_poll_at = polled_at
        self.last_message_count = 0
