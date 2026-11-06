"""Daily luck (今日人品) for AstrBot, ported from AmiyaBot's ``src/jrrp``."""

from __future__ import annotations

import re
from pathlib import Path

from astrbot.api import star
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.message_components import ActionRow, At, Button, Plain
from astrbot.core.platform.message_type import MessageType

from .clock import Clock
from .defaults import DEFAULT_RANGES
from .luck import (
    average_luck,
    bounds,
    calculate_luck_level,
    generate_luck_value,
    parse_ranges,
    same_month,
    same_week,
)
from .storage import JrrpStore

#: Words that ask for today's luck; the reference plugin answers them without a prefix.
_TODAY = re.compile(r"^\s*[/／]?\s*(?:jrrp|今日人品|今日运势)\s*$", re.IGNORECASE)

#: Words that ask for the all-time average.
_ALL = re.compile(
    r"^\s*[/／]?\s*(?:alljrrp|总人品|平均人品|平均运势)\s*$", re.IGNORECASE
)

#: Words that ask for this month's average.
_MONTH = re.compile(
    r"^\s*[/／]?\s*(?:monthjrrp|本月人品|本月运势|月运势)\s*$", re.IGNORECASE
)

#: Words that ask for this week's average.
_WEEK = re.compile(
    r"^\s*[/／]?\s*(?:weekjrrp|本周人品|本周运势|周运势)\s*$", re.IGNORECASE
)


def _as_int(user_id: str) -> int:
    """Turn a platform sender id into the integer the reference plugin expects.

    Args:
        user_id: Sender id, numeric on QQ and Telegram but arbitrary elsewhere.

    Returns:
        The numeric id, or a stable 63-bit hash for non-numeric ids.
    """
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return int.from_bytes(user_id.encode("utf-8")[:8].ljust(8, b"\0"), "big") >> 1


#: Action id carried by the ``查查我的`` button.
_BUTTON_ID = "jrrp_check_mine"

#: Platforms that render the inline keyboard as a card button.
_BUTTON_PLATFORMS = ("qq_official",)


def _reply(
    event: AstrMessageEvent, text: str, *, mention: bool = True
) -> MessageEventResult:
    """Build a reply that optionally mentions the sender and offers a button.

    Args:
        event: Incoming message event.
        text: Reply body.
        mention: Whether to prepend ``@sender``.

    Returns:
        A chain of the mention (when enabled), the text and, on QQ official
        bots, one button that reruns the query for whoever clicks it.
    """
    # QQ rejects `<qqbot-at-user>` in C2C messages, so the mention is limited to
    # group chats.
    in_group = event.get_message_type() == MessageType.GROUP_MESSAGE
    chain = (
        [At(qq=event.get_sender_id()), Plain(text)]
        if mention and in_group
        else [Plain(text)]
    )
    platform = event.get_platform_name() or ""
    if any(platform.startswith(name) for name in _BUTTON_PLATFORMS):
        chain.append(
            ActionRow(
                buttons=[
                    Button(
                        id=_BUTTON_ID,
                        label="查查我的",
                        style=Button.Style.SUCCESS,
                        action=Button.CallbackAction(data={"cmd": "jrrp"}),
                    )
                ],
                fallback_text="查查我的",
            )
        )
    return event.chain_result(chain)


