# Rental Manager

A self-hosted app for managing rental properties, starting with what matters every
June: **capturing income and expenses and giving the accountant exactly what they
need** for the ATO rental property schedule.

It replaces the "one sheet per financial year" expenses spreadsheet with:

- **Income & expenses** per property, with receipts and invoices attached (photos or PDFs)
- **Categories mapped to ATO rental schedule labels** – call them whatever you like; reports always line up with the schedule
- **Ownership splits** (e.g. 50/50) so each owner's share is calculated for their own return
- **Owner funds** – record money an owner puts in to cover a shortfall (or takes out) against that owner; kept off the tax schedule and reported separately
- **Loans** with 30 June balances and interest rates; private-use apportionment for partly private loans or expenses
- **Spreadsheet import** – drop in the old workbooks (or a bank CSV), review every row, then import. Spots duplicates, rows with no date, loan balances mixed in with expenses, and the same bill counted in two years. One-click undo.
- **Tax reports** – totals by schedule label, net rent, owner shares, loan balances and a *check before sending* list (no rent recorded, missing interest months, unreviewed items, missing receipts)
- **Accountant pack** – one ZIP with an Excel report, a CSV of every transaction and all receipts, named and filed by property
- **Read-only login for your accountant**, plus admin / editor roles
- Works on a phone (installable web app) – snap a receipt as you pay a bill

See [docs/ROADMAP.md](docs/ROADMAP.md) for what comes next: recurring bills and bill scanning, rent collection, tenant and owner portals, maintenance, inspections, leasing and AI add-ons.

---

## Deploy with Portainer

**Option A – build from this repo (simplest)**

1. Portainer → **Stacks → Add stack → Repository**
2. Repository URL `https://github.com/mdburlace/rentalmananger`, reference `refs/heads/main`, compose path `docker-compose.yml`
3. Optional environment variables: `RM_PORT` (default `8085`), `RM_COOKIE_SECURE=true` once it's behind HTTPS
4. Deploy, then open `http://<server>:8085` – the first visit asks you to create your portfolio and admin login

**Option B – pull the published image**

Every push to `main` runs the tests and publishes `ghcr.io/mdburlace/rentalmananger:latest`.
In `docker-compose.yml`, replace `build: .` with `image: ghcr.io/mdburlace/rentalmananger:latest`.
(If the repo is private, add a GHCR registry in Portainer with a GitHub token that has `read:packages`.)

**Data & backups** – everything (SQLite database, uploaded receipts, generated session key) lives in the
`rentalmanager-data` volume mounted at `/data`. Back up that volume. Database migrations run automatically on start.

**HTTPS** – put it behind your reverse proxy (Nginx Proxy Manager, Traefik, Cloudflare Tunnel) and set
`RM_COOKIE_SECURE=true`. This app holds financial records, so don't expose it over plain HTTP.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `RM_DATA_DIR` | `/data` | Database, receipts and secrets |
| `RM_DATABASE_URL` | SQLite in data dir | e.g. `postgresql+psycopg://user:pass@db/rental` (add `psycopg[binary]` to requirements) |
| `RM_SECRET_KEY` | generated | Session signing key |
| `RM_COOKIE_SECURE` | `false` | `true` when served over HTTPS |
| `RM_SESSION_HOURS` | `336` | Sign-in lifetime |
| `RM_MAX_UPLOAD_MB` | `25` | Max receipt/import size |

---

## First run checklist

1. **Properties** → add the property (address, purchase date/price, date first rented)
2. Add the **owners** and set ownership shares
3. Add the **loan** and its 30 June balance(s)
4. **Import** → choose the property and drop in the old spreadsheet(s). Fix anything flagged, then import
5. Add **rent received** for each year (monthly, or the agent's EOFY statement total)
6. **Reports** → enter weeks rented / available, clear the checks, download the accountant pack
7. **Settings** → add your accountant as a read-only user if you'd like them to download it themselves

## How the numbers work

- Financial years run 1 July – 30 June and are labelled by the year they end (FY 2026 = 2025-26)
- Transactions are counted in the year they're **paid or received** (cash basis), which is how
  individual landlords report rental income. Bill periods can be recorded for reference.
- Amounts are entered including GST – residential rent is input-taxed, so there are no GST credits to separate
- *Claimable %* reduces a transaction to its deductible share (e.g. a loan partly used privately)
- Categories mapped to *Capital / non-deductible* (improvements, principal repayments) are tracked for the
  CGT cost base but excluded from the schedule totals
- *Owner contribution* / *Owner drawing* record money moving between an owner and the property. They name the
  owner, never count as income or expenses, and appear on their own "Owner funding" section and Excel sheet.
  Record the bills that money paid for as normal expenses. Co-owners' income and expenses are still split by
  ownership share, whoever funded them.

This app organises your records; it isn't tax advice. Your accountant decides how items are treated
(e.g. repairs vs capital improvements, depreciation).

## Development

```bash
# API (http://localhost:8000, docs at /api/docs)
cd backend
pip install -r requirements-dev.txt
RM_DATA_DIR=./data uvicorn app.main:app --reload
pytest

# Web UI (http://localhost:5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Schema changes: edit `backend/app/models.py`, then
`cd backend && RM_DATA_DIR=./data alembic revision --autogenerate -m "describe change"`.

Architecture notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
