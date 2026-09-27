# 入口层：注册 WebUI 接口、记下已配置群的会话，并按轮询结果推送。
# 不注册群口令。开哪些群只在 WebUI 增删改查。

import asyncio
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.api.web import error_response, json_response, request

from .business.groups import (
    add_group,
    delete_group,
    list_payload,
    push_targets,
    remember_origin,
    row_payload,
    session_umo,
    stored_enabled,
    switch_notice_text,
    update_group,
)
from .business.poll import run_once, status_payload
from .business.settings import platform_id, poll_seconds, timeout_seconds, user_agent
from .data.client import ResetClient
from .data.group_store import GroupStore
from .data.seen_store import SeenStore
from .entity.constants import DB_FILE_NAME, PLUGIN_NAME
from .entity.record import MonitorStatus


class CodexResetPlugin(Star):
    """轮询 Codex 重置来源，推送到 WebUI 里开启的群。"""

    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        self.config = config
        db_path = Path(StarTools.get_data_dir()) / DB_FILE_NAME
        self.groups = GroupStore(db_path)
        self.seen = SeenStore(db_path)
        self.status = MonitorStatus()
        self._task = asyncio.create_task(self._poll_loop())
        self._register_pages()
        logger.info("[codex_reset] 业务库已载入：%s", db_path)

    def _register_pages(self) -> None:
        """注册页面用的增删改查和状态接口。路由必须带插件名前缀。"""
        self.context.register_web_api(
            f"/{PLUGIN_NAME}/groups",
            self.page_list_groups,
            ["GET"],
            "列出监控群",
        )
        self.context.register_web_api(
            f"/{PLUGIN_NAME}/groups",
            self.page_add_group,
            ["POST"],
            "新增监控群",
        )
        self.context.register_web_api(
            f"/{PLUGIN_NAME}/groups/update",
            self.page_update_group,
            ["POST"],
            "修改监控群",
        )
        self.context.register_web_api(
            f"/{PLUGIN_NAME}/groups/delete",
            self.page_delete_group,
            ["POST"],
            "删除监控群",
        )
        self.context.register_web_api(
            f"/{PLUGIN_NAME}/status",
            self.page_status,
            ["GET"],
            "查看轮询状态",
        )

    async def terminate(self) -> None:
        """卸载时停掉轮询，避免插件重载后两轮一起打来源。"""
        # 还没建任务就不用取消
        if self._task is None:
            return
        self._task.cancel()

    def _client(self) -> ResetClient:
        """按当前配置建一个只读客户端。"""
        return ResetClient(user_agent(self.config), timeout_seconds(self.config))

    async def _poll_loop(self) -> None:
        """按来源允许的间隔轮询。取消任务时退出。"""
        while True:
            wait = await self._tick()
            await asyncio.sleep(wait)

    async def _tick(self) -> int:
        """跑一轮。异常只记日志，下一分钟再试，不把任务打崩。"""
        try:
            messages, wait = await run_once(
                self._client(),
                self.seen,
                self.status,
                poll_seconds(self.config),
            )
        except Exception as exc:
            logger.warning("[codex_reset] 轮询异常：%s", type(exc).__name__)
            self.status.note_error("", "轮询异常：" + type(exc).__name__)
            return poll_seconds(self.config)
        # 有新重置才推，没有消息就只是更新了基线或什么都没变
        if messages:
            await self._push_all(messages)
        return wait

    async def _push_all(self, messages: list) -> None:
        """把文案发到当前可推送的群。某个群失败不影响其它群。"""
        targets = push_targets(self.groups.list_rows(), platform_id(self.config))
        # 没有可推送的群就只记在库里，避免以后补推历史
        if not targets:
            logger.info("[codex_reset] 有新重置，但没有可推送的群")
            return
        for group_id, umo in targets:
            await self._push_one(group_id, umo, messages)

    async def _push_one(self, group_id: str, umo: str, messages: list) -> None:
        """向一个会话逐条发送。失败只记日志，不回滚已见位置。"""
        for text in messages:
            try:
                await self.context.send_message(umo, MessageChain().message(text))
            except Exception as exc:
                logger.warning(
                    "[codex_reset] 推送到群 %s 失败：%s",
                    group_id,
                    type(exc).__name__,
                )

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """已配置的群来消息时记下真实会话。不回复，也不拦 LLM。"""
        group_id = event.get_group_id()
        # 私聊或拿不到群号的事件不记
        if not group_id:
            return
        umo = getattr(event, "unified_msg_origin", "") or ""
        await remember_origin(self.groups, str(group_id), str(umo))

    async def page_list_groups(self):
        """页面列出全部监控群。"""
        rows = list_payload(self.groups.list_rows(), platform_id(self.config))
        return json_response({"groups": rows})

    async def page_add_group(self):
        """页面新增一群。校验失败不写库。开着就通知该群。"""
        payload = await request.json(default={})
        result = await add_group(
            self.groups,
            str(payload.get("group_id", "")).strip(),
            str(payload.get("remark", "")).strip(),
            _read_enabled(payload, True),
        )
        # 不合格或重复时把原因还给页面
        if result.error:
            return error_response(result.error, status_code=400)
        notice = await self._announce_switch(False, result.row)
        return json_response(_saved_payload(result.row, platform_id(self.config), notice))

    async def page_update_group(self):
        """页面改备注和开关。群号不变。开关变化时通知该群。"""
        payload = await request.json(default={})
        group_id = str(payload.get("group_id", "")).strip()
        was_enabled = stored_enabled(self.groups, group_id)
        result = await update_group(
            self.groups,
            group_id,
            str(payload.get("remark", "")).strip(),
            _read_enabled(payload, False),
        )
        # 没有这个群或备注不合法时不改库，也不发通知
        if result.error:
            return error_response(result.error, status_code=400)
        notice = await self._announce_switch(was_enabled, result.row)
        return json_response(_saved_payload(result.row, platform_id(self.config), notice))

    async def _announce_switch(self, was_enabled: bool, row) -> str:
        """开关变了就发到该群。发不出时返回页面上要显示的说明。"""
        text = switch_notice_text(was_enabled, row.enabled)
        # 只改备注不发，避免每次保存都刷群
        if not text:
            return ""
        umo = session_umo(row, platform_id(self.config))
        # 没有会话就无法告知，状态仍然已经保存
        if not umo:
            return "群状态已保存，但没有可用会话，群里没有发出通知。请先填写平台 ID。"
        try:
            await self.context.send_message(umo, MessageChain().message(text))
        except Exception as exc:
            return "群状态已保存，但通知发送失败：" + type(exc).__name__
        return ""

    async def page_delete_group(self):
        """页面删除一群。"""
        payload = await request.json(default={})
        result = await delete_group(self.groups, str(payload.get("group_id", "")).strip())
        # 没有这个群时告诉页面，不当成成功
        if result.error:
            return error_response(result.error, status_code=400)
        return json_response({"deleted": True})

    async def page_status(self):
        """页面看最近一轮轮询。不额外打来源，避免突破每分钟 1 次。"""
        return json_response(status_payload(self.seen, self.status, None))


def _read_enabled(payload: dict, default: bool) -> bool:
    """读页面提交的开关。缺字段时用调用方给的默认。"""
    # 页面没传这个字段，新增默认开，修改不能猜
    if "enabled" not in payload:
        return default
    return bool(payload.get("enabled"))


def _saved_payload(row, platform: str, notice: str) -> dict:
    """保存成功后给页面的结果。notice 非空表示群里没通知到。"""
    return {"group": row_payload(row, platform), "notice": notice}