class Main(star.Star):
    """Answer 今日人品 queries and keep one record per user and day."""

    def __init__(self, context: star.Context, config: dict | None = None) -> None:
        """Create the plugin; the database is opened in ``initialize``.

        Args:
            context: AstrBot plugin context.
            config: Plugin configuration coming from ``_conf_schema.json``.
        """
        super().__init__(context, config)
        self.config = config or {}
        self.ranges = parse_ranges(self.config.get("ranges"), DEFAULT_RANGES)
        timeout = self.config.get("sync_timeout")
        self.clock = Clock(self.logger, timeout=float(timeout) if timeout else 5.0)
        self.store: JrrpStore | None = None
        self._sync_time = bool(self.config.get("time_sync", True))
        self._mention = bool(self.config.get("mention", True))

    async def initialize(self) -> None:
        """Open the database and, when enabled, align the clock with bjtime.org.cn."""
        try:
            data_dir = star.StarTools.get_data_dir("astrbot_plugin_jrrp")
        except Exception as exc:  # noqa: BLE001 - fall back to the plugin folder
            self.logger.warning("data dir unavailable (%s), using plugin folder", exc)
            data_dir = Path(__file__).parent / "data"
        self.store = JrrpStore(Path(data_dir) / "jrrp.db")
        if self._sync_time:
            await self.clock.sync()

    async def terminate(self) -> None:
        """Close the database connection."""
        if self.store is not None:
            self.store.close()
            self.store = None

    def _reply(self, event: AstrMessageEvent, text: str) -> MessageEventResult:
        """Reply with the user's mention when the config allows it.

        Args:
            event: Incoming message event.
            text: Reply body.

        Returns:
            The message chain built by the module level helper.
        """
        return _reply(event, text, mention=self._mention)

    def _store(self) -> JrrpStore:
        """Return the opened store, creating it when ``initialize`` was skipped.

        Returns:
            The active store.
        """
        if self.store is None:
            data_dir = Path(__file__).parent / "data"
            self.store = JrrpStore(data_dir / "jrrp.db")
        return self.store

    def _today_text(self, event: AstrMessageEvent) -> str:
        """Compute today's luck for the sender and record it once per day.

        Args:
            event: Incoming message event.

        Returns:
            The reply body with the value, its level and the level remark.
        """
        user_id = event.get_sender_id()
        today = self.clock.stamp("%y%m%d")
        seed = int(today) + _as_int(user_id)
        low, high = bounds(self.ranges)
        value = generate_luck_value(low, high, seed)
        store = self._store()
        if not store.has(user_id, today):
            store.add(user_id, value, today)
        level, description = calculate_luck_level(value, self.ranges)
        return f'您今日的幸运指数是 {value}，为"{level}"，{description}'

    @filter.regex(_TODAY)
    async def on_today(self, event: AstrMessageEvent):
        """Answer today's luck, recording it the first time of the day.

        Args:
            event: Incoming message event.

        Yields:
            One text result with the value and its level.
        """
        yield self._reply(event, self._today_text(event))

    @filter.button_action(_BUTTON_ID)
    async def on_check_button(self, event: AstrMessageEvent):
        """Answer the inline ``查查我的`` button for whoever clicked it.

        Args:
            event: Button interaction event carrying the clicking sender.

        Yields:
            One text result with that user's value for today.
        """
        yield self._reply(event, self._today_text(event))

    @filter.regex(_WEEK)
    async def on_week(self, event: AstrMessageEvent):
        """Answer the average of the current ISO week.

        Args:
            event: Incoming message event.

        Yields:
            One text result.
        """
        yield self._average_result(event, "本周", same_week)

    @filter.regex(_MONTH)
    async def on_month(self, event: AstrMessageEvent):
        """Answer the average of the current month.

        Args:
            event: Incoming message event.

        Yields:
            One text result.
        """
        yield self._average_result(event, "本月", same_month)

    @filter.regex(_ALL)
    async def on_all(self, event: AstrMessageEvent):
        """Answer the average of every stored record.

        Args:
            event: Incoming message event.

        Yields:
            One text result.
        """
        user_id = event.get_sender_id()
        rows = self._store().history(user_id)
        if not rows:
            yield self._reply(event, "您还没有过历史人品记录！")
            return
        days, avg = average_luck([value for _, value in rows])
        yield self._reply(
            event, f"您一共使用了 {days} 天 jrrp，您历史平均的幸运指数是 {avg}"
        )

    def _average_result(
        self, event: AstrMessageEvent, label: str, match
    ) -> MessageEventResult:
        """Build the week/month reply.

        Args:
            event: Incoming message event.
            label: ``本周`` or ``本月``, used in the wording.
            match: ``same_week`` or ``same_month``.

        Returns:
            The text result, including the reference plugin's empty-state wording.
        """
        user_id = event.get_sender_id()
        rows = self._store().history(user_id)
        if not rows:
            return self._reply(event, "您还没有过历史人品记录！")
        now = self.clock.now()
        picked = [value for date, value in rows if match(date, now)]
        if not picked:
            return self._reply(event, f"您{label}还没有过人品记录！")
        days, avg = average_luck(picked)
        return self._reply(
            event, f"您{label}共使用了 {days} 天 jrrp，平均的幸运指数是 {avg}"
        )
