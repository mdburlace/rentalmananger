from __future__ import annotations

import datetime as dt
import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..ato import ATO_BY_KEY, TRANSFER_KEYS
from ..config import get_settings
from ..db import get_db
from ..fy import fy_bounds
from ..models import Attachment, Category, Owner, Transaction, User
from ..money import to_cents
from ..schemas import AttachmentOut, BulkUpdate, TransactionIn, TransactionOut, TransactionPatch
from ..security import can_edit, can_view
from ..serialize import transaction_out
from .properties import get_category, get_property

router = APIRouter(prefix="/api", tags=["transactions"])

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/heic", "image/heif", "image/webp", "image/gif",
    "text/plain", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword",
    "application/vnd.ms-excel", "message/rfc822",
}


def get_txn(db: Session, user: User, txn_id: int) -> Transaction:
    t = db.get(Transaction, txn_id)
    if not t or t.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Transaction not found")
    return t


def check_owner(db: Session, user: User, t: Transaction) -> None:
    """Owner contributions/drawings must name an owner of that property; other
    transactions don't carry an owner."""
    cat = db.get(Category, t.category_id)
    if cat.ato_key not in TRANSFER_KEYS:
        t.owner_id = None
        return
    if not t.owner_id:
        raise HTTPException(400, "Choose which owner put in or took out the money")
    owner = db.get(Owner, t.owner_id)
    if not owner or owner.portfolio_id != user.portfolio_id:
        raise HTTPException(400, "Unknown owner")
    prop = get_property(db, user, t.property_id)
    if prop.ownerships and t.owner_id not in {o.owner_id for o in prop.ownerships}:
        raise HTTPException(400, f"{owner.name} isn't an owner of {prop.name}")
    t.deductible_percent = 100


def filtered_query(user: User, *, fy: int | None = None, property_id: int | None = None,
                   category_id: int | None = None, kind: str | None = None, q: str | None = None,
                   needs_review: bool | None = None, missing_receipt: bool | None = None,
                   date_from: dt.date | None = None, date_to: dt.date | None = None):
    stmt = select(Transaction).join(Transaction.category).where(Transaction.portfolio_id == user.portfolio_id)
    if fy:
        start, end = fy_bounds(fy)
        stmt = stmt.where(Transaction.date >= start, Transaction.date <= end)
    if date_from:
        stmt = stmt.where(Transaction.date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.date <= date_to)
    if property_id:
        stmt = stmt.where(Transaction.property_id == property_id)
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    if kind:
        keys = [k for k, a in ATO_BY_KEY.items() if a.kind == kind]
        stmt = stmt.where(Category.ato_key.in_(keys))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Transaction.description.ilike(like), Transaction.payee.ilike(like),
                              Transaction.reference.ilike(like), Transaction.notes.ilike(like),
                              Category.name.ilike(like)))
    if needs_review is not None:
        stmt = stmt.where(Transaction.needs_review.is_(needs_review))
    if missing_receipt:
        has_att = select(Attachment.id).where(Attachment.transaction_id == Transaction.id).exists()
        stmt = stmt.where(~has_att)
    return stmt


@router.get("/transactions")
def list_transactions(
    fy: int | None = None, property_id: int | None = None, category_id: int | None = None,
    kind: str | None = Query(default=None, pattern="^(income|expense|excluded|transfer)$"), q: str | None = None,
    needs_review: bool | None = None, missing_receipt: bool | None = None,
    date_from: dt.date | None = None, date_to: dt.date | None = None,
    limit: int = Query(default=500, le=5000), offset: int = 0,
    user: User = Depends(can_view), db: Session = Depends(get_db),
):
    stmt = filtered_query(user, fy=fy, property_id=property_id, category_id=category_id, kind=kind, q=q,
                          needs_review=needs_review, missing_receipt=missing_receipt,
                          date_from=date_from, date_to=date_to)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).offset(offset)).unique().all()
    items = [transaction_out(t) for t in rows]
    return {"total": total, "items": items}


@router.get("/transactions/{txn_id}", response_model=TransactionOut)
def read_transaction(txn_id: int, user: User = Depends(can_view), db: Session = Depends(get_db)):
    return transaction_out(get_txn(db, user, txn_id))


@router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    get_property(db, user, body.property_id)
    get_category(db, user, body.category_id)
    data = body.model_dump(exclude={"amount"})
    t = Transaction(portfolio_id=user.portfolio_id, amount_cents=to_cents(body.amount), created_by=user.id, **data)
    check_owner(db, user, t)
    db.add(t)
    db.commit()
    db.refresh(t)
    return transaction_out(t)


