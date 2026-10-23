from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ato import ATO_BY_KEY, ATO_LABELS
from ..db import get_db
from ..models import Category, Owner, Property, PropertyOwnership, PropertyYear, Transaction, User
from ..money import to_cents
from ..schemas import (
    CategoryIn,
    CategoryOut,
    OwnerIn,
    OwnerOut,
    PropertyIn,
    PropertyOut,
    PropertyYearIn,
    PropertyYearOut,
)
from ..security import can_edit, can_view
from ..serialize import category_out, property_out

router = APIRouter(prefix="/api", tags=["setup"])


def get_property(db: Session, user: User, property_id: int) -> Property:
    p = db.get(Property, property_id)
    if not p or p.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Property not found")
    return p


def get_category(db: Session, user: User, category_id: int) -> Category:
    c = db.get(Category, category_id)
    if not c or c.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Category not found")
    return c


# ---- owners ------------------------------------------------------------
@router.get("/owners", response_model=list[OwnerOut])
def list_owners(user: User = Depends(can_view), db: Session = Depends(get_db)):
    return db.scalars(select(Owner).where(Owner.portfolio_id == user.portfolio_id).order_by(Owner.name)).all()


@router.post("/owners", response_model=OwnerOut, status_code=201)
def create_owner(body: OwnerIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    o = Owner(portfolio_id=user.portfolio_id, **body.model_dump())
    db.add(o)
    db.commit()
    return o


@router.put("/owners/{owner_id}", response_model=OwnerOut)
def update_owner(owner_id: int, body: OwnerIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    o = db.get(Owner, owner_id)
    if not o or o.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Owner not found")
    for k, v in body.model_dump().items():
        setattr(o, k, v)
    db.commit()
    return o


@router.delete("/owners/{owner_id}", status_code=204)
def delete_owner(owner_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    o = db.get(Owner, owner_id)
    if not o or o.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "Owner not found")
    if db.scalar(select(func.count()).select_from(PropertyOwnership).where(PropertyOwnership.owner_id == o.id)):
        raise HTTPException(400, "Remove this owner from their properties first")
    db.delete(o)
    db.commit()


# ---- properties --------------------------------------------------------
def _apply_property(db: Session, user: User, p: Property, body: PropertyIn) -> None:
    data = body.model_dump(exclude={"ownerships", "purchase_price"})
    for k, v in data.items():
        setattr(p, k, v)
    p.purchase_price_cents = to_cents(body.purchase_price) if body.purchase_price is not None else None
    if body.ownerships is not None:
        p.ownerships.clear()
        db.flush()
        for o in body.ownerships:
            owner = db.get(Owner, o.owner_id)
            if not owner or owner.portfolio_id != user.portfolio_id:
                raise HTTPException(400, f"Unknown owner {o.owner_id}")
            p.ownerships.append(PropertyOwnership(owner_id=o.owner_id, share_percent=o.share_percent))


@router.get("/properties", response_model=list[PropertyOut])
def list_properties(include_archived: bool = False, user: User = Depends(can_view), db: Session = Depends(get_db)):
    q = select(Property).where(Property.portfolio_id == user.portfolio_id)
    if not include_archived:
        q = q.where(Property.archived.is_(False))
    return [property_out(p) for p in db.scalars(q.order_by(Property.name)).all()]


@router.get("/properties/{property_id}", response_model=PropertyOut)
def read_property(property_id: int, user: User = Depends(can_view), db: Session = Depends(get_db)):
    return property_out(get_property(db, user, property_id))


@router.post("/properties", response_model=PropertyOut, status_code=201)
def create_property(body: PropertyIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    p = Property(portfolio_id=user.portfolio_id, name=body.name)
    db.add(p)
    _apply_property(db, user, p, body)
    db.commit()
    db.refresh(p)
    return property_out(p)


@router.put("/properties/{property_id}", response_model=PropertyOut)
def update_property(property_id: int, body: PropertyIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    p = get_property(db, user, property_id)
    _apply_property(db, user, p, body)
    db.commit()
    db.refresh(p)
    return property_out(p)


@router.delete("/properties/{property_id}", status_code=204)
def delete_property(property_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    p = get_property(db, user, property_id)
    if db.scalar(select(func.count()).select_from(Transaction).where(Transaction.property_id == p.id)):
        raise HTTPException(400, "This property has transactions – archive it instead of deleting")
    db.delete(p)
    db.commit()


@router.get("/properties/{property_id}/years/{fy}", response_model=PropertyYearOut)
def get_property_year(property_id: int, fy: int, user: User = Depends(can_view), db: Session = Depends(get_db)):
    get_property(db, user, property_id)
    py = db.scalar(select(PropertyYear).where(PropertyYear.property_id == property_id, PropertyYear.fy == fy))
    if not py:
        return PropertyYearOut(fy=fy, property_id=property_id)
    return PropertyYearOut(fy=fy, property_id=property_id, weeks_rented=py.weeks_rented,
                           weeks_available=py.weeks_available, loan_refinanced=py.loan_refinanced, notes=py.notes)


@router.put("/properties/{property_id}/years/{fy}", response_model=PropertyYearOut)
def put_property_year(property_id: int, fy: int, body: PropertyYearIn, user: User = Depends(can_edit),
                      db: Session = Depends(get_db)):
    get_property(db, user, property_id)
    py = db.scalar(select(PropertyYear).where(PropertyYear.property_id == property_id, PropertyYear.fy == fy))
    if not py:
        py = PropertyYear(property_id=property_id, fy=fy)
        db.add(py)
    for k, v in body.model_dump().items():
        setattr(py, k, v)
    db.commit()
    return PropertyYearOut(fy=fy, property_id=property_id, **body.model_dump())


# ---- categories --------------------------------------------------------
@router.get("/ato-labels")
def ato_labels():
    return [{"key": a.key, "label": a.label, "kind": a.kind, "order": a.order, "help": a.help} for a in ATO_LABELS]


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(user: User = Depends(can_view), db: Session = Depends(get_db)):
    cats = db.scalars(select(Category).where(Category.portfolio_id == user.portfolio_id)
                      .order_by(Category.sort_order, Category.name)).all()
    return [category_out(c) for c in cats]


def _check_ato(key: str) -> None:
    if key not in ATO_BY_KEY:
        raise HTTPException(400, f"Unknown ATO label '{key}'")


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    _check_ato(body.ato_key)
    c = Category(portfolio_id=user.portfolio_id, **body.model_dump())
    db.add(c)
    db.commit()
    return category_out(c)


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryIn, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    _check_ato(body.ato_key)
    c = get_category(db, user, category_id)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    return category_out(c)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, user: User = Depends(can_edit), db: Session = Depends(get_db)):
    c = get_category(db, user, category_id)
    if db.scalar(select(func.count()).select_from(Transaction).where(Transaction.category_id == c.id)):
        raise HTTPException(400, "This category is in use – archive it or move its transactions first")
    db.delete(c)
    db.commit()
