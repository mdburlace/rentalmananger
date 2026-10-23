"""Australian financial year helpers (1 July – 30 June).

A financial year is identified by the calendar year it ENDS in, so FY 2026
means 1 July 2025 – 30 June 2026 and is displayed as "2025-26".
"""
from __future__ import annotations

import re
from datetime import date


def fy_of(d: date) -> int:
    return d.year + 1 if d.month >= 7 else d.year


def fy_bounds(fy: int) -> tuple[date, date]:
    return date(fy - 1, 7, 1), date(fy, 6, 30)


def fy_label(fy: int) -> str:
    return f"{fy - 1}-{str(fy)[-2:]}"


def current_fy(today: date | None = None) -> int:
    return fy_of(today or date.today())


_FY_PATTERNS = [
    # "23 - 24", "2023-2024", "2023-24", "FY24"
    re.compile(r"(?<!\d)(20)?(\d{2})\s*[-–/]\s*(20)?(\d{2})(?!\d)"),
]


def fy_from_text(text: str) -> int | None:
    """Guess a financial year from a sheet name like '23 - 24yr expences'."""
    if not text:
        return None
    for pat in _FY_PATTERNS:
        m = pat.search(text)
        if m:
            start = int(m.group(2))
            end = int(m.group(4))
            if (start + 1) % 100 == end:
                return 2000 + end
    m = re.search(r"FY\s*(20)?(\d{2})", text, re.I)
    if m:
        return 2000 + int(m.group(2))
    return None
