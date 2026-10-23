import { FormEvent, useState } from "react";
import { api, AtoLabel, Category, User } from "../api";
import { Drawer, ErrorBox, KindBadge, useLoad, useSession } from "../components";

function Categories() {
  const { categories, canEdit, reload, toast } = useSession();
  const { data: labels } = useLoad(() => api<AtoLabel[]>("/api/ato-labels"), []);
  const [edit, setEdit] = useState<Category | null | undefined>(undefined);
  const [f, setF] = useState({ name: "", ato_key: "repairs", keywords: "", archived: false, sort_order: 100 });
  const [err, setErr] = useState<string | null>(null);
  const open = (c: Category | null) => {
    setErr(null);
    setF(c ? { name: c.name, ato_key: c.ato_key, keywords: c.keywords ?? "", archived: c.archived, sort_order: c.sort_order } : { name: "", ato_key: "repairs", keywords: "", archived: false, sort_order: 500 });
    setEdit(c);
  };
  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (edit) await api(`/api/categories/${edit.id}`, { method: "PUT", body: f }); else await api("/api/categories", { body: f });
      await reload(); setEdit(undefined); toast("Category saved");
    } catch (ex) { setErr((ex as Error).message); }
  };
  const remove = async () => {
    try { await api(`/api/categories/${edit!.id}`, { method: "DELETE" }); await reload(); setEdit(undefined); toast("Category deleted"); }
    catch (ex) { setErr((ex as Error).message); }
  };
  const label = labels?.find((l) => l.key === f.ato_key);
  return (
    <div className="card">
      <div className="card-head">
        <div><h2>Categories</h2><div className="sub muted">Name them however you like – each one maps to an ATO rental schedule label so reports always line up.</div></div>
        {canEdit && <button className="small" onClick={() => open(null)}>+ Category</button>}
      </div>
      <div className="table-wrap"><table>
        <thead><tr><th>Category</th><th>Schedule label</th><th className="hide-sm">Import keywords</th></tr></thead>
        <tbody>{categories.map((c) => (
          <tr key={c.id} className={`clickable ${c.archived ? "muted" : ""}`} onClick={() => canEdit && open(c)}>
            <td>{c.name} {c.archived && <span className="badge b-excluded">archived</span>}</td>
            <td><KindBadge kind={c.kind} /> <span className="sub">{c.ato_label}</span></td>
            <td className="hide-sm sub">{c.keywords}</td>
          </tr>
        ))}</tbody>
      </table></div>
      {edit !== undefined && (
        <Drawer title={edit ? "Edit category" : "New category"} onClose={() => setEdit(undefined)}
          footer={<>{edit ? <button className="danger" onClick={remove}>Delete</button> : <span />}<button className="primary" form="cat-form">Save</button></>}>
          <form id="cat-form" className="form-grid" onSubmit={save}>
            <div className="full"><ErrorBox error={err} /></div>
            <label className="field full">Name<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
            <label className="field full">ATO rental schedule label
              <select value={f.ato_key} onChange={(e) => setF({ ...f, ato_key: e.target.value })}>
                {(["income", "expense", "excluded"] as const).map((k) => (
                  <optgroup key={k} label={k === "income" ? "Income" : k === "expense" ? "Expenses" : "Not claimed"}>
                    {labels?.filter((l) => l.kind === k).map((l) => <option key={l.key} value={l.key}>{l.label}</option>)}
                  </optgroup>
                ))}
              </select>
              {label?.help && <small>{label.help}</small>}
            </label>
            <label className="field full">Import keywords<small>Comma separated. Spreadsheet rows containing these words are matched to this category.</small><input value={f.keywords} onChange={(e) => setF({ ...f, keywords: e.target.value })} /></label>
            <label className="field">Sort order<input type="number" value={f.sort_order} onChange={(e) => setF({ ...f, sort_order: Number(e.target.value) })} /></label>
            <label className="check" style={{ alignSelf: "end" }}><input type="checkbox" checked={f.archived} onChange={(e) => setF({ ...f, archived: e.target.checked })} />Archived (hide from pick lists)</label>
          </form>
        </Drawer>
      )}
    </div>
  );
}

function Users() {
  const { user: me, toast } = useSession();
  const { data: users, reload } = useLoad(() => api<User[]>("/api/users"), []);
  const [f, setF] = useState({ name: "", email: "", role: "viewer", password: "" });
  const [err, setErr] = useState<string | null>(null);
  const add = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    try { await api("/api/users", { body: f }); setF({ name: "", email: "", role: "viewer", password: "" }); reload(); toast("User added – share the password with them"); }
    catch (ex) { setErr((ex as Error).message); }
  };
  const patch = async (u: User, body: object) => {
    try { await api(`/api/users/${u.id}`, { method: "PATCH", body }); reload(); } catch (ex) { setErr((ex as Error).message); }
  };
  return (
    <div className="card">
      <div className="card-head"><div><h2>People with access</h2><div className="sub muted">Give your accountant a read-only login so they can download reports themselves.</div></div></div>
      <div className="card-pad stack">
        <ErrorBox error={err} />
        <table><tbody>{users?.map((u) => (
          <tr key={u.id} className={u.is_active ? "" : "muted"}>
            <td>{u.name}<div className="sub">{u.email}</div></td>
            <td>
              <select value={u.role} disabled={u.id === me.id} onChange={(e) => patch(u, { role: e.target.value })} style={{ width: "auto" }}>
                <option value="admin">Admin</option><option value="editor">Editor</option><option value="viewer">Read-only</option>
              </select>
            </td>
            <td>{u.id !== me.id && <>
              <button className="small ghost" onClick={() => { const p = prompt("New password (min 8 characters)"); if (p) patch(u, { password: p }).then(() => toast("Password reset")); }}>Reset password</button>
              <button className="small ghost" onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? "Disable" : "Enable"}</button>
            </>}</td>
          </tr>
        ))}</tbody></table>
        <form className="form-grid" onSubmit={add}>
          <label className="field">Name<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
          <label className="field">Email<input type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
          <label className="field">Access<select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="viewer">Read-only (accountant)</option><option value="editor">Editor</option><option value="admin">Admin</option></select></label>
          <label className="field">Temporary password<input required minLength={8} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
          <div className="full"><button className="primary">Add person</button></div>
        </form>
      </div>
    </div>
  );
}

function Password() {
  const { toast } = useSession();
  const [f, setF] = useState({ current_password: "", new_password: "" });
  const [err, setErr] = useState<string | null>(null);
  const save = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    try { await api("/api/auth/password", { body: f }); setF({ current_password: "", new_password: "" }); toast("Password changed"); }
    catch (ex) { setErr((ex as Error).message); }
  };
  return (
    <div className="card">
      <div className="card-head"><h2>Your password</h2></div>
      <form className="card-pad stack" onSubmit={save}>
        <ErrorBox error={err} />
        <label className="field">Current password<input type="password" autoComplete="current-password" required value={f.current_password} onChange={(e) => setF({ ...f, current_password: e.target.value })} /></label>
        <label className="field">New password<input type="password" autoComplete="new-password" minLength={8} required value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} /></label>
        <div><button>Change password</button></div>
      </form>
    </div>
  );
}

export default function SettingsPage() {
  const { isAdmin } = useSession();
  return (
    <>
      <div className="page-head"><div><h1>Settings</h1></div></div>
      <div className="grid grid-main" style={{ alignItems: "start" }}>
        <Categories />
        <div className="stack">{isAdmin && <Users />}<Password /></div>
      </div>
    </>
  );
}
