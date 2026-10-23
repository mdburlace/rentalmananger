import { FormEvent, Fragment, useEffect, useState } from "react";
import { api, currentFy, fmtDate, FyReport, money, PropertyReport, qs, ReportLine } from "../api";
import { ErrorBox, FySelect, PropertySelect, useLoad, useLocalState, useSession } from "../components";

function YearFacts({ r, fy, onSaved }: { r: PropertyReport; fy: number; onSaved: () => void }) {
  const { canEdit, toast } = useSession();
  const [f, setF] = useState({ weeks_rented: "", weeks_available: "", loan_refinanced: false, notes: "" });
  useEffect(() => setF({
    weeks_rented: r.year.weeks_rented?.toString() ?? "", weeks_available: r.year.weeks_available?.toString() ?? "",
    loan_refinanced: r.year.loan_refinanced, notes: r.year.notes ?? "",
  }), [r]);
  const save = async (e: FormEvent) => {
    e.preventDefault();
    await api(`/api/properties/${r.property.id}/years/${fy}`, { method: "PUT", body: {
      weeks_rented: f.weeks_rented === "" ? null : Number(f.weeks_rented), weeks_available: f.weeks_available === "" ? null : Number(f.weeks_available),
      loan_refinanced: f.loan_refinanced, notes: f.notes || null,
    } });
    toast("Saved"); onSaved();
  };
  return (
    <form className="form-grid" onSubmit={save}>
      <label className="field">Weeks rented<input type="number" min={0} max={53} disabled={!canEdit} value={f.weeks_rented} onChange={(e) => setF({ ...f, weeks_rented: e.target.value })} /></label>
      <label className="field">Weeks available for rent<input type="number" min={0} max={53} disabled={!canEdit} value={f.weeks_available} onChange={(e) => setF({ ...f, weeks_available: e.target.value })} /></label>
      <label className="check full"><input type="checkbox" disabled={!canEdit} checked={f.loan_refinanced} onChange={(e) => setF({ ...f, loan_refinanced: e.target.checked })} />Loan was refinanced or renegotiated this year</label>
      <label className="field full">Notes for the accountant<small>Anything unusual – vacancy, major repairs, private use, sale plans</small><textarea disabled={!canEdit} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></label>
      {canEdit && <div className="full no-print"><button>Save year details</button></div>}
    </form>
  );
}

function Lines({ title, lines, total, showZero }: { title: string; lines: ReportLine[]; total?: number; showZero: boolean }) {
  const [open, setOpen] = useState<string | null>(null);
  const visible = lines.filter((l) => showZero || l.amount);
  return (
    <>
      <tr className="section"><td colSpan={2}>{title}</td></tr>
      {visible.map((l) => (
        <Fragment key={l.key}>
          <tr className={l.amount ? "clickable" : "muted"} onClick={() => l.categories.length && setOpen(open === l.key ? null : l.key)}>
            <td>{l.label}{l.gross_amount !== l.amount && <span className="sub"> (of {money(l.gross_amount)} paid)</span>}</td>
            <td className="num">{money(l.amount)}</td>
          </tr>
          {open === l.key && l.categories.map((c) => (
            <tr key={l.key + c.name} className="muted"><td style={{ paddingLeft: 28 }}>{c.name}</td><td className="num">{money(c.amount)}</td></tr>
          ))}
        </Fragment>
      ))}
      {visible.length === 0 && <tr className="muted"><td colSpan={2}>Nothing recorded</td></tr>}
      {total !== undefined && <tr className="total"><td>Total {title.toLowerCase()}</td><td className="num">{money(total)}</td></tr>}
    </>
  );
}

