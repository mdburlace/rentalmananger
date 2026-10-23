# Roadmap

Rental Manager starts where the spreadsheets left off – capturing income and
expenses and handing the accountant clean, schedule-ready numbers – and grows
into a full property management platform in phases. Each phase is usable on
its own, and the data model was set up in v0.1 so later phases don't need a
rewrite (every record belongs to a *portfolio*, users have roles, money is
stored as integer cents, every category maps to an ATO schedule label).

Status key: ✅ shipped · 🔜 next · 🗓 planned · 💭 exploring

---

## Phase 0 — Income, expenses & accountant reporting ✅ (v0.1)

- ✅ Properties with ownership splits (e.g. 50/50) and per-year facts the rental schedule asks for (weeks rented / available, loan refinanced, notes)
- ✅ Income & expense capture with receipts/invoices attached (photos, PDFs)
- ✅ Categories you name yourself, each mapped to an **ATO rental property schedule** label
- ✅ Private-use apportionment per transaction (claimable %) and per loan
- ✅ Loans with 30 June balances and interest rates
- ✅ Owner contributions and drawings (v0.2) – who funded shortfalls, kept separate from the tax figures
- ✅ Spreadsheet & bank CSV import with preview, duplicate detection, "this bill appears in two years" warnings, learned category mappings and one-click undo
- ✅ Financial-year report: totals by schedule label, owner shares, loan balances and a "check before sending" list (missing rent, missing interest months, unreviewed items, missing receipts)
- ✅ Accountant pack: Excel report + CSV + every receipt in one ZIP; printable report
- ✅ Read-only login for your accountant; admin / editor / read-only roles
- ✅ Self-hosted Docker image for Portainer; SQLite by default, Postgres-ready

## Phase 1 — Expense & bill tracking, tax & financial reporting 🔜

*Roadmap area 1: "Expense & Bill Tracking" and "Tax & Financial Reporting".*

- 🔜 **Recurring items & expected bills** – rates (half-yearly), water (quarterly), insurance (annual), loan interest (monthly). Dashboard shows what's due and what's missing *before* tax time.
- 🔜 **Bill inbox** – forward bills/receipts to an email address or upload a photo; extract supplier, amount, bill period and due date (OCR + AI), create a draft transaction for one-tap approval.
- 🔜 **Bank import rules** – saved rules for bank CSV/OFX ("URBAN UTILITIES" → Water, Conochie). Later: Consumer Data Right (open banking) feeds via an accredited aggregator such as Basiq.
- 🗓 **Agent statement import** – monthly / EOFY owner statements from the property manager (PDF/CSV) split into rent, fees and paid bills.
- 🗓 **Depreciation & borrowing costs** – enter the quantity surveyor's schedule (Div 40 plant, Div 43 capital works) and amortise borrowing expenses over 5 years automatically.
- 🗓 **More reports** – monthly cash flow, profit & loss, budget vs actual, yield/return on purchase price, ledger export for Xero/MYOB, CGT cost-base register (capital improvements, purchase and sale costs).
- 🗓 **Water usage recovery** – where the property is individually metered and water-efficient, Queensland tenants can be charged for water consumption; split each water bill into usage (recoverable) and fixed charges and track what's been on-charged.

## Phase 2 — Tenancies, rent & communication 🗓

*Roadmap areas 1 & 2: "Automated Rent Collection", "Dedicated Portals", "In-App Messaging & SMS Alerts", "Automated Notifications".*

- Tenancies: lease dates, rent amount and frequency, bond (RTA lodgement number), rent ledger with paid-to date and arrears
- **Rent collection**: direct debit / PayTo (e.g. Stripe BECS, Zepto, GoCardless), cards, BPAY via a biller provider; automatic reconciliation into income
- **Tenant portal**: balance, receipts, lease documents, maintenance requests
- **Owner portal**: real-time portfolio dashboard and statements for co-owners or investors
- **Communication timeline** per tenancy – email, SMS and in-app messages in one place for a clear paper trail
- **Notifications** (email, SMS via e.g. Twilio/MessageMedia, PWA push): rent due/late reminders aligned to RTA breach timeframes, inspection notices, lease expiry, insurance renewal

## Phase 3 — Maintenance & work orders 🗓

*Roadmap area 3.*

- Tenants log issues with photos from their phone
- Contractor directory (licences, insurance expiry), quote requests, work orders, live job status
- Contractor invoice → expense transaction with the invoice attached, categorised as repairs vs capital improvement
- Lifelong maintenance history per property and asset (hot water system, smoke alarms, roof) for compliance and asset evaluation

## Phase 4 — Inspections & compliance 🗓

*Roadmap area 5.*

- Entry, routine and exit inspection templates (room-by-room condition, QLD entry condition report format)
- Photos and 360° panoramas linked to each room/item to evidence wear and tear; PDF report for tenant signature
- Compliance calendar: smoke alarm servicing (QLD interconnected alarm rules), pool safety certificate, gas/electrical checks, insurance renewal, lease and bond deadlines

## Phase 5 — Leasing & tenant onboarding 🗓

*Roadmap area 4.*

- Vacancy listings with photos; syndication to realestate.com.au / Domain (both require an agency or approved-partner account – may start as "export listing" instead)
- Digital applications, reference checks and tenancy database checks through a screening provider
- Lease generation (QLD Form 18a general tenancy agreement) and e-signature (e.g. DocuSign or Dropbox Sign)

## Phase 6 — Agency mode & trust accounting 💭

*Roadmap area 1: "Trust Accounting & Compliance".*

Only needed if the app is used to manage **other people's** properties for a fee. A licensed agent in Queensland must keep client money in a trust account under the *Agents Financial Administration Act 2014* (receipting, monthly reconciliations, annual audit). Self-managing owners don't need this. If pursued:

- Multiple client portfolios per agency (the data model already scopes records by portfolio)
- Separate trust ledger, receipts, disbursements, owner payouts and fees
- Three-way bank reconciliation and auditor reports
- Full audit log and immutable ledger entries

## Phase 7 — AI add-ons 💭

*Roadmap area 6.*

- Scan and split bills automatically (water: usage vs fixed; shared bills across properties)
- Draft context-aware replies to tenant messages from the tenancy timeline
- Lease abstracting – pull key dates, rent reviews and special terms from a signed lease
- Ask questions of your records ("what did we spend on repairs at Conochie over 3 years?")
- Anomaly checks before EOFY (unusual amounts, missing months, likely capital items coded as repairs)

## Platform work (runs alongside)

- Automatic database + receipts backups (e.g. to S3/Backblaze) and restore
- Postgres deployment option in the compose file
- Sign-in hardening: MFA, Google/Apple sign-in, OIDC for SSO
- Installable PWA with offline capture (snap a receipt with no signal, sync later); native apps later if needed
- Audit log of every change; API tokens for integrations
- Multi-tenant hosting if the app is ever offered to other landlords
