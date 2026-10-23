import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, currentFy, fmtDate, money, qs, today, Transaction } from "../api";
import { CategorySelect, Drawer, ErrorBox, KindBadge, PropertySelect, useLoad, useLocalState, useSession } from "../components";

type Draft = {
  property_id: number | ""; category_id: number | ""; date: string; amount: string; deductible_percent: string;
  payee: string; description: string; reference: string; period_start: string; period_end: string; needs_review: boolean; notes: string;
};

function toDraft(t: Transaction | null, defaults: Partial<Draft>): Draft {
  if (!t) return { property_id: "", category_id: "", date: today(), amount: "", deductible_percent: "100", payee: "", description: "", reference: "", period_start: "", period_end: "", needs_review: false, notes: "", ...defaults };
  return {
    property_id: t.property_id, category_id: t.category_id, date: t.date, amount: String(t.amount), deductible_percent: String(t.deductible_percent),
    payee: t.payee ?? "", description: t.description ?? "", reference: t.reference ?? "", period_start: t.period_start ?? "", period_end: t.period_end ?? "",
    needs_review: t.needs_review, notes: t.notes ?? "",
  };
}

export function TransactionEditor({ txn, onClose, onSaved, defaults = {} }: { txn: Transaction | null; onClose: () => void; onSaved: () => void; defaults?: Partial<Draft> }) {
  const { properties, categories, canEdit, toast } = useSession();
  const [d, setD] = useState<Draft>(() => toDraft(txn, { property_id: properties.length === 1 ? properties[0].id : "", ...defaults }));
  const [files, setFiles] = useState<File[]>([]);
  const [current, setCurrent] = useState(txn);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const cat = categories.find((c) => c.id === d.category_id);
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setD((x) => ({ ...x, [k]: v }));

  const save = async (e: FormEvent, again = false) => {
    e.preventDefault();
    setBusy(true); setErr(null);
    const body = {
      ...d, amount: d.amount, deductible_percent: d.deductible_percent || "100",
      period_start: d.period_start || null, period_end: d.period_end || null,
      payee: d.payee || null, description: d.description || null, reference: d.reference || null, notes: d.notes || null,
    };
    try {
      const saved = current
        ? await api<Transaction>(`/api/transactions/${current.id}`, { method: "PATCH", body })
        : await api<Transaction>("/api/transactions", { body });
      if (files.length) {
        const fd = new FormData();
        files.forEach((f) => fd.append("files", f));
        await api(`/api/transactions/${saved.id}/attachments`, { form: fd });
      }
      toast(current ? "Transaction updated" : "Transaction added");
      onSaved();
      if (again) { setCurrent(null); setFiles([]); setD(toDraft(null, { property_id: d.property_id, category_id: d.category_id, date: d.date })); }
      else onClose();
    } catch (ex) { setErr((ex as Error).message); } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!current || !confirm("Delete this transaction and its attachments?")) return;
    await api(`/api/transactions/${current.id}`, { method: "DELETE" });
    toast("Transaction deleted"); onSaved(); onClose();
  };
  const removeAtt = async (id: number) => {
    if (!confirm("Remove this attachment?")) return;
    await api(`/api/attachments/${id}`, { method: "DELETE" });
    setCurrent(await api<Transaction>(`/api/transactions/${current!.id}`));
    onSaved();
  };
  const ro = !canEdit;
  return (
    <Drawer title={current ? "Edit transaction" : "New transaction"} onClose={onClose}
      footer={ro ? <span className="muted">Read-only access</span> : (
        <>
          <div>{current && <button type="button" className="danger" onClick={remove}>Delete</button>}</div>
          <div className="toolbar">
            {!current && <button type="button" disabled={busy} onClick={(e) => save(e, true)}>Save & add another</button>}
            <button className="primary" form="txn-form" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
          </div>
        </>
      )}>
      <form id="txn-form" onSubmit={save} className="form-grid">
        <div className="full"><ErrorBox error={err} /></div>
        <label className="field">Property
          <select required disabled={ro} value={d.property_id} onChange={(e) => set("property_id", e.target.value ? Number(e.target.value) : "")}>
            <option value="">Choose…</option>
            {properties.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        <label className="field">Category
          <CategorySelect required value={d.category_id} onChange={(v) => set("category_id", v)} includeEmpty="Choose…" />
          {cat && <small>{cat.kind === "excluded" ? "Tracked but not claimed" : `Schedule: ${cat.ato_label}`}</small>}
        </label>
        <label className="field">Date paid / received<input type="date" required disabled={ro} value={d.date} onChange={(e) => set("date", e.target.value)} /></label>
        <label className="field">Amount (incl. GST)<input inputMode="decimal" required disabled={ro} placeholder="0.00" value={d.amount} onChange={(e) => set("amount", e.target.value)} /></label>
        <label className="field">Payee / from<input disabled={ro} value={d.payee} onChange={(e) => set("payee", e.target.value)} placeholder="e.g. Youi, Council, Urban Utilities" /></label>
        <label className="field">Reference<input disabled={ro} value={d.reference} onChange={(e) => set("reference", e.target.value)} placeholder="Invoice / receipt no." /></label>
        <label className="field full">Description<input disabled={ro} value={d.description} onChange={(e) => set("description", e.target.value)} /></label>
        <label className="field">Bill period from<input type="date" disabled={ro} value={d.period_start} onChange={(e) => set("period_start", e.target.value)} /></label>
        <label className="field">Bill period to<input type="date" disabled={ro} value={d.period_end} onChange={(e) => set("period_end", e.target.value)} /></label>
        <label className="field">Claimable %<small>Lower this for private use (e.g. a partly private loan)</small>
          <input type="number" min={0} max={100} step="0.01" disabled={ro} value={d.deductible_percent} onChange={(e) => set("deductible_percent", e.target.value)} />
        </label>
        <div className="field" style={{ justifyContent: "flex-end" }}>
          <label className="check"><input type="checkbox" disabled={ro} checked={d.needs_review} onChange={(e) => set("needs_review", e.target.checked)} />Flag for review</label>
        </div>
        <label className="field full">Notes for the accountant<textarea disabled={ro} value={d.notes} onChange={(e) => set("notes", e.target.value)} /></label>
        <div className="field full">
          Receipts & documents
          <div className="chips">
            {current?.attachments.map((a) => (
              <span className="chip" key={a.id}>
                <a href={`/api/attachments/${a.id}`} target="_blank" rel="noreferrer">📎 {a.filename}</a>
                {!ro && <button type="button" className="ghost small" onClick={() => removeAtt(a.id)} aria-label={`Remove ${a.filename}`}>✕</button>}
              </span>
            ))}
            {files.map((f) => <span className="chip" key={f.name}>⬆ {f.name}</span>)}
          </div>
          {!ro && <input type="file" multiple accept="image/*,application/pdf,.xlsx,.docx,.csv,.txt,.eml" onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />}
          <small>Photos of receipts, PDF invoices, agent statements. Saved with the transaction and included in the accountant pack.</small>
        </div>
      </form>
    </Drawer>
  );
}