export default function ReportsPage() {
  const { properties } = useSession();
  const [fy, setFy] = useLocalState("rm.reportFy", currentFy() - 1);
  const [prop, setProp] = useState<number | "">("");
  const [showZero, setShowZero] = useState(false);
  const { data, error, reload } = useLoad(() => api<FyReport>(`/api/reports/fy${qs({ fy, property_id: prop })}`), [fy, prop]);
  const dl = (kind: string) => `/api/reports/fy/${kind}${qs({ fy, property_id: prop })}`;

  return (
    <>
      <div className="page-head">
        <div><h1>Tax reports</h1><p>Everything your accountant needs for the rental schedule, FY {data?.fy_label} (1 Jul {data?.start.slice(0, 4)} – 30 Jun {data?.end.slice(0, 4)}).</p></div>
        <div className="toolbar">
          {properties.length > 1 && <PropertySelect value={prop} onChange={setProp} />}
          <FySelect value={fy} onChange={setFy} />
        </div>
      </div>
      <ErrorBox error={error} />
      <div className="card card-pad no-print" style={{ marginBottom: 16, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div><b>Send to your accountant</b><div className="sub muted">The pack has the Excel report, a CSV of every transaction and all receipts, organised by property.</div></div>
        <div className="toolbar">
          <a className="btn gold" href={dl("pack.zip")}>⬇ Accountant pack (.zip)</a>
          <a className="btn" href={dl("export.xlsx")}>Excel report</a>
          <a className="btn" href={dl("export.csv")}>CSV</a>
          <button onClick={() => window.print()}>Print / PDF</button>
        </div>
      </div>
      {data && data.properties.length > 1 && (
        <div className="grid grid-3" style={{ marginBottom: 16 }}>
          <div className="card kpi"><div className="label">Total income</div><div className="value pos">{money(data.totals.income)}</div></div>
          <div className="card kpi"><div className="label">Total expenses</div><div className="value neg">{money(data.totals.expenses)}</div></div>
          <div className="card kpi"><div className="label">Net rent</div><div className={`value ${data.totals.net >= 0 ? "pos" : "neg"}`}>{money(data.totals.net)}</div></div>
        </div>
      )}
      <div className="stack">
        {data?.properties.map((r) => (
          <div className="card" key={r.property.id}>
            <div className="card-head">
              <div><h2>{r.property.name}</h2><div className="muted">{r.property.address}</div></div>
              <label className="check no-print"><input type="checkbox" checked={showZero} onChange={(e) => setShowZero(e.target.checked)} />Show all schedule labels</label>
            </div>
            <div className="grid grid-main" style={{ gap: 0 }}>
              <div style={{ borderRight: "1px solid var(--line)" }}>
                <table>
                  <tbody>
                    <Lines title="Income" lines={r.income} total={r.totals.income} showZero={showZero} />
                    <Lines title="Expenses" lines={r.expenses} total={r.totals.expenses} showZero={showZero} />
                    <tr className="total" style={{ fontSize: "1.05rem" }}><td>Net rent</td><td className={`num ${r.totals.net >= 0 ? "pos" : "neg"}`}>{money(r.totals.net)}</td></tr>
                    {(r.totals.excluded > 0 || showZero) && <Lines title="Not claimed (capital / private)" lines={r.excluded} showZero={showZero} />}
                  </tbody>
                </table>
              </div>
              <div className="card-pad stack">
                {r.checks.length > 0 && (
                  <div>
                    <h3 style={{ marginBottom: 8 }}>Check before sending</h3>
                    <div className="checks">{r.checks.map((c, i) => <div key={i} className={`alert ${c.level}`}>{c.message}</div>)}</div>
                  </div>
                )}
                <div>
                  <h3 style={{ marginBottom: 8 }}>Owner shares</h3>
                  <table>
                    <thead><tr><th>Owner</th><th className="num">Share</th><th className="num">Net</th></tr></thead>
                    <tbody>{r.owners.map((o) => (
                      <tr key={o.owner_name}><td>{o.owner_name}<div className="sub">Inc {money(o.income)} · Exp {money(o.expenses)}</div></td><td className="num">{o.share_percent}%</td><td className="num">{money(o.net)}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
                <div>
                  <h3 style={{ marginBottom: 8 }}>Property & year details</h3>
                  <div className="sub muted" style={{ marginBottom: 10 }}>Purchased {fmtDate(r.property.purchase_date)}{r.property.purchase_price ? ` for ${money(r.property.purchase_price)}` : ""} · first rented {fmtDate(r.property.first_rented_date)}</div>
                  <YearFacts r={r} fy={fy} onSaved={reload} />
                </div>
                {r.loans.length > 0 && (
                  <div>
                    <h3 style={{ marginBottom: 8 }}>Loans at 30 June</h3>
                    {r.loans.map((l) => <div key={l.id} className="sub">{l.name}{l.lender ? ` (${l.lender})` : ""}: {l.balance !== null ? `${money(l.balance)} at ${fmtDate(l.balance_date)}${l.interest_rate ? `, ${l.interest_rate}%` : ""}` : <span className="badge b-warn">no balance for this FY</span>}</div>)}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {data?.properties.length === 0 && <div className="card empty">No properties yet.</div>}
      </div>
    </>
  );
}
