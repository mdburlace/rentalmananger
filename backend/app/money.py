from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def to_cents(value) -> int:
    """Convert '1,234.56', '$1234.5', 1234.56 or Decimal to integer cents."""
    if value is None or value == "":
        raise ValueError("amount is required")
    if isinstance(value, int):
        return value * 100
    if isinstance(value, float):
        value = repr(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("$", "").replace(",", "").replace(" ", "")
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        value = cleaned
    try:
        d = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValueError(f"not a valid amount: {value!r}")
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_cents(cents: int | None) -> float | None:
    if cents is None:
        return None
    return round(cents / 100, 2)


def apply_percent(cents: int, percent) -> int:
    pct = Decimal(str(percent if percent is not None else 100))
    return int((Decimal(cents) * pct / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
