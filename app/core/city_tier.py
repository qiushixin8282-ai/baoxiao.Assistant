"""城市分级数据，用于差旅住宿/伙食标准的限额判断。

改编自 megemini/AuditAgent 的 mcp_citytier 数据，做了精简。
"""

from typing import Dict, List

TIER_LABELS = {
    1: "一线城市",
    2: "二线城市",
    3: "其余地区",
}

# 住宿限额（元/晚）
TIER_HOTEL_LIMIT = {1: 600, 2: 500, 3: 400}

_TIER1: List[str] = ["北京", "上海", "广州", "深圳"]

_TIER2: List[str] = [
    "成都", "杭州", "重庆", "武汉", "西安", "苏州", "天津", "南京",
    "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明", "合肥",
    "佛山", "福州", "厦门", "大连", "无锡", "济南", "温州", "南宁",
]

_TIER_MAP: Dict[str, int] = {}
for _city in _TIER1:
    _TIER_MAP[_city] = 1
for _city in _TIER2:
    _TIER_MAP[_city] = 2


def _normalize(city: str) -> str:
    if not city:
        return ""
    city = city.strip()
    for suffix in ("特别行政区", "自治区", "地区", "市", "区", "县"):
        if city.endswith(suffix):
            city = city[: -len(suffix)]
    return city


def get_city_tier(city: str) -> int:
    """返回城市分级：1 一线、2 二线、其余 3。"""
    return _TIER_MAP.get(_normalize(city), 3)


def get_city_tier_label(city: str) -> str:
    return TIER_LABELS[get_city_tier(city)]


def get_hotel_limit(city: str) -> int:
    return TIER_HOTEL_LIMIT[get_city_tier(city)]
