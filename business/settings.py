# 业务层：读 WebUI 全局配置。缺项回退默认，不让轮询停掉。

from ..entity.constants import DEFAULT_USER_AGENT, MIN_POLL_SECONDS


def get_setting(config: object, key: str, default: object) -> object:
    """从配置对象取值。没有配置或没有这个键时用默认。"""
    # 测试和未注入配置时走代码默认
    if config is None:
        return default
    try:
        value = config.get(key, default)  # type: ignore[union-attr]
    except Exception:
        # 配置对象不是 dict-like 时不能让插件挂掉
        return default
    # 键在但值为空，同样回退
    if value is None:
        return default
    return value


def get_int(config: object, key: str, default: int) -> int:
    """读整数。非数字回退默认。"""
    value = get_setting(config, key, default)
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def get_str(config: object, key: str, default: str) -> str:
    """读字符串并去掉首尾空白。"""
    value = get_setting(config, key, default)
    return str(value).strip()


def poll_seconds(config: object) -> int:
    """轮询间隔。小于来源下限时抬到 60 秒。"""
    value = get_int(config, "poll_seconds", MIN_POLL_SECONDS)
    # 来源禁止快于每分钟 1 次，配置写小了也不能真的打那么快
    if value < MIN_POLL_SECONDS:
        return MIN_POLL_SECONDS
    return value


def timeout_seconds(config: object) -> int:
    """HTTP 超时。小于 1 秒没有意义，抬回 20。"""
    value = get_int(config, "http_timeout_seconds", 20)
    # 0 或负数会让请求立刻失败
    if value < 1:
        return 20
    return value


def user_agent(config: object) -> str:
    """可识别的 User-Agent。配置留空时用插件默认。"""
    value = get_str(config, "user_agent", DEFAULT_USER_AGENT)
    # 空 User-Agent 会被来源拒绝，不能发出去
    if not value:
        return DEFAULT_USER_AGENT
    return value


def platform_id(config: object) -> str:
    """OneBot 平台实例 ID。留空就只能等群里来过消息再推。"""
    return get_str(config, "platform_id", "")
