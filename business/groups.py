# 业务层：校验 WebUI 提交的群数据，并决定推给哪些会话。

from ..entity.constants import GROUP_ID_MAX_LEN, GROUP_ID_MIN_LEN, GROUP_MESSAGE_TYPE, REMARK_MAX_LEN
from ..entity.record import ActionResult, GroupRow
from ..data.group_store import GroupStore
from .text import format_disabled, format_enabled


def check_group_id(group_id: str) -> str:
    """群号必须是数字，且长度落在常见 QQ 群号范围。不合规则返回原因。"""
    # 空群号无法对应会话
    if not group_id:
        return "请填写群号"
    # 非数字会把平台会话串拼坏
    if not group_id.isdigit():
        return "群号只能是数字"
    # 太短不像群号，多半是填错
    if len(group_id) < GROUP_ID_MIN_LEN:
        return "群号太短"
    # 太长也不像群号
    if len(group_id) > GROUP_ID_MAX_LEN:
        return "群号太长"
    return ""


def check_remark(remark: str) -> str:
    """备注只是给人看的，过长就拒绝，避免页面一行撑爆。"""
    # 超长备注不入库
    if len(remark) > REMARK_MAX_LEN:
        return "备注不能超过 40 字"
    return ""


def check_platform_id(platform_id: str) -> str:
    """平台 ID 不能含冒号，否则官方会话串无法按两段冒号拆开。"""
    # 留空是允许的，这时只能等群消息记下会话
    if not platform_id:
        return ""
    # 冒号是会话串的分隔符，不能出现在平台 ID 里
    if ":" in platform_id:
        return "平台 ID 不能包含冒号"
    return ""


async def add_group(store: GroupStore, group_id: str, remark: str, enabled: bool) -> ActionResult:
    """新增一群。重复群号不覆盖，让用户去改。"""
    id_error = check_group_id(group_id)
    # 群号不合格就不写库
    if id_error:
        return ActionResult(id_error, None)
    remark_error = check_remark(remark)
    # 备注不合格也不写库
    if remark_error:
        return ActionResult(remark_error, None)
    # 已存在就不要插入，避免把已记下的会话冲掉
    if store.get(group_id) is not None:
        return ActionResult("这个群已经在列表里", None)
    row = GroupRow(group_id, remark, enabled, "")
    await store.insert(row)
    return ActionResult("", row)


async def update_group(store: GroupStore, group_id: str, remark: str, enabled: bool) -> ActionResult:
    """改备注和开关。不改群号，换群号要删了再加。"""
    id_error = check_group_id(group_id)
    # 找不到合格群号就无法更新
    if id_error:
        return ActionResult(id_error, None)
    remark_error = check_remark(remark)
    # 备注不合格时保持原行
    if remark_error:
        return ActionResult(remark_error, None)
    current = store.get(group_id)
    # 没有这一行就不能改
    if current is None:
        return ActionResult("没有这个群", None)
    row = GroupRow(group_id, remark, enabled, current.umo)
    await store.save(row)
    return ActionResult("", row)


async def delete_group(store: GroupStore, group_id: str) -> ActionResult:
    """删除一群。删掉后不再推送。"""
    id_error = check_group_id(group_id)
    # 不合格群号本来也不该在表里
    if id_error:
        return ActionResult(id_error, None)
    # 没有这一行就告诉页面，不要假装删成功
    if store.get(group_id) is None:
        return ActionResult("没有这个群", None)
    await store.delete(group_id)
    return ActionResult("", None)


async def remember_origin(store: GroupStore, group_id: str, umo: str) -> bool:
    """群里来消息时记下真实会话。群不在表里就不动，避免自动开启。"""
    # 没有会话串就没东西可记
    if not umo:
        return False
    current = store.get(group_id)
    # 没在 WebUI 配置过的群不记，也不自动加入
    if current is None:
        return False
    # 会话没变就不写库
    if current.umo == umo:
        return False
    row = GroupRow(current.group_id, current.remark, current.enabled, umo)
    await store.save(row)
    return True


def build_umo(platform_id: str, group_id: str) -> str:
    """用平台 ID 和群号拼官方会话串。平台 ID 不合格时返回空串。"""
    # 平台 ID 不合格就不能拼，否则 send_message 会找错会话
    if check_platform_id(platform_id):
        return ""
    # 没填平台 ID 时不能编会话
    if not platform_id:
        return ""
    return platform_id + ":" + GROUP_MESSAGE_TYPE + ":" + group_id


def stored_enabled(store: GroupStore, group_id: str) -> bool:
    """改之前这个群开没开。没有记录就当关，新增时不会误发关闭通知。"""
    row = store.get(group_id)
    # 表里没有这一群，之前就是关着的
    if row is None:
        return False
    return row.enabled


def session_umo(row: GroupRow, platform_id: str) -> str:
    """定位这个群的会话。关闭通知也要能发，所以不看开关。"""
    # 已经见过群消息时，用真实会话，不自己拼
    if row.umo:
        return row.umo
    return build_umo(platform_id, row.group_id)


def switch_notice_text(was_enabled: bool, enabled: bool) -> str:
    """开关变了才有群通知。只改备注不发，避免每次保存都刷群。"""
    # 开关没变，不通知
    if was_enabled == enabled:
        return ""
    # 从关到开，告诉群里已经开始监控
    if enabled:
        return format_enabled()
    return format_disabled()


def push_targets(rows: list, platform_id: str) -> list:
    """开启且能定位会话的群。关闭的群不推。"""
    targets = []
    for row in rows:
        # 关闭的群即使有会话也不推
        if not row.enabled:
            continue
        umo = row.umo
        # 还没见过群消息时，用配置的平台 ID 拼会话
        if not umo:
            umo = build_umo(platform_id, row.group_id)
        # 两种办法都没有会话，这群这轮跳过
        if not umo:
            continue
        targets.append((row.group_id, umo))
    return targets


def row_payload(row: GroupRow, platform_id: str) -> dict:
    """给页面的一行。can_push 告诉用户现在能不能推到这个群。"""
    umo = row.umo
    # 页面上也用和推送相同的规则判断能不能发
    if not umo:
        umo = build_umo(platform_id, row.group_id)
    return {
        "group_id": row.group_id,
        "remark": row.remark,
        "enabled": row.enabled,
        "has_session": bool(row.umo),
        "can_push": bool(umo),
    }


def list_payload(rows: list, platform_id: str) -> list:
    """把全部行收成页面要的列表。"""
    payload = []
    for row in rows:
        payload.append(row_payload(row, platform_id))
    return payload
