import { FormEvent, useCallback, useEffect, useState } from "react";
import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, Category, Property, User } from "./api";
import { ErrorBox, Icon, SessionCtx } from "./components";
import DashboardPage from "./pages/Dashboard";
import TransactionsPage from "./pages/Transactions";
import PropertiesPage from "./pages/Properties";
import ImportPage from "./pages/Import";
import ReportsPage from "./pages/Reports";
import SettingsPage from "./pages/Settings";
import RoadmapPage from "./pages/Roadmap";

type Me = { user: User; portfolio: { id: number; name: string } };

function ForgotScreen({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const r = await api<{ message: string }>("/api/auth/forgot-password", { body: { email } });
      setSent(r.message);
    } catch (ex) { setErr((ex as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="auth-wrap">
      <form className="card auth-card stack" onSubmit={submit}>
        <div>
          <h1>Forgot password</h1>
          <p className="muted" style={{ margin: 0 }}>Enter your login email and we'll send you a link to choose a new password.</p>
        </div>
        <ErrorBox error={err} />
        {sent ? (
          <div className="alert success" role="status">{sent} Check your inbox (and spam folder).</div>
        ) : (
          <>
            <label className="field">Email<input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <button className="primary" disabled={busy}>{busy ? "Please wait…" : "Email me a reset link"}</button>
          </>
        )}
        <button type="button" className="link" onClick={onBack}>Back to sign in</button>
      </form>
    </div>
  );
}

function ResetScreen({ token, onDone }: { token: string; onDone: () => void }) {
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (pw !== pw2) return setErr("Passwords don't match");
    setBusy(true); setErr(null);
    try {
      await api("/api/auth/reset-password", { body: { token, new_password: pw } });
      window.history.replaceState(null, "", "/");
      onDone();
    } catch (ex) { setErr((ex as Error).message); } finally { setBusy(false); }
  };
  const back = () => { window.history.replaceState(null, "", "/"); onDone(); };
  return (
    <div className="auth-wrap">
      <form className="card auth-card stack" onSubmit={submit}>
        <div>
          <h1>Choose a new password</h1>
          <p className="muted" style={{ margin: 0 }}>You'll be signed in once it's saved.</p>
        </div>
        <ErrorBox error={err} />
        <label className="field">New password<small>At least 8 characters</small><input type="password" autoComplete="new-password" minLength={8} required value={pw} onChange={(e) => setPw(e.target.value)} /></label>
        <label className="field">Confirm new password<input type="password" autoComplete="new-password" minLength={8} required value={pw2} onChange={(e) => setPw2(e.target.value)} /></label>
        <button className="primary" disabled={busy}>{busy ? "Please wait…" : "Save password"}</button>
        <button type="button" className="link" onClick={back}>Back to sign in</button>
      </form>
    </div>
  );
}

function AuthScreen({ setup, onDone, onForgot }: { setup: boolean; onDone: () => void; onForgot?: () => void }) {
  const [f, setF] = useState({ portfolio_name: "", name: "", email: "", password: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      if (setup) await api("/api/auth/setup", { body: f });
      else await api("/api/auth/login", { body: { email: f.email, password: f.password } });
      onDone();
    } catch (ex) { setErr((ex as Error).message); } finally { setBusy(false); }
  };
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="auth-wrap">
      <form className="card auth-card stack" onSubmit={submit}>
        <div>
          <h1>{setup ? "Set up Rental Manager" : "Sign in"}</h1>
          <p className="muted" style={{ margin: 0 }}>{setup ? "Create your portfolio and the first admin login." : "Rental income, expenses and tax-time reports."}</p>
        </div>
        <ErrorBox error={err} />
        {setup && <label className="field">Portfolio name<small>e.g. your family name or entity</small><input required value={f.portfolio_name} onChange={set("portfolio_name")} /></label>}
        {setup && <label className="field">Your name<input required value={f.name} onChange={set("name")} /></label>}
        <label className="field">Email<input type="email" autoComplete="username" required value={f.email} onChange={set("email")} /></label>
        <label className="field">Password{setup && <small>At least 8 characters</small>}<input type="password" autoComplete={setup ? "new-password" : "current-password"} minLength={setup ? 8 : undefined} required value={f.password} onChange={set("password")} /></label>
        <button className="primary" disabled={busy}>{busy ? "Please wait…" : setup ? "Create portfolio" : "Sign in"}</button>
        {!setup && onForgot && <button type="button" className="link" onClick={onForgot}>Forgot password?</button>}
      </form>
    </div>
  );
}

