"""Database models.

Money is stored as integer cents. Every business record hangs off a Portfolio
so the app can later host several owners/entities (or a property manager's
clients) in one instance without a schema rewrite.
"""
from __future__ import annotations

import datetime as dt
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    # admin: everything incl. users | editor: manage data | viewer: read + reports (e.g. your accountant)
    role: Mapped[str] = mapped_column(String(20), default="editor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Owner(Base):
    """A legal owner of one or more properties (for splitting income/expenses)."""

    __tablename__ = "owners"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    address_line: Mapped[str | None] = mapped_column(String(255))
    suburb: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(10))
    postcode: Mapped[str | None] = mapped_column(String(10))
    property_type: Mapped[str | None] = mapped_column(String(40))
    purchase_date: Mapped[dt.date | None] = mapped_column(Date)
    purchase_price_cents: Mapped[int | None] = mapped_column(Integer)
    first_rented_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ownerships: Mapped[list[PropertyOwnership]] = relationship(
        back_populates="property", cascade="all, delete-orphan", lazy="selectin"
    )
    loans: Mapped[list[Loan]] = relationship(back_populates="property", cascade="all, delete-orphan")


class PropertyOwnership(Base):
    __tablename__ = "property_ownerships"
    __table_args__ = (UniqueConstraint("property_id", "owner_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id", ondelete="CASCADE"))
    share_percent: Mapped[Decimal] = mapped_column(Numeric(6, 3))

    property: Mapped[Property] = relationship(back_populates="ownerships")
    owner: Mapped[Owner] = relationship(lazy="joined")


class PropertyYear(Base):
    """Per-financial-year facts the rental schedule asks for."""

    __tablename__ = "property_years"
    __table_args__ = (UniqueConstraint("property_id", "fy"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    fy: Mapped[int] = mapped_column(Integer)  # year the FY ends in
    weeks_rented: Mapped[int | None] = mapped_column(Integer)
    weeks_available: Mapped[int | None] = mapped_column(Integer)
    loan_refinanced: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)  # notes for the accountant


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    ato_key: Mapped[str] = mapped_column(String(40))
    keywords: Mapped[str | None] = mapped_column(Text)  # comma separated, used by the importer
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    # Always positive; income/expense comes from the category's ATO label.
    amount_cents: Mapped[int] = mapped_column(Integer)
    # Share of the amount that is deductible/assessable (e.g. 80 if a loan is partly private).
    deductible_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100"))
    description: Mapped[str | None] = mapped_column(String(500))
    payee: Mapped[str | None] = mapped_column(String(200))
    reference: Mapped[str | None] = mapped_column(String(120))
    period_start: Mapped[dt.date | None] = mapped_column(Date)
    period_end: Mapped[dt.date | None] = mapped_column(Date)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    category: Mapped[Category] = relationship(lazy="joined")
    property: Mapped[Property] = relationship(lazy="joined")
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    transaction: Mapped[Transaction | None] = relationship(back_populates="attachments")


class Loan(Base):
    __tablename__ = "loans"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    lender: Mapped[str | None] = mapped_column(String(120))
    # A label such as "ends 4417" – never store full account numbers.
    account_hint: Mapped[str | None] = mapped_column(String(40))
    start_date: Mapped[dt.date | None] = mapped_column(Date)
    original_amount_cents: Mapped[int | None] = mapped_column(Integer)
    # % of the loan used for the rental (rest is private and not deductible).
    rental_use_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100"))
    notes: Mapped[str | None] = mapped_column(Text)

    property: Mapped[Property] = relationship(back_populates="loans")
    balances: Mapped[list[LoanBalance]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", lazy="selectin", order_by="LoanBalance.as_of"
    )


class LoanBalance(Base):
    __tablename__ = "loan_balances"
    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"), index=True)
    as_of: Mapped[dt.date] = mapped_column(Date)
    balance_cents: Mapped[int] = mapped_column(Integer)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))

    loan: Mapped[Loan] = relationship(back_populates="balances")
