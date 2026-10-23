# Architecture

```
┌────────────── Docker container ───────────────┐
│  FastAPI (Python 3.12)                        │
│   ├─ /api/*        JSON API (OpenAPI at /api/docs)
│   └─ /*            built React app (static)   │
│  SQLAlchemy 2 + Alembic migrations            │
└──────────────┬────────────────────────────────┘
               │ /data volume
               ├─ rental.db        (SQLite; Postgres via RM_DATABASE_URL)
               ├─ uploads/         receipts & documents (uuid filenames)
               └─ .secret_key      session signing key
```

One image, one volume – easy to run under Portainer and easy to back up. The API is
the contract: the web UI uses nothing the future mobile app, tenant/owner portals or
integrations couldn't also use.

## Code layout

| Path | What |
|---|---|
| `backend/app/models.py` | Database tables |
| `backend/app/ato.py` | ATO rental schedule labels + default categories and import keywords |
| `backend/app/fy.py` | Australian financial-year helpers |
| `backend/app/routers/` | API endpoints (auth/users, properties/owners/categories, transactions/attachments, loans, reports/imports/dashboard) |
| `backend/app/services/reports.py` | FY report, owner shares, pre-tax checks, multi-year and monthly summaries |
| `backend/app/services/export.py` | Excel workbook, CSV and accountant ZIP |
| `backend/app/services/importer.py` | Spreadsheet / CSV import (preview → commit) |
| `backend/migrations/` | Alembic migrations, run automatically at start-up |
| `frontend/src/pages/` | Dashboard, Transactions, Properties, Import, Reports, Settings, Roadmap |

## Data model

- **Portfolio** – the top-level owner of all records (a household or entity today; a property manager's client later). Every query is scoped to the signed-in user's portfolio.
- **User** – role `admin` (everything incl. users), `editor` (data), `viewer` (read + reports, e.g. the accountant).
- **Owner** / **PropertyOwnership** – legal owners and their % share of each property; shares must total 100%.
- **Property** / **PropertyYear** – property details and per-FY schedule facts (weeks rented/available, loan refinanced, notes).
- **Category** – user-named, mapped to one ATO label key (`ato.py`); `keywords` drive import matching and grow as the user corrects imports.
- **Transaction** – date, positive amount in cents, category (which decides income vs expense), claimable %, payee, reference, bill period, review flag, notes, source/import batch.
- **Attachment** – files stored under `/data/uploads` with random names; original filename kept for display and the accountant pack.
- **Loan** / **LoanBalance** – lender, account label (never full numbers), rental-use %, dated balances and rates.
- **ImportBatch** – groups imported rows so an import can be undone.

Design choices that keep the roadmap open:

- Money is integer cents everywhere; the API speaks dollars.
- Income/expense is derived from the category's ATO label, not stored per transaction, so recategorising is a single change.
- Portfolio scoping and roles exist from day one, ready for tenant/owner portals and agency mode.
- Import is two-step and stateless (preview → user edits → commit), the same shape a future bill-scanning or bank-feed inbox will use.

## Security notes

- Passwords hashed with bcrypt; sessions are signed JWTs in an HttpOnly, SameSite=Lax cookie (Secure when `RM_COOKIE_SECURE=true`).
- Uploads limited by type and size and stored with generated names; downloads require a session in the same portfolio.
- Run behind HTTPS. MFA/SSO are on the roadmap.
