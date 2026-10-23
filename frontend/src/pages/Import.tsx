import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate, fyLabel, money, PreviewRow } from "../api";
import { CategorySelect, ErrorBox, PropertySelect, useLoad, useSession } from "../components";

type Preview = { filename: string; sheets: { sheet: string; fy?: number | null; rows: number; skipped?: string }[]; rows: PreviewRow[] };
type Batch = { id: number; filename: string; row_count: number; remaining: number; created_at: string };

export default function ImportPage() {
  const { properties, toast, reload: reloadSession } = useSession();
  const [prop, setProp] = useState<number | "">(properties.length === 1 ? properties[0].id : "");
  const [file, setFile] = useState<File | null>(null);
  const [over, setOver] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [rows, setRows] = useState<PreviewRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [onlyIssues, setOnlyIssues] = useState(false);
  const [learn, setLearn] = useState(true);
  const { data: batches, reload: reloadBatches } = useLoad(() => api<Batch[]>("/api/imports"), []);

  const upload = async (f: File) => {
    if (!prop) { setErr("Choose the property these transactions belong to first."); return; }
    setFile(f); setBusy(true); setErr(null);
    const fd = new FormData();
    fd.append("property_id", String(prop));
    fd.append("file", f);
    try {
      const p = await api<Preview>("/api/imports/preview", { form: fd });
      setPreview(p); setRows(p.rows);
    } catch (ex) { setErr((ex as Error).message); } finally { setBusy(false); }
  };
  const update = (id: string, patch: Partial<PreviewRow>) => setRows((rs) => rs.map((r) => (r.row_id === id ? { ...r, ...patch } : r)));
  const stats = useMemo(() => {
    const inc = rows.filter((r) => r.action !== "skip");
    return {
      tx: inc.filter((r) => r.action === "transaction").length,
      bal: inc.filter((r) => r.action === "loan_balance").length,
      skip: rows.length - inc.length,
      missingCat: inc.filter((r) => r.action === "transaction" && !r.category_id).length,
      missingDate: inc.filter((r) => !r.date || r.amount === null).length,
      total: inc.filter((r) => r.action === "transaction").reduce((s, r) => s + (r.amount ?? 0), 0),
    };
  }, [rows]);

  const commit = async () => {
    setBusy(true); setErr(null);
    try {
      const res = await api<{ transactions: number; loan_balances: number }>("/api/imports/commit", {
        body: { property_id: prop, filename: preview!.filename, rows, learn_mappings: learn },
      });
      toast(`Imported ${res.transactions} transaction(s)${res.loan_balances ? ` and ${res.loan_balances} loan balance(s)` : ""}`);
      setPreview(null); setRows([]); setFile(null); reloadBatches(); reloadSession();
    } catch (ex) { setErr((ex as Error).message); } finally { setBusy(false); }
  };
  const undo = async (b: Batch) => {
    if (!confirm(`Remove the ${b.remaining} transaction(s) imported from ${b.filename}?`)) return;
    await api(`/api/imports/${b.id}`, { method: "DELETE" });
    toast("Import undone"); reloadBatches();
  };

  if (!properties.length) return <div className="card empty">Add a property first, then come back to import. <Link to="/properties">Properties →</Link></div>;
  const shown = onlyIssues ? rows.filter((r) => r.issues.length || r.action === "skip" || !r.category_id) : rows;

  return (
    <>
      <div className="page-head">
        <div><h1>Import</h1><p>Bring in your existing spreadsheets or a bank export. You'll check every row before anything is saved.</p></div>
      </div>
      <ErrorBox error={err} />
      {!preview && (
        <div className="grid grid-main" style={{ alignItems: "start" }}>
          <div className="card card-pad stack">
            <label className="field">Property<PropertySelect value={prop} onChange={setProp} allowAll={!prop} label="Choose a property…" /></label>
            <label
              className={`dropzone ${over ? "over" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) upload(f); }}
            >
              <input type="file" accept=".xlsx,.xlsm,.csv" hidden onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
              <div style={{ fontSize: "1.6rem" }}>⬆</div>
              <b>{busy ? `Reading ${file?.name}…` : "Drop an Excel or CSV file here, or click to choose"}</b>
              <div className="sub">Works with one sheet per financial year (Date · Item · Value) and bank CSVs (Date · Description · Amount or Debit/Credit).</div>
            </label>
          </div>
          <div className="card">
            <div className="card-head"><h2>Previous imports</h2></div>
            <div className="table-wrap"><table><tbody>
              {batches?.map((b) => (
                <tr key={b.id}><td>{b.filename}<div className="sub">{fmtDate(b.created_at)} · {b.remaining} of {b.row_count} rows remain</div></td>
                  <td>{b.remaining > 0 && <button className="small ghost danger" onClick={() => undo(b)}>Undo</button>}</td></tr>
              ))}
              {batches?.length === 0 && <tr><td className="empty">No imports yet</td></tr>}
            </tbody></table></div>
          </div>
        </div>
      )}

      {preview && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>{preview.filename}</h2>
              <div className="sub muted">
                {preview.sheets.map((s) => `${s.sheet.trim()}${s.fy ? ` (FY ${fyLabel(s.fy)})` : ""}: ${s.skipped ?? `${s.rows} rows`}`).join(" · ")}
              </div>
            </div>
            <div className="toolbar">
              <label className="check"><input type="checkbox" checked={onlyIssues} onChange={(e) => setOnlyIssues(e.target.checked)} />Only rows needing attention</label>
              <button onClick={() => { setPreview(null); setRows([]); }}>Cancel</button>
              <button className="primary" disabled={busy || stats.missingCat > 0 || stats.missingDate > 0 || stats.tx + stats.bal === 0} onClick={commit}>
                Import {stats.tx} transaction(s){stats.bal ? ` + ${stats.bal} balance` : ""}
              </button>
            </div>
          </div>
          <div className="inline-filters" style={{ justifyContent: "space-between" }}>
            <span>
              <b>{money(stats.total)}</b> to import · {stats.skip} skipped
              {stats.missingCat > 0 && <span className="badge b-warn" style={{ marginLeft: 8 }}>{stats.missingCat} need a category</span>}
              {stats.missingDate > 0 && <span className="badge b-warn" style={{ marginLeft: 8 }}>{stats.missingDate} need a date/amount</span>}
            </span>
            <label className="check"><input type="checkbox" checked={learn} onChange={(e) => setLearn(e.target.checked)} />Remember my category choices for next time</label>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Import as</th><th>Sheet / row</th><th>Item</th><th>Date</th><th className="num">Amount</th><th>Category</th><th>Notes</th></tr></thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.row_id} className={r.action === "skip" ? "muted" : ""}>
                    <td>
                      <select value={r.action} onChange={(e) => update(r.row_id, { action: e.target.value as PreviewRow["action"] })} style={{ minWidth: 130 }}>
                        <option value="transaction">Transaction</option><option value="loan_balance">Loan balance</option><option value="skip">Skip</option>
                      </select>
                    </td>
                    <td className="sub">{r.sheet.trim()} · {r.row_number}</td>
                    <td>{r.description}</td>
                    <td><input type="date" value={r.date ?? ""} onChange={(e) => update(r.row_id, { date: e.target.value || null })} style={{ minWidth: 140 }} /></td>
                    <td className="num"><input inputMode="decimal" value={r.amount ?? ""} onChange={(e) => update(r.row_id, { amount: e.target.value === "" ? null : Number(e.target.value) })} style={{ width: 110, textAlign: "right" }} /></td>
                    <td style={{ minWidth: 190 }}>
                      {r.action === "loan_balance" ? <span className="sub">Rate <input style={{ width: 70 }} value={r.interest_rate ?? ""} onChange={(e) => update(r.row_id, { interest_rate: e.target.value ? Number(e.target.value) : null })} />%</span>
                        : <CategorySelect value={r.category_id} onChange={(v) => update(r.row_id, { category_id: v || null })} includeEmpty="Choose…" />}
                    </td>
                    <td style={{ maxWidth: 360 }}>
                      {r.issues.map((i, k) => <div key={k} className="sub" style={{ color: i.startsWith("Already") || i.startsWith("Same as") ? "var(--muted)" : "var(--warn)" }}>{i}</div>)}
                      {r.action === "transaction" && <label className="check sub"><input type="checkbox" checked={r.needs_review} onChange={(e) => update(r.row_id, { needs_review: e.target.checked })} />flag for review</label>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
