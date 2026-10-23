"""Financial-year reporting: the numbers the accountant needs for the rental schedule."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ato import ATO_BY_KEY, ATO_LABELS
from ..fy import fy_bounds, fy_label, fy_of
from ..models import Loan, Property, PropertyYear, Transaction, User
from ..money import apply_percent, from_cents
from ..serialize import full_address


def _share(cents: int, pct: Decimal) -> int:
    return apply_percent(cents, pct)


def fy_transactions(db: Session, user: User, fy: int, property_id: int | None = None) -> list[Transaction]:
    start, end = fy_bounds(fy)
    q = select(Transaction).where(Transaction.portfolio_id == user.portfolio_id,
                                  Transaction.date >= start, Transaction.date <= end)
    if property_id:
        q = q.where(Transaction.property_id == property_id)
    return list(db.scalars(q.order_by(Transaction.date, Transaction.id)).unique().all())


def _checks(db: Session, prop: Property, fy: int, txns: list[Transaction], py: PropertyYear | None,
            totals: dict[str, int]) -> list[dict]:
    """Things worth fixing (or explaining) before sending to the accountant."""
    out: list[dict] = []

    def add(level: str, msg: str):
        out.append({"level": level, "message": msg})

    if not prop.ownerships:
        add("warning", "Ownership isn't set – the report assumes one owner at 100%.")
    elif abs(sum(o.share_percent for o in prop.ownerships) - 100) > Decimal("0.01"):
        add("error", "Ownership shares don't add up to 100%.")
    if not totals.get("gross_rent"):
        add("warning", "No rent income recorded for this year. Add rent received (or the agent's EOFY statement total).")
    if not py or py.weeks_rented is None:
        add("info", "Weeks rented this year hasn't been entered (the rental schedule asks for it).")
    review = [t for t in txns if t.needs_review]
    if review:
        add("warning", f"{len(review)} transaction(s) are flagged for review.")
    no_receipt = [t for t in txns if not t.attachments and ATO_BY_KEY[t.category.ato_key].kind == "expense"]
    if no_receipt:
        add("info", f"{len(no_receipt)} expense(s) have no receipt or statement attached.")

    # Interest is normally charged monthly – spot missing months.
    interest_months = {(t.date.year, t.date.month) for t in txns if t.category.ato_key == "interest"}
    if interest_months and len(interest_months) < 12:
        start, _ = fy_bounds(fy)
        missing = []
        y, m = start.year, start.month
        for _ in range(12):
            if (y, m) not in interest_months:
                missing.append(date(y, m, 1).strftime("%b %Y"))
            m += 1
            if m == 13:
                y, m = y + 1, 1
        add("warning", f"Loan interest is missing for: {', '.join(missing)}.")

    # Same bill amount recorded in a neighbouring year – often a bill counted twice.
    s, e = fy_bounds(fy)
    near = db.scalars(select(Transaction).where(
        Transaction.property_id == prop.id,
        Transaction.date >= date(s.year - 1, s.month, s.day), Transaction.date <= date(e.year + 1, e.month, e.day),
    )).unique().all()
    seen = set()
    for t in txns:
        for o in near:
            if (o.id != t.id and fy_of(o.date) != fy and o.category_id == t.category_id
                    and o.amount_cents == t.amount_cents and abs((o.date - t.date).days) < 200
                    and t.category.ato_key not in ("interest", "gross_rent")):
                key = tuple(sorted((t.id, o.id)))
                if key in seen:
                    continue
                seen.add(key)
                add("warning", f"{t.category.name} ${from_cents(t.amount_cents):,.2f} on {t.date:%d/%m/%Y} also appears "
                               f"on {o.date:%d/%m/%Y} (FY{fy_label(fy_of(o.date))}) – check it isn't counted twice.")
    return out


def property_fy_report(db: Session, user: User, prop: Property, fy: int, txns: list[Transaction]) -> dict:
    gross: dict[str, int] = defaultdict(int)
    claim: dict[str, int] = defaultdict(int)
    by_cat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in txns:
        key = t.category.ato_key
        c = apply_percent(t.amount_cents, t.deductible_percent)
        gross[key] += t.amount_cents
        claim[key] += c
        by_cat[key][t.category.name] += c

    def lines(kind: str):
        rows = []
        for a in ATO_LABELS:
            if a.kind != kind:
                continue
            rows.append({
                "key": a.key, "label": a.label,
                "amount": from_cents(claim.get(a.key, 0)),
                "gross_amount": from_cents(gross.get(a.key, 0)),
                "categories": [{"name": n, "amount": from_cents(v)} for n, v in sorted(by_cat[a.key].items())],
            })
        return rows

    income = sum(v for k, v in claim.items() if ATO_BY_KEY[k].kind == "income")
    expenses = sum(v for k, v in claim.items() if ATO_BY_KEY[k].kind == "expense")
    excluded = sum(v for k, v in gross.items() if ATO_BY_KEY[k].kind == "excluded")
    net = income - expenses

    owners = [(o.owner.name, o.owner_id, o.share_percent) for o in prop.ownerships] or [("Owner (not set)", None, Decimal(100))]
    owner_rows = [{
        "owner_id": oid, "owner_name": name, "share_percent": float(pct),
        "income": from_cents(_share(income, pct)), "expenses": from_cents(_share(expenses, pct)),
        "net": from_cents(_share(income, pct) - _share(expenses, pct)),
    } for name, oid, pct in owners]

    py = db.scalar(select(PropertyYear).where(PropertyYear.property_id == prop.id, PropertyYear.fy == fy))
    _, fy_end = fy_bounds(fy)
    loans = []
    for l in db.scalars(select(Loan).where(Loan.property_id == prop.id)).all():
        bal = [b for b in l.balances if b.as_of <= fy_end and fy_of(b.as_of) == fy]
        b = bal[-1] if bal else None
        loans.append({
            "id": l.id, "name": l.name, "lender": l.lender, "account_hint": l.account_hint,
            "rental_use_percent": float(l.rental_use_percent),
            "balance": from_cents(b.balance_cents) if b else None,
            "balance_date": b.as_of if b else None,
            "interest_rate": float(b.interest_rate) if b and b.interest_rate is not None else None,
        })

    return {
        "property": {
            "id": prop.id, "name": prop.name, "address": full_address(prop),
            "purchase_date": prop.purchase_date, "purchase_price": from_cents(prop.purchase_price_cents),
            "first_rented_date": prop.first_rented_date,
        },
        "year": {
            "weeks_rented": py.weeks_rented if py else None,
            "weeks_available": py.weeks_available if py else None,
            "loan_refinanced": py.loan_refinanced if py else False,
            "notes": py.notes if py else None,
        },
        "income": lines("income"),
        "expenses": lines("expense"),
        "excluded": lines("excluded"),
        "totals": {"income": from_cents(income), "expenses": from_cents(expenses), "net": from_cents(net),
                   "excluded": from_cents(excluded)},
        "owners": owner_rows,
        "loans": loans,
        "transaction_count": len(txns),
        "checks": _checks(db, prop, fy, txns, py, claim),
    }


def fy_report(db: Session, user: User, fy: int, property_id: int | None = None) -> dict:
    txns = fy_transactions(db, user, fy, property_id)
    by_prop: dict[int, list[Transaction]] = defaultdict(list)
    for t in txns:
        by_prop[t.property_id].append(t)
    q = select(Property).where(Property.portfolio_id == user.portfolio_id)
    if property_id:
        q = q.where(Property.id == property_id)
    props = [p for p in db.scalars(q.order_by(Property.name)).all() if not p.archived or by_prop.get(p.id)]
    reports = [property_fy_report(db, user, p, fy, by_prop.get(p.id, [])) for p in props]

    owner_totals: dict[str, dict] = {}
    for r in reports:
        for o in r["owners"]:
            ot = owner_totals.setdefault(o["owner_name"], {"owner_name": o["owner_name"], "income": 0.0, "expenses": 0.0, "net": 0.0})
            for k in ("income", "expenses", "net"):
                ot[k] = round(ot[k] + o[k], 2)

    start, end = fy_bounds(fy)
    return {
        "fy": fy, "fy_label": fy_label(fy), "start": start, "end": end,
        "properties": reports,
        "totals": {
            k: round(sum(r["totals"][k] for r in reports), 2) for k in ("income", "expenses", "net", "excluded")
        },
        "owners": list(owner_totals.values()),
    }


def multi_year(db: Session, user: User, property_id: int | None = None) -> list[dict]:
    q = select(Transaction).where(Transaction.portfolio_id == user.portfolio_id)
    if property_id:
        q = q.where(Transaction.property_id == property_id)
    years: dict[int, dict] = {}
    for t in db.scalars(q).unique().all():
        fy = fy_of(t.date)
        y = years.setdefault(fy, {"fy": fy, "fy_label": fy_label(fy), "income": 0, "expenses": 0, "by_label": defaultdict(int)})
        kind = ATO_BY_KEY[t.category.ato_key].kind
        c = apply_percent(t.amount_cents, t.deductible_percent)
        if kind == "income":
            y["income"] += c
        elif kind == "expense":
            y["expenses"] += c
            y["by_label"][t.category.ato_key] += c
    out = []
    for fy in sorted(years):
        y = years[fy]
        out.append({
            "fy": fy, "fy_label": y["fy_label"], "income": from_cents(y["income"]),
            "expenses": from_cents(y["expenses"]), "net": from_cents(y["income"] - y["expenses"]),
            "by_label": {k: from_cents(v) for k, v in y["by_label"].items()},
        })
    return out


def monthly(db: Session, user: User, fy: int, property_id: int | None = None) -> list[dict]:
    start, _ = fy_bounds(fy)
    buckets = []
    y, m = start.year, start.month
    for _ in range(12):
        buckets.append({"month": f"{y}-{m:02d}", "label": date(y, m, 1).strftime("%b"), "income": 0, "expenses": 0})
        m += 1
        if m == 13:
            y, m = y + 1, 1
    idx = {b["month"]: b for b in buckets}
    for t in fy_transactions(db, user, fy, property_id):
        b = idx[f"{t.date.year}-{t.date.month:02d}"]
        kind = ATO_BY_KEY[t.category.ato_key].kind
        c = apply_percent(t.amount_cents, t.deductible_percent)
        if kind == "income":
            b["income"] += c
        elif kind == "expense":
            b["expenses"] += c
    for b in buckets:
        b["income"] = from_cents(b["income"])
        b["expenses"] = from_cents(b["expenses"])
    return buckets
