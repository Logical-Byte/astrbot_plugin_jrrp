"""Pure helpers for the daily-luck value, its level and the date filters.

The formulas mirror the reference AmiyaBot plugin byte for byte so that the same
user gets the same number on the same day on both bots.
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterable
from datetime import datetime
from typing import Any

#: Absolute bound of the seed-derived range, inherited from the reference plugin.
MIN_SAFE = -1_000_000
MAX_SAFE = 1_000_000

#: Range used when the configured bounds are not usable by ``randint``.
FALLBACK_MIN = 1
FALLBACK_MAX = 100


def parse_ranges(
    text: str | None, fallback: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Parse the JSON text of the config field.

    Args:
        text: JSON array written by the user, or ``None``/empty for the default.
        fallback: Ranges used when the text is empty, malformed or unusable.

    Returns:
        A list of ``{min, max, level, description}`` dicts.
    """
    if not text or not text.strip():
        return list(fallback)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return list(fallback)
    if not isinstance(data, list):
        return list(fallback)

    ranges: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            low = int(item["min"])
            high = int(item["max"])
        except (KeyError, TypeError, ValueError):
            continue
        if high < low:
            continue
        ranges.append(
            {
                "min": low,
                "max": high,
                "level": str(item.get("level") or "未知"),
                "description": str(item.get("description") or ""),
            }
        )
    return ranges or list(fallback)


def bounds(ranges: Iterable[dict[str, Any]]) -> tuple[int, int]:
    """Derive the drawable window from the configured ranges.

    Args:
        ranges: Parsed luck ranges.

    Returns:
        The smallest ``min`` and the largest ``max``; ``0``/``100`` when empty.
    """
    lows = [int(item["min"]) for item in ranges]
    highs = [int(item["max"]) for item in ranges]
    if not lows or not highs:
        return 0, 100
    return min(lows), max(highs)


def generate_luck_value(min_luck: int, max_luck: int, seed: int) -> int:
    """Draw the daily value from the seed, exactly like the reference plugin.

    Args:
        min_luck: Lower bound taken from the configured ranges.
        max_luck: Upper bound taken from the configured ranges.
        seed: ``int(YYMMDD) + int(user id)``.

    Returns:
        The luck value for that user on that day.
    """
    low = max(MIN_SAFE, min(int(min_luck), MAX_SAFE))
    high = max(MIN_SAFE, min(int(max_luck), MAX_SAFE))
    try:
        rnd = random.Random()
        rnd.seed(seed)
        return rnd.randint(low, high)
    except ValueError:
        # An inverted window would raise here; the reference falls back to 1..100.
        rnd = random.Random()
        rnd.seed(seed)
        return rnd.randint(FALLBACK_MIN, FALLBACK_MAX)


def calculate_luck_level(num: int, ranges: Iterable[dict[str, Any]]) -> tuple[str, str]:
    """Map a value to its configured level.

    Args:
        num: Luck value.
        ranges: Parsed luck ranges, first match wins.

    Returns:
        ``(level, description)``; the reference's void message when no window matches.
    """
    for item in ranges:
        if int(item["min"]) <= num <= int(item["max"]):
            return str(item["level"]), str(item["description"])
    return "未知", "你进入了虚空之地"


def average_luck(values: list[int]) -> tuple[int, float]:
    """Average a user's stored values.

    Args:
        values: Stored luck values.

    Returns:
        ``(days, average)`` with the average rounded to one decimal.
    """
    if not values:
        return 0, 0
    return len(values), round(sum(values) / len(values), 1)


def same_week(date_string: str, now: datetime) -> bool:
    """Tell whether a stored ``YYMMDD`` date falls in the same ISO week as ``now``.

    Args:
        date_string: Stored date.
        now: Current synced time.

    Returns:
        ``True`` on a match; ``False`` for unparsable dates.
    """
    try:
        day = datetime.strptime(date_string, "%y%m%d")
    except ValueError:
        return False
    return day.isocalendar()[1] == now.isocalendar()[1] and day.year == now.year


def same_month(date_string: str, now: datetime) -> bool:
    """Tell whether a stored ``YYMMDD`` date falls in the same month as ``now``.

    Args:
        date_string: Stored date.
        now: Current synced time.

    Returns:
        ``True`` on a match; ``False`` for unparsable dates.
    """
    try:
        day = datetime.strptime(date_string, "%y%m%d")
    except ValueError:
        return False
    return day.month == now.month and day.year == now.year
