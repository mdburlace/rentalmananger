from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..fy import current_fy, fy_label
from ..models import ImportBatch, Transaction, User
from ..security import can_edit, can_view
from ..serialize import transaction_out
from ..services import export, importer, reports
from .properties import get_property

router = APIRouter(prefix="/api", tags=["reports"])


def _prop_suffix(db: Session, user: User, property_id: int | None) -> str:
    if not property_id:
        return ""
    return " " + get_property(db, user, property_id).name


@router.get("/reports/fy")
def fy_report(fy: int, property_id: int | None = None, user: User = Depends(can_view), db: Session = Depends(get_db)):
    if property_id:
        get_property(db, user, property_id)
    return reports.fy_report(db, user, fy, property_id)


@router.get("/reports/years")
def years(property_id: int | None = None, user: User = Depends(can_view), db: Session = Depends(get_db)):
    return reports.multi_year(db, user, property_id)


@router.get("/reports/fy/export.xlsx")
def export_xlsx(fy: int, property_id: int | None = None, user: User = Depends(can_view), db: Session = Depends(get_db)):
    name = f"Rental schedule FY{fy_label(fy)}{_prop_suffix(db, user, property_id)}.xlsx"
    return Response(export.build_workbook(db, user, fy, property_id),
                     media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/reports/fy/export.csv")
def export_csv(fy: int, property_id: int | None = None, user: User = Depends(can_view), db: Session = Depends(get_db)):
    name = f"Transactions FY{fy_label(fy)}{_prop_suffix(db, user, property_id)}.csv"
    return Response(export.transactions_csv(db, user, fy, property_id), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/reports/fy/pack.zip")
def export_pack(fy: int, property_id: int | None = None, user: User = Depends(can_view), db: Session = Depends(get_db)):
    name = f"Accountant pack FY{fy_label(fy)}{_prop_suffix(db, user, property_id)}.zip"
    return Response(export.accountant_pack(db, user, fy, property_id), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/dashboard")
def dashboard(fy: int | None = None, property_id: int | None = None, user: User = Depends(can_view),
              db: Session = Depends(get_db)):
    fy = fy or current_fy()
    rep = reports.fy_report(db, user, fy, property_id)
    expense_lines: dict[str, dict] = {}
    for p in rep["properties"]:
        for l in p["expenses"]:
            if l["amount"]:
                e = expense_lines.setdefault(l["key"], {"key": l["key"], "label": l["label"], "amount": 0.0})
                e["amount"] = round(e["amount"] + l["amount"], 2)
    recent = db.scalars(select(Transaction).where(Transaction.portfolio_id == user.portfolio_id)
                        .order_by(Transaction.created_at.desc()).limit(8)).unique().all()
    review = db.scalar(select(func.count()).select_from(Transaction).where(
        Transaction.portfolio_id == user.portfolio_id, Transaction.needs_review.is_(True)))
    return {
        "fy": fy, "fy_label": fy_label(fy), "current_fy": current_fy(),
        "totals": rep["totals"],
        "expenses_by_label": sorted(expense_lines.values(), key=lambda x: -x["amount"]),
        "monthly": reports.monthly(db, user, fy, property_id),
        "years": reports.multi_year(db, user, property_id),
        "checks": [{"property": p["property"]["name"], **c} for p in rep["properties"] for c in p["checks"]],
        "needs_review": review,
        "recent": [transaction_out(t) for t in recent],
    }


# ---- imports -----------------------------------------------------------
@router.post("/imports/preview")
async def import_preview(property_id: int = Form(...), file: UploadFile = File(...), user: User = Depends(can_edit),
                         db: Session = Depends(get_db)):
    get_property(db, user, property_id)
    name = file.filename or "upload"
    if not name.lower().endswith((".xlsx", ".xlsm", ".csv", ".txt")):
        raise HTTPException(400, "Upload an Excel (.xlsx) or CSV file")
    data = await file.read()
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File is too large")
    try:
        return importer.preview(db, user, property_id, data, name)
    except Exception as e:  # corrupt / unexpected file
        raise HTTPException(400, f"Couldn't read that file: {e}")


class CommitIn(BaseModel):
    property_id: int
    filename: str
    rows: list[dict]
    learn_mappings: bool = True


@router.post("/imports/commit")
def import_commit(body: CommitIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    get_property(db, user, body.property_id)
    try:
        return importer.commit(db, user, body.property_id, body.filename, body.rows, body.learn_mappings)
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.get("/imports")
def list_imports(user: User = Depends(can_view), db: Session = Depends(get_db)):
    batches = db.scalars(select(ImportBatch).where(ImportBatch.portfolio_id == user.portfolio_id)
                         .order_by(ImportBatch.created_at.desc())).all()
    out = []
    for b in batches:
        remaining = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.import_batch_id == b.id))
        out.append({"id": b.id, "filename": b.filename, "row_count": b.row_count, "remaining": remaining,
                    "created_at": b.created_at})
    return out


@router.delete("/imports/{batch_id}")
def undo_import(batch_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    b = db.get(ImportBatch, batch_id)
    if not b or b.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Import not found")
    txns = db.scalars(select(Transaction).where(Transaction.import_batch_id == b.id)).unique().all()
    files = [a.stored_name for t in txns for a in t.attachments]
    for t in txns:
        db.delete(t)
    db.delete(b)
    db.commit()
    for f in files:
        (get_settings().uploads_dir / f).unlink(missing_ok=True)
    return {"deleted": len(txns)}


@router.get("/fy/current")
def fy_current():
    fy = current_fy()
    return {"fy": fy, "label": fy_label(fy), "today": date.today()}
