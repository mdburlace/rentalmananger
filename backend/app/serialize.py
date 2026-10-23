from __future__ import annotations

from .ato import ATO_BY_KEY
from .fy import fy_of
from .models import Category, Loan, Property, Transaction
from .money import apply_percent, from_cents
from .schemas import (
    AttachmentOut,
    CategoryOut,
    LoanBalanceOut,
    LoanOut,
    OwnershipOut,
    PropertyOut,
    TransactionOut,
)


def full_address(p: Property) -> str:
    parts = [p.address_line, " ".join(x for x in [p.suburb, p.state, p.postcode] if x)]
    return ", ".join(x for x in parts if x) or p.name


def property_out(p: Property) -> PropertyOut:
    return PropertyOut(
        id=p.id,
        name=p.name,
        address_line=p.address_line,
        suburb=p.suburb,
        state=p.state,
        postcode=p.postcode,
        property_type=p.property_type,
        purchase_date=p.purchase_date,
        purchase_price=from_cents(p.purchase_price_cents),
        first_rented_date=p.first_rented_date,
        notes=p.notes,
        archived=p.archived,
        ownerships=[
            OwnershipOut(owner_id=o.owner_id, owner_name=o.owner.name, share_percent=float(o.share_percent))
            for o in p.ownerships
        ],
        full_address=full_address(p),
    )


def category_out(c: Category) -> CategoryOut:
    label = ATO_BY_KEY.get(c.ato_key)
    return CategoryOut(
        id=c.id,
        name=c.name,
        ato_key=c.ato_key,
        ato_label=label.label if label else c.ato_key,
        kind=label.kind if label else "expense",
        keywords=c.keywords,
        archived=c.archived,
        sort_order=c.sort_order,
    )


def transaction_out(t: Transaction) -> TransactionOut:
    label = ATO_BY_KEY.get(t.category.ato_key)
    return TransactionOut(
        id=t.id,
        property_id=t.property_id,
        property_name=t.property.name,
        category_id=t.category_id,
        category_name=t.category.name,
        ato_key=t.category.ato_key,
        kind=label.kind if label else "expense",
        date=t.date,
        fy=fy_of(t.date),
        amount=from_cents(t.amount_cents),
        deductible_percent=float(t.deductible_percent),
        claimable_amount=from_cents(apply_percent(t.amount_cents, t.deductible_percent)),
        description=t.description,
        payee=t.payee,
        reference=t.reference,
        period_start=t.period_start,
        period_end=t.period_end,
        needs_review=t.needs_review,
        owner_id=t.owner_id,
        owner_name=t.owner.name if t.owner else None,
        notes=t.notes,
        source=t.source,
        attachments=[AttachmentOut.model_validate(a) for a in t.attachments],
    )


def loan_out(l: Loan) -> LoanOut:
    return LoanOut(
        id=l.id,
        property_id=l.property_id,
        name=l.name,
        lender=l.lender,
        account_hint=l.account_hint,
        start_date=l.start_date,
        original_amount=from_cents(l.original_amount_cents),
        rental_use_percent=float(l.rental_use_percent),
        notes=l.notes,
        balances=[
            LoanBalanceOut(
                id=b.id,
                as_of=b.as_of,
                balance=from_cents(b.balance_cents),
                interest_rate=float(b.interest_rate) if b.interest_rate is not None else None,
            )
            for b in l.balances
        ],
    )
