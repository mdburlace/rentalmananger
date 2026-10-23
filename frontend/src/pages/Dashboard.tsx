import { Link } from "react-router-dom";
import { api, currentFy, Dashboard, fmtDate, money, moneyShort, qs } from "../api";
import { ErrorBox, FySelect, KindBadge, PropertySelect, useLoad, useLocalState, useSession } from "../components";

function MonthlyChart({ data }: { data: Dashboard["monthly"] }) {
  const max = Math.max(1, ...data.flatMap((m) => [m.income, m.expenses]));
  return (
    <div>
      <div className="bars" role="img" aria-label="Monthly income and expenses">
        {data.map((m) => (
          <div className="col" key={m.month} title={`${m.label}: income ${money(m.income)}, expenses ${money(m.expenses)}`}>
            <div className="pair">
              <div className="bar in" style={{ height: `${(m.income / max) * 100}%` }} />
              <div className="bar out" style={{ height: `${(m.expenses / max) * 100}%` }} />
            </div>
            <span className="lbl">{m.label}</span>
          </div>
        ))}
      </div>
      <div className="legend" style={{ marginTop: 10 }}>
        <span><i style={{ background: "var(--income)" }} />Income</span>
        <span><i style={{ background: "var(--expense)" }} />Expenses</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { properties, canEdit } = useSession();
  const [fy, setFy] = useLocalState("rm.fy", currentFy());
  const [prop, setProp] = useLocalState<number | "">("rm.dashProp", "");
  const { data, error } = useLoad(() => api<Dashboard>(`/api/dashboard${qs({ fy, property_id: prop })}`), [fy, prop]);

  if (!properties.length) {
    return (
      <div className="card card-pad stack" style={{ maxWidth: 640 }}>
        <h1>Welcome 👋</h1>
        <p>Start by adding your rental property (and who owns it), then import your existing spreadsheets or add transactions as they happen.</p>
        <div className="toolbar">
          <Link className="btn primary" to="/properties">Add a property</Link>
          {canEdit && <Link className="btn" to="/import">Import a spreadsheet</Link>}
        </div>
      </div>
    );
  }
  const maxLabel = Math.max(1, ...(data?.expenses_by_label.map((e) => e.amount) ?? [1]));
  return (
    <>
      <div className="page-head">
        <div><h1>Dashboard</h1><p>FY {data?.fy_label ?? ""} · 1 July – 30 June</p></div>
        <div className="toolbar">
          {properties.length > 1 && <PropertySelect value={prop} onChange={setProp} />}
          <FySelect value={fy} onChange={setFy} years={data?.years.map((y) => y.fy)} />
          {canEdit && <Link className="btn primary" to="/transactions?new=1">+ Add transaction</Link>}
        </div>
      </div>
      <ErrorBox error={error} />
      {data && (
        <div className="stack">
          <div className="grid grid-3">
            <div className="card kpi"><div className="label">Income</div><div className="value pos">{money(data.totals.income)}</div><div className="sub">Rent & other rental income</div></div>
            <div className="card kpi"><div className="label">Deductible expenses</div><div className="value neg">{money(data.totals.expenses)}</div><div className="sub">Claimable share</div></div>
            <div className="card kpi"><div className="label">Net rent</div><div className={`value ${data.totals.net >= 0 ? "pos" : "neg"}`}>{money(data.totals.net)}</div><div className="sub">{data.totals.net < 0 ? "Negatively geared" : "Positively geared"}</div></div>
          </div>

          {(data.checks.length > 0 || data.needs_review > 0) && (
            <div className="card">
              <div className="card-head"><h2>Before tax time</h2><Link to="/reports">Open report →</Link></div>
              <div className="card-pad checks">
                {data.checks.filter((c) => c.level !== "info").slice(0, 6).map((c, i) => (
                  <div key={i} className={`alert ${c.level}`}>{properties.length > 1 && <b>{c.property}:</b>} {c.message}</div>
                ))}
                {data.needs_review > 0 && <Link to="/transactions?review=1">Review {data.needs_review} flagged transaction(s) →</Link>}
              </div>
            </div>
          )}

          <div className="grid grid-main">
            <div className="card"><div className="card-head"><h2>Month by month</h2></div><div className="card-pad"><MonthlyChart data={data.monthly} /></div></div>
            <div className="card">
              <div className="card-head"><h2>Where the money went</h2></div>
              <div className="card-pad">
                {data.expenses_by_label.length === 0 && <p className="muted">No expenses this year yet.</p>}
                {data.expenses_by_label.map((e) => (
                  <div className="hbar" key={e.key}>
                    <span>{e.label}</span><span className="num">{money(e.amount)}</span>
                    <div className="track"><div className="fill" style={{ width: `${(e.amount / maxLabel) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-2">
            <div className="card">
              <div className="card-head"><h2>Year on year</h2></div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>FY</th><th className="num">Income</th><th className="num">Expenses</th><th className="num">Net</th></tr></thead>
                  <tbody>
                    {[...data.years].reverse().map((y) => (
                      <tr key={y.fy} className="clickable" onClick={() => setFy(y.fy)} style={y.fy === fy ? { fontWeight: 700 } : undefined}>
                        <td>{y.fy_label}</td><td className="num">{moneyShort(y.income)}</td><td className="num">{moneyShort(y.expenses)}</td>
                        <td className={`num ${y.net >= 0 ? "pos" : "neg"}`}>{moneyShort(y.net)}</td>
                      </tr>
                    ))}
                    {data.years.length === 0 && <tr><td colSpan={4} className="empty">No transactions yet</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="card">
              <div className="card-head"><h2>Recently added</h2><Link to="/transactions">All transactions →</Link></div>
              <div className="table-wrap">
                <table>
                  <tbody>
                    {data.recent.map((t) => (
                      <tr key={t.id}>
                        <td>{fmtDate(t.date)}<div className="sub">{t.category_name}</div></td>
                        <td className="hide-sm"><KindBadge kind={t.kind} /></td>
                        <td className="num">{money(t.amount)}</td>
                      </tr>
                    ))}
                    {data.recent.length === 0 && <tr><td className="empty">Nothing yet</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
