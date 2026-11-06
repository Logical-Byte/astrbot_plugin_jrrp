"""Fallback luck ranges, copied from the reference plugin's config_default.yaml."""

from typing import Any

#: Luck ranges used when the config text is empty or invalid.
#: Each entry maps an inclusive ``min``/``max`` window to a level and a remark.
DEFAULT_RANGES: list[dict[str, Any]] = [
    {
        "min": 100,
        "max": 100,
        "level": "超吉",
        "description": "100！100诶！！你就是欧皇？",
    },
    {"min": 76, "max": 99, "level": "大吉", "description": "好耶！今天运气真不错呢"},
    {"min": 66, "max": 75, "level": "吉", "description": "哦豁，今天运气还顺利哦"},
    {"min": 63, "max": 65, "level": "半吉", "description": "emm，今天运气一般般呢"},
    {
        "min": 59,
        "max": 62,
        "level": "小吉",
        "description": "还……还行吧，今天运气稍差一点点呢",
    },
    {"min": 54, "max": 58, "level": "末小吉", "description": "唔……今天运气有点差哦"},
    {"min": 19, "max": 53, "level": "末吉", "description": "呜哇，今天运气应该不太好"},
    {
        "min": 10,
        "max": 18,
        "level": "凶",
        "description": "啊这……（没错……是百分制），今天还是吃点好的吧",
    },
    {
        "min": 1,
        "max": 9,
        "level": "大凶",
        "description": "啊这……（个位数可还行），今天还是吃点好的吧",
    },
    {"min": 0, "max": 0, "level": "超凶（大寄）", "description": "？？？反向欧皇？"},
]
