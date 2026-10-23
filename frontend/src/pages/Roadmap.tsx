const PHASES: { name: string; status: "done" | "next" | "planned" | "exploring"; area: string; items: string[] }[] = [
  { name: "Income, expenses & accountant reporting", status: "done", area: "v0.2 – you are here", items: [
    "Properties, ownership splits and per-year rental schedule facts",
    "Income & expenses with receipts, private-use apportionment",
    "Categories mapped to ATO rental schedule labels",
    "Loans with 30 June balances",
    "Owner contributions & drawings, reported separately from tax figures",
    "Spreadsheet / bank CSV import with duplicate checks and undo",
    "FY report, owner shares, pre-tax checks, accountant pack (Excel + CSV + receipts)",
    "Read-only accountant login",
  ] },
  { name: "Bill tracking & financial reporting", status: "next", area: "Financial & rent management", items: [
    "Recurring items and expected-bill reminders (rates, water, insurance, interest)",
    "Bill inbox: email or photo → AI-extracted draft transaction",
    "Bank import rules, later open-banking feeds",
    "Agent statement import",
    "Depreciation schedule and borrowing-cost amortisation",
    "Cash flow, P&L, budget vs actual, Xero/MYOB export, CGT cost base",
    "Water usage recovery from tenants",
  ] },
  { name: "Tenancies, rent & communication", status: "planned", area: "Financial · Tenant & communication portals", items: [
    "Leases, bond, rent ledger and arrears",
    "Rent collection: direct debit / PayTo, card, BPAY",
    "Tenant and owner portals",
    "Single message timeline (email, SMS, in-app)",
    "Automated reminders: late rent, inspections, lease expiry",
  ] },
  { name: "Maintenance & work orders", status: "planned", area: "Maintenance", items: [
    "Tenant requests with photos", "Contractor quotes, dispatch and job tracking",
    "Contractor invoices flow straight into expenses", "Lifelong maintenance history per property",
  ] },
  { name: "Inspections & compliance", status: "planned", area: "Inspections", items: [
    "Entry / routine / exit templates, room by room", "Photos and 360° panoramas per item",
    "Compliance calendar: smoke alarms, pool, insurance, lease dates",
  ] },
  { name: "Leasing & onboarding", status: "planned", area: "Leasing", items: [
    "Listings and portal syndication", "Applications and tenant screening", "Lease generation and e-signature",
  ] },
  { name: "Agency mode & trust accounting", status: "exploring", area: "Only if managing others' properties", items: [
    "Client portfolios, trust ledger, reconciliations and audit reports (QLD AFA Act)",
  ] },
  { name: "AI add-ons", status: "exploring", area: "Modern add-ons", items: [
    "Bill scanning and splitting", "Drafted tenant replies", "Lease abstracting", "Ask questions of your records",
  ] },
];

const badge = { done: ["Shipped", "b-income"], next: ["Next", "b-warn"], planned: ["Planned", "b-info"], exploring: ["Exploring", "b-excluded"] } as const;

export default function RoadmapPage() {
  return (
    <>
      <div className="page-head"><div><h1>Roadmap</h1><p>Where Rental Manager is heading. Full detail is in docs/ROADMAP.md in the repository.</p></div></div>
      <div className="grid grid-2">
        {PHASES.map((p, i) => (
          <div className="card" key={p.name}>
            <div className="card-head">
              <div><div className="sub muted">Phase {i} · {p.area}</div><h2>{p.name}</h2></div>
              <span className={`badge ${badge[p.status][1]}`}>{badge[p.status][0]}</span>
            </div>
            <ul style={{ margin: 0, padding: "14px 20px 16px 38px" }}>{p.items.map((it) => <li key={it} style={{ marginBottom: 4 }}>{it}</li>)}</ul>
          </div>
        ))}
      </div>
    </>
  );
}