@router.patch("/transactions/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: int, body: TransactionPatch, user: User = Depends(can_edit),
                       db: Session = Depends(get_db)):
    t = get_txn(db, user, txn_id)
    data = body.model_dump(exclude_unset=True)
    if "property_id" in data:
        get_property(db, user, data["property_id"])
    if "category_id" in data:
        get_category(db, user, data["category_id"])
    if "amount" in data:
        t.amount_cents = to_cents(data.pop("amount"))
    for k, v in data.items():
        setattr(t, k, v)
    check_owner(db, user, t)
    db.commit()
    db.refresh(t)
    return transaction_out(t)


def _delete_files(atts: list[Attachment]) -> None:
    up = get_settings().uploads_dir
    for a in atts:
        (up / a.stored_name).unlink(missing_ok=True)


@router.delete("/transactions/{txn_id}", status_code=204)
def delete_transaction(txn_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    t = get_txn(db, user, txn_id)
    atts = list(t.attachments)
    db.delete(t)
    db.commit()
    _delete_files(atts)


@router.post("/transactions/bulk")
def bulk_update(body: BulkUpdate, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    txns = [get_txn(db, user, i) for i in body.ids]
    if body.delete:
        atts = [a for t in txns for a in t.attachments]
        for t in txns:
            db.delete(t)
        db.commit()
        _delete_files(atts)
        return {"deleted": len(txns)}
    if body.category_id:
        get_category(db, user, body.category_id)
    if body.property_id:
        get_property(db, user, body.property_id)
    for t in txns:
        if body.category_id:
            t.category_id = body.category_id
        if body.property_id:
            t.property_id = body.property_id
        if body.needs_review is not None:
            t.needs_review = body.needs_review
        try:
            check_owner(db, user, t)
        except HTTPException as e:
            db.rollback()
            raise HTTPException(400, f"{t.date:%d/%m/%Y} ${t.amount_cents / 100:,.2f}: {e.detail} – edit it individually")
    db.commit()
    return {"updated": len(txns)}


# ---- attachments (receipts, invoices, statements) ----------------------
@router.post("/transactions/{txn_id}/attachments", response_model=list[AttachmentOut], status_code=201)
async def upload_attachments(txn_id: int, files: list[UploadFile] = File(...), user: User = Depends(can_edit),
                             db: Session = Depends(get_db)):
    t = get_txn(db, user, txn_id)
    s = get_settings()
    out = []
    for f in files:
        ctype = f.content_type or mimetypes.guess_type(f.filename or "")[0] or "application/octet-stream"
        if ctype not in ALLOWED_TYPES:
            raise HTTPException(400, f"{f.filename}: file type {ctype} isn't supported")
        data = await f.read()
        if len(data) > s.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"{f.filename} is larger than {s.max_upload_mb} MB")
        ext = Path(f.filename or "").suffix.lower()[:10]
        stored = f"{uuid.uuid4().hex}{ext}"
        (s.uploads_dir / stored).write_bytes(data)
        a = Attachment(portfolio_id=user.portfolio_id, transaction_id=t.id, filename=Path(f.filename or "file").name,
                       stored_name=stored, content_type=ctype, size_bytes=len(data))
        db.add(a)
        out.append(a)
    db.commit()
    return out


def get_attachment(db: Session, user: User, att_id: int) -> Attachment:
    a = db.get(Attachment, att_id)
    if not a or a.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Attachment not found")
    return a


@router.get("/attachments/{att_id}")
def download_attachment(att_id: int, download: bool = False, user: User = Depends(can_view),
                        db: Session = Depends(get_db)):
    a = get_attachment(db, user, att_id)
    path = get_settings().uploads_dir / a.stored_name
    if not path.exists():
        raise HTTPException(404, "File is missing from storage")
    disp = "attachment" if download else "inline"
    return FileResponse(path, media_type=a.content_type, filename=a.filename, content_disposition_type=disp)


@router.delete("/attachments/{att_id}", status_code=204)
def delete_attachment(att_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    a = get_attachment(db, user, att_id)
    db.delete(a)
    db.commit()
    _delete_files([a])


@router.get("/categories/{category_id}/usage")
def category_usage(category_id: int, user: User = Depends(can_view), db: Session = Depends(get_db)):
    get_category(db, user, category_id)
    n = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.category_id == category_id))
    return {"transactions": n}


__all__ = ["router", "filtered_query", "Category"]
