# 数据层：只读请求 codex-reset.com。判定不在这里。

import json

from ..entity.constants import API_ORIGIN, FORECAST_PATH, TIMELINE_PATH
from ..entity.record import LoadResult
from .parse import parse_events, parse_forecast


def _aiohttp():
    """运行时再导入 aiohttp。单测不打网络时不必安装它。"""
    import aiohttp

    return aiohttp


def read_max_age(header_value: object) -> int:
    """从 Cache-Control 取出 max-age。没有或不是数字就当 0。"""
    # 没带头时不额外拉长间隔
    if not header_value:
        return 0
    parts = str(header_value).split(",")
    for part in parts:
        item = part.strip()
        # 只认 max-age，别的缓存指令不影响轮询
        if not item.startswith("max-age="):
            continue
        number = item[len("max-age=") :]
        try:
            value = int(number)
        except ValueError:
            return 0
        # 负数没有意义，忽略
        if value < 0:
            return 0
        return value
    return 0


def read_retry_after(header_value: object) -> int:
    """429 的 Retry-After 秒数。不是整数时交给上层用最小间隔。"""
    # 没有这个头就不额外等待
    if not header_value:
        return 0
    try:
        value = int(str(header_value).strip())
    except ValueError:
        return 0
    # 负数不当成等待
    if value < 0:
        return 0
    return value


class ResetClient:
    """拉取时间线和预测。调用方注入 fetch 时可脱离网络测试。"""

    def __init__(self, user_agent: str, timeout_seconds: int, fetch=None) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self._fetch = fetch

    async def load(self) -> LoadResult:
        """拉两个只读接口。任一失败都不把半份数据交给判定。"""
        timeline = await self._get(TIMELINE_PATH)
        forecast = await self._get(FORECAST_PATH)
        return _merge_loads(timeline, forecast)

    async def _get(self, path: str) -> tuple:
        """请求一个路径。返回状态、正文、缓存秒数、重试秒数、错误。"""
        # 测试注入的 fetch 不走真实网络
        if self._fetch is not None:
            return await self._fetch(path, self.user_agent, self.timeout_seconds)
        return await self._get_aiohttp(path)

    async def _get_aiohttp(self, path: str) -> tuple:
        """真实 GET。必须带 User-Agent，否则来源可能拒绝。"""
        aiohttp = _aiohttp()
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        url = API_ORIGIN + path
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    return await _read_response(resp)
        except aiohttp.ClientError as exc:
            return 0, None, 0, 0, "请求失败：" + type(exc).__name__
        except TimeoutError:
            return 0, None, 0, 0, "请求超时"


async def _read_response(resp: object) -> tuple:
    """读状态和头。非 200 不解析正文，避免把错误页当事件。"""
    status = int(getattr(resp, "status", 0))
    headers = getattr(resp, "headers", {})
    cache_max_age = read_max_age(headers.get("Cache-Control"))
    retry_after = read_retry_after(headers.get("Retry-After"))
    # 429 必须停手，并听 Retry-After
    if status == 429:
        return status, None, cache_max_age, retry_after, "来源返回 429"
    # 其它非 200 也不拿来判定
    if status != 200:
        return status, None, cache_max_age, retry_after, "来源返回 " + str(status)
    text = await resp.text()
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return status, None, cache_max_age, retry_after, "来源不是 JSON"
    return status, body, cache_max_age, retry_after, ""


def _merge_loads(timeline: tuple, forecast: tuple) -> LoadResult:
    """两个接口都成功才返回可判定数据。"""
    cache_max_age = timeline[2]
    # 两个头都要遵守，取更长的缓存时间
    if forecast[2] > cache_max_age:
        cache_max_age = forecast[2]
    retry_after = timeline[3]
    # 任一侧要求重试，就按更长的 Retry-After 等
    if forecast[3] > retry_after:
        retry_after = forecast[3]
    # 时间线失败时不能判定，也不要用旧预测假装成功
    if timeline[4]:
        return LoadResult(None, None, cache_max_age, retry_after, timeline[4])
    # 预测失败时仍不能宣称这轮完整，避免漏掉 last_reset_at 前移
    if forecast[4]:
        return LoadResult(None, None, cache_max_age, retry_after, forecast[4])
    events = parse_events(timeline[1])
    snapshot = parse_forecast(forecast[1])
    return LoadResult(events, snapshot, cache_max_age, retry_after, "")
