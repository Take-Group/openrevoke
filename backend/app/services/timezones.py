"""Time zones the organization can pick: IANA names from the ``tzdata`` package (no system tz database needed)."""

from functools import cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

DEFAULT_TIMEZONE = "Europe/Warsaw"


@cache
def known_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def is_known_timezone(name: str) -> bool:
    if name not in known_timezones():
        return False
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError, ValueError:
        return False
    return True
