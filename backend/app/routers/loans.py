from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Loan, LoanBalance, Property, User
from ..money import to_cents
from ..schemas import LoanBalanceIn, LoanIn, LoanOut
from ..security import can_edit, can_view
from ..serialize import loan_out
from .properties import get_property

router = APIRouter(prefix="/api/loans", tags=["loans"])


def get_loan(db: Session, user: User, loan_id: int) -> Loan:
    l = db.get(Loan, loan_id)
    if not l or l.property.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Loan not found")
    return l


def _apply(l: Loan, body: LoanIn) -> None:
    for k, v in body.model_dump(exclude={"original_amount"}).items():
        setattr(l, k, v)
    l.original_amount_cents = to_cents(body.original_amount) if body.original_amount is not None else None


@router.get("", response_model=list[LoanOut])
def list_loans(property_id: int | None = None, user: User = Depends(can_view), db: Session = Depends(get_db)):
    q = select(Loan).join(Loan.property).where(Property.portfolio_id == user.portfolio_id)
    if property_id:
        q = q.where(Loan.property_id == property_id)
    return [loan_out(l) for l in db.scalars(q.order_by(Loan.name)).all()]


@router.post("", response_model=LoanOut, status_code=201)
def create_loan(body: LoanIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    get_property(db, user, body.property_id)
    l = Loan(property_id=body.property_id, name=body.name)
    _apply(l, body)
    db.add(l)
    db.commit()
    db.refresh(l)
    return loan_out(l)


@router.put("/{loan_id}", response_model=LoanOut)
def update_loan(loan_id: int, body: LoanIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    l = get_loan(db, user, loan_id)
    get_property(db, user, body.property_id)
    _apply(l, body)
    db.commit()
    db.refresh(l)
    return loan_out(l)


@router.delete("/{loan_id}", status_code=204)
def delete_loan(loan_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    db.delete(get_loan(db, user, loan_id))
    db.commit()


@router.post("/{loan_id}/balances", response_model=LoanOut, status_code=201)
def add_balance(loan_id: int, body: LoanBalanceIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    l = get_loan(db, user, loan_id)
    existing = next((b for b in l.balances if b.as_of == body.as_of), None)
    if existing:
        existing.balance_cents = to_cents(body.balance)
        existing.interest_rate = body.interest_rate
    else:
        l.balances.append(LoanBalance(as_of=body.as_of, balance_cents=to_cents(body.balance),
                                      interest_rate=body.interest_rate))
    db.commit()
    db.refresh(l)
    return loan_out(l)


@router.delete("/{loan_id}/balances/{balance_id}", status_code=204)
def delete_balance(loan_id: int, balance_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    l = get_loan(db, user, loan_id)
    b = next((b for b in l.balances if b.id == balance_id), None)
    if not b:
        raise HTTPException(404, "Balance not found")
    l.balances.remove(b)
    db.commit()
