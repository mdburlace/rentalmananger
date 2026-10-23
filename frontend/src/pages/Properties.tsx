import { FormEvent, useState } from "react";
import { api, fmtDate, Loan, money, Owner, Property } from "../api";
import { Drawer, ErrorBox, useLoad, useSession } from "../components";

const STATES = ["QLD", "NSW", "VIC", "ACT", "SA", "WA", "TAS", "NT"];

function PropertyEditor({ prop, owners, onClose, onSaved }: { prop: Property | null; owners: Owner[]; onClose: () => void; onSaved: () => void }) {
  const { toast } = useSession();
  const [f, setF] = useState({
    name: prop?.name ?? "", address_line: prop?.address_line ?? "", suburb: prop?.suburb ?? "", state: prop?.state ?? "QLD",
    postcode: prop?.postcode ?? "", property_type: prop?.property_type ?? "House", purchase_date: prop?.purchase_date ?? "",
    purchase_price: prop?.purchase_price?.toString() ?? "", first_rented_date: prop?.first_rented_date ?? "", notes: prop?.notes ?? "",
    archived: prop?.archived ?? false,
  });
  const [shares, setShares] = useState<{ owner_id: number | ""; share_percent: string }[]>(
    prop?.ownerships.length ? prop.ownerships.map((o) => ({ owner_id: o.owner_id, share_percent: String(o.share_percent) })) : [],
  );
  const [err, setErr] = useState<string | null>(null);
  const total = shares.reduce((s, x) => s + (Number(x.share_percent) || 0), 0);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  const save = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    const body = {
      ...f, purchase_date: f.purchase_date || null, first_rented_date: f.first_rented_date || null,
      purchase_price: f.purchase_price ? f.purchase_price.replace(/[$,]/g, "") : null,
      ownerships: shares.filter((s) => s.owner_id).map((s) => ({ owner_id: s.owner_id, share_percent: s.share_percent })),
    };
    try {
      if (prop) await api(`/api/properties/${prop.id}`, { method: "PUT", body });
      else await api("/api/properties", { body });
      toast("Property saved"); onSaved(); onClose();
    } catch (ex) { setErr((ex as Error).message); }
  };
  return (
    <Drawer title={prop ? `Edit ${prop.name}` : "Add property"} onClose={onClose}
      footer={<><span /><button className="primary" form="prop-form">Save</button></>}>
      <form id="prop-form" className="form-grid" onSubmit={save}>
        <div className="full"><ErrorBox error={err} /></div>
        <label className="field full">Short name<small>What you call it, e.g. "Conochie"</small><input required value={f.name} onChange={set("name")} /></label>
        <label className="field full">Street address<input value={f.address_line} onChange={set("address_line")} /></label>
        <label className="field">Suburb<input value={f.suburb} onChange={set("suburb")} /></label>
        <div className="form-grid" style={{ gap: 10 }}>
          <label className="field">State<select value={f.state} onChange={set("state")}>{STATES.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label className="field">Postcode<input inputMode="numeric" value={f.postcode} onChange={set("postcode")} /></label>
        </div>
        <label className="field">Type<select value={f.property_type} onChange={set("property_type")}>{["House", "Unit", "Townhouse", "Duplex", "Land", "Commercial", "Other"].map((s) => <option key={s}>{s}</option>)}</select></label>
        <label className="field">Date purchased<input type="date" value={f.purchase_date} onChange={set("purchase_date")} /></label>
        <label className="field">Purchase price<input inputMode="decimal" value={f.purchase_price} onChange={set("purchase_price")} /></label>
        <label className="field">First earned rent<small>Asked on the rental schedule</small><input type="date" value={f.first_rented_date} onChange={set("first_rented_date")} /></label>
        <div className="field full">
          Ownership <small>Income and expenses are split between owners by these shares in the accountant report.</small>
          {shares.map((s, i) => (
            <div key={i} className="toolbar" style={{ flexWrap: "nowrap" }}>
              <select value={s.owner_id} onChange={(e) => setShares(shares.map((x, j) => j === i ? { ...x, owner_id: e.target.value ? Number(e.target.value) : "" } : x))}>
                <option value="">Choose owner…</option>
                {owners.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
              <input style={{ width: 90 }} type="number" min={0.01} max={100} step="0.01" value={s.share_percent} onChange={(e) => setShares(shares.map((x, j) => j === i ? { ...x, share_percent: e.target.value } : x))} aria-label="Share percent" />
              <span>%</span>
              <button type="button" className="ghost small" onClick={() => setShares(shares.filter((_, j) => j !== i))} aria-label="Remove owner">✕</button>
            </div>
          ))}
          <div className="toolbar">
            <button type="button" className="small" disabled={!owners.length} onClick={() => setShares([...shares, { owner_id: "", share_percent: shares.length ? String(Math.max(0, 100 - total)) : "100" }])}>+ Add owner</button>
            {shares.length > 0 && <span className={Math.abs(total - 100) > 0.01 ? "neg" : "muted"}>Total {total}%</span>}
            {!owners.length && <small className="muted">Add owners in the Owners section first.</small>}
          </div>
        </div>
        <label className="field full">Notes<textarea value={f.notes} onChange={set("notes")} /></label>
        {prop && <label className="check full"><input type="checkbox" checked={f.archived} onChange={(e) => setF({ ...f, archived: e.target.checked })} />Archived (sold / no longer rented)</label>}
      </form>
    </Drawer>
  );
}

function LoansCard({ prop }: { prop: Property }) {
  const { canEdit, toast } = useSession();
  const { data: loans, reload } = useLoad(() => api<Loan[]>(`/api/loans?property_id=${prop.id}`), [prop.id]);
  const [edit, setEdit] = useState<Loan | null | undefined>(undefined);
  const [bal, setBal] = useState<{ loan: Loan; as_of: string; balance: string; interest_rate: string } | null>(null);
  const [f, setF] = useState({ name: "", lender: "", account_hint: "", rental_use_percent: "100", notes: "" });
  const [err, setErr] = useState<string | null>(null);
  const open = (l: Loan | null) => { setErr(null); setF({ name: l?.name ?? "Investment loan", lender: l?.lender ?? "", account_hint: l?.account_hint ?? "", rental_use_percent: String(l?.rental_use_percent ?? 100), notes: l?.notes ?? "" }); setEdit(l); };
  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const body = { ...f, property_id: prop.id };
      if (edit) await api(`/api/loans/${edit.id}`, { method: "PUT", body }); else await api("/api/loans", { body });
      setEdit(undefined); reload(); toast("Loan saved");
    } catch (ex) { setErr((ex as Error).message); }
  };
  const saveBal = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api(`/api/loans/${bal!.loan.id}/balances`, { body: { as_of: bal!.as_of, balance: bal!.balance.replace(/[$,]/g, ""), interest_rate: bal!.interest_rate || null } });
      setBal(null); reload(); toast("Balance saved");
    } catch (ex) { setErr((ex as Error).message); }
  };
  return (
    <div style={{ borderTop: "1px solid var(--line)" }}>
      <div className="card-head" style={{ borderBottom: "none", paddingBottom: 4 }}>
        <h3>Loans</h3>{canEdit && <button className="small" onClick={() => open(null)}>+ Loan</button>}
      </div>
      <div style={{ padding: "0 20px 14px" }}>
        {loans?.length === 0 && <p className="muted" style={{ margin: 0 }}>No loans recorded. Add one to track the 30 June balance your accountant asks for.</p>}
        {loans?.map((l) => {
          const last = l.balances[l.balances.length - 1];
          return (
            <div key={l.id} style={{ padding: "8px 0", display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <div>
                <b>{l.name}</b> <span className="muted">{[l.lender, l.account_hint].filter(Boolean).join(" · ")}</span>
                {l.rental_use_percent < 100 && <span className="badge b-info" style={{ marginLeft: 6 }}>{l.rental_use_percent}% rental use</span>}
                <div className="sub muted">{last ? `${money(last.balance)} at ${fmtDate(last.as_of)}${last.interest_rate ? ` · ${last.interest_rate}%` : ""}` : "No balances yet"}</div>
              </div>
              {canEdit && <div className="toolbar">
                <button className="small" onClick={() => { setErr(null); setBal({ loan: l, as_of: `${new Date().getMonth() >= 6 ? new Date().getFullYear() : new Date().getFullYear() - 1}-06-30`, balance: "", interest_rate: last?.interest_rate?.toString() ?? "" }); }}>+ Balance</button>
                <button className="small ghost" onClick={() => open(l)}>Edit</button>
              </div>}
            </div>
          );
        })}
      </div>
      {edit !== undefined && (
        <Drawer title={edit ? "Edit loan" : "Add loan"} onClose={() => setEdit(undefined)}
          footer={<>{edit ? <button className="danger" onClick={async () => { if (confirm("Delete loan and its balances?")) { await api(`/api/loans/${edit.id}`, { method: "DELETE" }); setEdit(undefined); reload(); } }}>Delete</button> : <span />}<button className="primary" form="loan-form">Save</button></>}>
          <form id="loan-form" className="form-grid" onSubmit={save}>
            <div className="full"><ErrorBox error={err} /></div>
            <label className="field full">Name<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
            <label className="field">Lender<input value={f.lender} onChange={(e) => setF({ ...f, lender: e.target.value })} /></label>
            <label className="field">Account label<small>e.g. "ends 4417" – never the full number</small><input maxLength={40} value={f.account_hint} onChange={(e) => setF({ ...f, account_hint: e.target.value })} /></label>
            <label className="field">Rental use %<small>If part of the loan was for private use</small><input type="number" min={0} max={100} value={f.rental_use_percent} onChange={(e) => setF({ ...f, rental_use_percent: e.target.value })} /></label>
            <label className="field full">Notes<textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></label>
            {edit && edit.balances.length > 0 && (
              <div className="full">
                <h3 style={{ marginBottom: 6 }}>Balance history</h3>
                <table><tbody>{edit.balances.map((b) => (
                  <tr key={b.id}><td>{fmtDate(b.as_of)}</td><td className="num">{money(b.balance)}</td><td className="num">{b.interest_rate ? `${b.interest_rate}%` : ""}</td>
                    <td><button type="button" className="ghost small" onClick={async () => { await api(`/api/loans/${edit.id}/balances/${b.id}`, { method: "DELETE" }); reload(); setEdit(undefined); }}>✕</button></td></tr>
                ))}</tbody></table>
              </div>
            )}
          </form>
        </Drawer>
      )}
      {bal && (
        <Drawer title={`Balance – ${bal.loan.name}`} onClose={() => setBal(null)} footer={<><span /><button className="primary" form="bal-form">Save</button></>}>
          <form id="bal-form" className="form-grid" onSubmit={saveBal}>
            <div className="full"><ErrorBox error={err} /></div>
            <label className="field">As at<input type="date" required value={bal.as_of} onChange={(e) => setBal({ ...bal, as_of: e.target.value })} /></label>
            <label className="field">Balance<input inputMode="decimal" required value={bal.balance} onChange={(e) => setBal({ ...bal, balance: e.target.value })} /></label>
            <label className="field">Interest rate %<input inputMode="decimal" value={bal.interest_rate} onChange={(e) => setBal({ ...bal, interest_rate: e.target.value })} /></label>
          </form>
        </Drawer>
      )}
    </div>
  );
}

function OwnersCard({ owners, reload }: { owners: Owner[]; reload: () => void }) {
  const { canEdit, toast } = useSession();
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const add = async (e: FormEvent) => {
    e.preventDefault();
    try { await api("/api/owners", { body: { name } }); setName(""); reload(); toast("Owner added"); } catch (ex) { setErr((ex as Error).message); }
  };
  const rename = async (o: Owner) => {
    const n = prompt("Owner name", o.name);
    if (n && n !== o.name) { await api(`/api/owners/${o.id}`, { method: "PUT", body: { ...o, name: n } }); reload(); }
  };
  const remove = async (o: Owner) => {
    if (!confirm(`Remove ${o.name}?`)) return;
    try { await api(`/api/owners/${o.id}`, { method: "DELETE" }); reload(); } catch (ex) { setErr((ex as Error).message); }
  };
  return (
    <div className="card">
      <div className="card-head"><h2>Owners</h2></div>
      <div className="card-pad stack" style={{ gap: 10 }}>
        <p className="muted" style={{ margin: 0 }}>The people (or entities) on the title. Each property's income and expenses are split between its owners for their own tax returns.</p>
        <ErrorBox error={err} />
        {owners.map((o) => (
          <div key={o.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{o.name}</span>
            {canEdit && <span><button className="ghost small" onClick={() => rename(o)}>Rename</button><button className="ghost small danger" onClick={() => remove(o)}>Remove</button></span>}
          </div>
        ))}
        {canEdit && <form className="toolbar" onSubmit={add} style={{ flexWrap: "nowrap" }}><input placeholder="Owner name" required value={name} onChange={(e) => setName(e.target.value)} /><button>Add</button></form>}
      </div>
    </div>
  );
}

export default function PropertiesPage() {
  const { canEdit, reload: reloadSession } = useSession();
  const { data: props, reload } = useLoad(() => api<Property[]>("/api/properties?include_archived=true"), []);
  const { data: owners, reload: reloadOwners } = useLoad(() => api<Owner[]>("/api/owners"), []);
  const [edit, setEdit] = useState<Property | null | undefined>(undefined);
  const refresh = () => { reload(); reloadSession(); };
  return (
    <>
      <div className="page-head">
        <div><h1>Properties</h1><p>Details, ownership and loans used on the rental schedule.</p></div>
        {canEdit && <button className="primary" onClick={() => setEdit(null)}>+ Add property</button>}
      </div>
      <div className="grid grid-main" style={{ alignItems: "start" }}>
        <div className="stack">
          {props?.length === 0 && <div className="card empty">No properties yet. Add your first one to start recording income and expenses.</div>}
          {props?.map((p) => (
            <div className="card" key={p.id} style={p.archived ? { opacity: 0.65 } : undefined}>
              <div className="card-head">
                <div><h2>{p.name} {p.archived && <span className="badge b-excluded">Archived</span>}</h2><div className="muted">{p.full_address}</div></div>
                {canEdit && <button className="small" onClick={() => setEdit(p)}>Edit</button>}
              </div>
              <div className="card-pad" style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
                <div><div className="muted sub">Purchased</div>{fmtDate(p.purchase_date)}{p.purchase_price ? ` · ${money(p.purchase_price)}` : ""}</div>
                <div><div className="muted sub">First rented</div>{fmtDate(p.first_rented_date)}</div>
                <div><div className="muted sub">Ownership</div>{p.ownerships.length ? p.ownerships.map((o) => `${o.owner_name} ${o.share_percent}%`).join(", ") : <span className="badge b-warn">Not set</span>}</div>
              </div>
              <LoansCard prop={p} />
            </div>
          ))}
        </div>
        <OwnersCard owners={owners ?? []} reload={() => { reloadOwners(); refresh(); }} />
      </div>
      {edit !== undefined && <PropertyEditor prop={edit} owners={owners ?? []} onClose={() => setEdit(undefined)} onSaved={refresh} />}
    </>
  );
}