export default function TransactionsPage() {
  const { properties, canEdit, toast } = useSession();
  const [params, setParams] = useSearchParams();
  const [fy, setFy] = useLocalState<number | "">("rm.txFy", currentFy());
  const [prop, setProp] = useState<number | "">("");
  const [cat, setCat] = useState<number | "">("");
  const [kind, setKind] = useState("");
  const [q, setQ] = useState("");
  const [review, setReview] = useState(params.get("review") === "1");
  const [noReceipt, setNoReceipt] = useState(false);
  const [editing, setEditing] = useState<Transaction | null | undefined>(params.get("new") === "1" ? null : undefined);
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [bulkCat, setBulkCat] = useState<number | "">("");
  const [debouncedQ, setDebouncedQ] = useState("");
  useEffect(() => { const t = setTimeout(() => setDebouncedQ(q), 250); return () => clearTimeout(t); }, [q]);

  const { data, error, reload, loading } = useLoad(
    () => api<{ total: number; items: Transaction[] }>(`/api/transactions${qs({ fy, property_id: prop, category_id: cat, kind, q: debouncedQ, needs_review: review || undefined, missing_receipt: noReceipt || undefined, limit: 2000 })}`),
    [fy, prop, cat, kind, debouncedQ, review, noReceipt],
  );
  useEffect(() => setSel(new Set()), [data]);
  const totals = useMemo(() => {
    const t = { income: 0, expense: 0 };
    data?.items.forEach((x) => { if (x.kind === "income") t.income += x.claimable_amount; else if (x.kind === "expense") t.expense += x.claimable_amount; });
    return t;
  }, [data]);

  const closeEditor = () => { setEditing(undefined); if (params.get("new")) { params.delete("new"); setParams(params, { replace: true }); } };
  const bulk = async (body: object, msg: string) => {
    await api("/api/transactions/bulk", { body: { ids: Array.from(sel), ...body } });
    toast(msg); reload();
  };
  const toggleAll = () => setSel(sel.size === data?.items.length ? new Set() : new Set(data?.items.map((t) => t.id)));

  return (
    <>
      <div className="page-head">
        <div><h1>Transactions</h1><p>{data ? `${data.total} shown · income ${money(totals.income)} · expenses ${money(totals.expense)}` : " "}</p></div>
        {canEdit && <div className="toolbar"><button className="primary" onClick={() => setEditing(null)} disabled={!properties.length}>+ Add transaction</button></div>}
      </div>
      <ErrorBox error={error} />
      <div className="card">
        <div className="inline-filters">
          <select value={fy} onChange={(e) => setFy(e.target.value ? Number(e.target.value) : "")} style={{ width: "auto" }} aria-label="Financial year">
            <option value="">All years</option>
            {[0, 1, 2, 3, 4].map((i) => { const y = currentFy() - i; return <option key={y} value={y}>FY {y - 1}-{String(y).slice(-2)}</option>; })}
          </select>
          {properties.length > 1 && <PropertySelect value={prop} onChange={setProp} />}
          <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: "auto" }} aria-label="Type">
            <option value="">Income & expenses</option><option value="income">Income</option><option value="expense">Expenses</option><option value="excluded">Not claimed</option>
          </select>
          <div style={{ minWidth: 180, maxWidth: 240 }}><CategorySelect value={cat} onChange={setCat} includeEmpty="All categories" /></div>
          <input type="search" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 200 }} />
          <label className="check"><input type="checkbox" checked={review} onChange={(e) => setReview(e.target.checked)} />Needs review</label>
          <label className="check"><input type="checkbox" checked={noReceipt} onChange={(e) => setNoReceipt(e.target.checked)} />No receipt</label>
        </div>
        {canEdit && sel.size > 0 && (
          <div className="sel-bar">
            <b>{sel.size} selected</b>
            <div style={{ minWidth: 180 }}><CategorySelect value={bulkCat} onChange={setBulkCat} includeEmpty="Move to category…" /></div>
            <button className="small" disabled={!bulkCat} onClick={() => bulk({ category_id: bulkCat }, "Category updated")}>Apply</button>
            <button className="small" onClick={() => bulk({ needs_review: false }, "Marked as reviewed")}>Mark reviewed</button>
            <button className="small" onClick={() => bulk({ needs_review: true }, "Flagged for review")}>Flag</button>
            <button className="small danger" onClick={() => confirm(`Delete ${sel.size} transaction(s)?`) && bulk({ delete: true }, "Deleted")}>Delete</button>
          </div>
        )}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {canEdit && <th style={{ width: 34 }}><input type="checkbox" aria-label="Select all" checked={!!data?.items.length && sel.size === data.items.length} onChange={toggleAll} /></th>}
                <th>Date</th><th>Category</th><th className="hide-sm">Details</th>{properties.length > 1 && <th className="hide-sm">Property</th>}
                <th className="num">Amount</th><th className="hide-sm" style={{ width: 70 }}></th>
              </tr>
            </thead>
            <tbody className={loading ? "spin" : ""}>
              {data?.items.map((t) => (
                <tr key={t.id} className="clickable" onClick={() => setEditing(t)}>
                  {canEdit && <td onClick={(e) => e.stopPropagation()}><input type="checkbox" aria-label="Select" checked={sel.has(t.id)} onChange={() => { const n = new Set(sel); n.has(t.id) ? n.delete(t.id) : n.add(t.id); setSel(n); }} /></td>}
                  <td>{fmtDate(t.date)}</td>
                  <td>{t.category_name}<div className="sub"><KindBadge kind={t.kind} /></div></td>
                  <td className="hide-sm">{t.payee && <b>{t.payee} </b>}{t.description}{t.notes && <div className="sub">{t.notes}</div>}</td>
                  {properties.length > 1 && <td className="hide-sm">{t.property_name}</td>}
                  <td className={`num ${t.kind === "income" ? "pos" : ""}`}>
                    {money(t.amount)}
                    {t.deductible_percent < 100 && <div className="sub">{t.deductible_percent}% → {money(t.claimable_amount)}</div>}
                  </td>
                  <td className="hide-sm">
                    {t.attachments.length > 0 && <span title={`${t.attachments.length} attachment(s)`}>📎</span>}{" "}
                    {t.needs_review && <span className="badge b-warn">Review</span>}
                  </td>
                </tr>
              ))}
              {data && data.items.length === 0 && <tr><td colSpan={7} className="empty">No transactions match these filters.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      {editing !== undefined && (
        <TransactionEditor txn={editing} onClose={closeEditor} onSaved={reload}
          defaults={prop ? { property_id: prop } : {}} />
      )}
    </>
  );
}