export default function App() {
  const [state, setState] = useState<"loading" | "setup" | "login" | "forgot" | "ready">("loading");
  const [emailReset, setEmailReset] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(() =>
    window.location.pathname === "/reset-password" ? new URLSearchParams(window.location.search).get("token") : null);
  const [me, setMe] = useState<Me | null>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const [p, c] = await Promise.all([api<Property[]>("/api/properties"), api<Category[]>("/api/categories")]);
    setProperties(p); setCategories(c);
  }, []);

  const boot = useCallback(async () => {
    try {
      const st = await api<{ setup_required: boolean; email_reset: boolean }>("/api/auth/status");
      setEmailReset(!!st.email_reset);
      if (st.setup_required) return setState("setup");
      const m = await api<Me>("/api/auth/me");
      setMe(m);
      await reload();
      setState("ready");
    } catch { setState("login"); }
  }, [reload]);

  useEffect(() => { boot(); }, [boot]);
  useEffect(() => {
    const h = () => setState("login");
    window.addEventListener("rm:unauthorised", h);
    return () => window.removeEventListener("rm:unauthorised", h);
  }, []);
  const toast = useCallback((m: string) => { setToastMsg(m); setTimeout(() => setToastMsg(null), 3200); }, []);

  if (resetToken) return <ResetScreen token={resetToken} onDone={() => { setResetToken(null); boot(); }} />;
  if (state === "loading") return <div className="empty">Loading…</div>;
  if (state === "forgot") return <ForgotScreen onBack={() => setState("login")} />;
  if (state === "setup" || state === "login")
    return <AuthScreen setup={state === "setup"} onDone={boot} onForgot={emailReset ? () => setState("forgot") : undefined} />;
  if (!me) return null;

  const logout = async () => { await api("/api/auth/logout", { method: "POST" }); setMe(null); setState("login"); };
  const session = {
    ...me, properties, categories, reload, toast, logout,
    canEdit: me.user.role !== "viewer", isAdmin: me.user.role === "admin",
  };
  const nav: [string, string, JSX.Element][] = [
    ["/", "Dashboard", Icon.dash], ["/transactions", "Transactions", Icon.list], ["/properties", "Properties", Icon.home],
    ...(session.canEdit ? [["/import", "Import", Icon.upload] as [string, string, JSX.Element]] : []),
    ["/reports", "Reports", Icon.report], ["/settings", "Settings", Icon.cog], ["/roadmap", "Roadmap", Icon.map],
  ];
  return (
    <SessionCtx.Provider value={session}>
      <BrowserRouter>
        <div className="shell">
          <aside className="sidebar">
            <div className="brand">
              <img src="/favicon.svg" width={30} height={30} alt="" />
              <div>Rental Manager<small>{me.portfolio.name}</small></div>
            </div>
            <nav className="nav">
              {nav.map(([to, label, icon]) => (
                <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `${isActive ? "active" : ""} ${to === "/roadmap" ? "desktop-only" : ""}`}>{icon}<span>{label}</span></NavLink>
              ))}
            </nav>
            <div className="spacer" />
            <div className="userbox">
              <b>{me.user.name}</b>{me.user.role === "viewer" ? "Read-only" : me.user.role === "admin" ? "Admin" : "Editor"}
              <div><button className="small" onClick={logout}>Sign out</button></div>
            </div>
          </aside>
          <main>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/transactions" element={<TransactionsPage />} />
              <Route path="/properties" element={<PropertiesPage />} />
              <Route path="/import" element={<ImportPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/roadmap" element={<RoadmapPage />} />
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </main>
        </div>
        {toastMsg && <div className="toast" role="status">{toastMsg}</div>}
      </BrowserRouter>
    </SessionCtx.Provider>
  );
}
