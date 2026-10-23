"""API request/response shapes. Amounts are dollars in the API, cents in the DB."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth / users -------------------------------------------------------
class SetupIn(BaseModel):
    portfolio_name: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(ORM):
    id: int
    email: str
    name: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern="^(admin|editor|viewer)$")
    password: str = Field(min_length=8, max_length=200)


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|editor|viewer)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


# ---- owners / properties ------------------------------------------------
class OwnerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = None
    notes: str | None = None


class OwnerOut(ORM):
    id: int
    name: str
    email: str | None
    notes: str | None


class OwnershipIn(BaseModel):
    owner_id: int
    share_percent: Decimal = Field(gt=0, le=100)


class OwnershipOut(BaseModel):
    owner_id: int
    owner_name: str
    share_percent: float


class PropertyIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address_line: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    property_type: str | None = None
    purchase_date: dt.date | None = None
    purchase_price: Decimal | None = None
    first_rented_date: dt.date | None = None
    notes: str | None = None
    archived: bool = False
    ownerships: list[OwnershipIn] | None = None

    @field_validator("ownerships")
    @classmethod
    def _shares_total_100(cls, v):
        if v:
            total = sum(o.share_percent for o in v)
            if abs(total - 100) > Decimal("0.01"):
                raise ValueError(f"ownership shares must add up to 100% (currently {total}%)")
        return v


class PropertyOut(BaseModel):
    id: int
    name: str
    address_line: str | None
    suburb: str | None
    state: str | None
    postcode: str | None
    property_type: str | None
    purchase_date: dt.date | None
    purchase_price: float | None
    first_rented_date: dt.date | None
    notes: str | None
    archived: bool
    ownerships: list[OwnershipOut]
    full_address: str


class PropertyYearIn(BaseModel):
    weeks_rented: int | None = Field(default=None, ge=0, le=53)
    weeks_available: int | None = Field(default=None, ge=0, le=53)
    loan_refinanced: bool = False
    notes: str | None = None


class PropertyYearOut(PropertyYearIn):
    fy: int
    property_id: int


# ---- categories ---------------------------------------------------------
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    ato_key: str
    keywords: str | None = None
    archived: bool = False
    sort_order: int = 100


class CategoryOut(ORM):
    id: int
    name: str
    ato_key: str
    ato_label: str
    kind: str
    keywords: str | None
    archived: bool
    sort_order: int


# ---- transactions -------------------------------------------------------
class TransactionIn(BaseModel):
    property_id: int
    category_id: int
    date: dt.date
    amount: Decimal = Field(gt=0)
    deductible_percent: Decimal = Field(default=Decimal("100"), ge=0, le=100)
    description: str | None = Field(default=None, max_length=500)
    payee: str | None = Field(default=None, max_length=200)
    reference: str | None = Field(default=None, max_length=120)
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    needs_review: bool = False
    owner_id: int | None = None
    notes: str | None = None


class TransactionPatch(BaseModel):
    property_id: int | None = None
    category_id: int | None = None
    date: dt.date | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    deductible_percent: Decimal | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    payee: str | None = None
    reference: str | None = None
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    needs_review: bool | None = None
    owner_id: int | None = None
    notes: str | None = None


class AttachmentOut(ORM):
    id: int
    filename: str
    content_type: str | None
    size_bytes: int


class TransactionOut(BaseModel):
    id: int
    property_id: int
    property_name: str
    category_id: int
    category_name: str
    ato_key: str
    kind: str
    date: dt.date
    fy: int
    amount: float
    deductible_percent: float
    claimable_amount: float
    description: str | None
    payee: str | None
    reference: str | None
    period_start: dt.date | None
    period_end: dt.date | None
    needs_review: bool
    owner_id: int | None
    owner_name: str | None
    notes: str | None
    source: str
    attachments: list[AttachmentOut]


class BulkUpdate(BaseModel):
    ids: list[int]
    category_id: int | None = None
    property_id: int | None = None
    needs_review: bool | None = None
    delete: bool = False


# ---- loans --------------------------------------------------------------
class LoanBalanceIn(BaseModel):
    as_of: dt.date
    balance: Decimal
    interest_rate: Decimal | None = None


class LoanBalanceOut(BaseModel):
    id: int
    as_of: dt.date
    balance: float
    interest_rate: float | None


class LoanIn(BaseModel):
    property_id: int
    name: str = Field(min_length=1, max_length=120)
    lender: str | None = None
    account_hint: str | None = Field(default=None, max_length=40)
    start_date: dt.date | None = None
    original_amount: Decimal | None = None
    rental_use_percent: Decimal = Field(default=Decimal("100"), ge=0, le=100)
    notes: str | None = None


class LoanOut(BaseModel):
    id: int
    property_id: int
    name: str
    lender: str | None
    account_hint: str | None
    start_date: dt.date | None
    original_amount: float | None
    rental_use_percent: float
    notes: str | None
    balances: list[LoanBalanceOut]
