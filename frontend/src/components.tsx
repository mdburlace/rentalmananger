import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { Category, currentFy, fyLabel, Property, User } from "./api";

// ---- session & shared reference data ---------------------------------
interface Session {
  user: User; portfolio: { id: number; name: string };
  properties: Property[]; categories: Category[];
  reload: () => Promise<void>; canEdit: boolean; isAdmin: boolean;
  toast: (msg: string) => void; logout: () => Promise<void>;
}
export const SessionCtx = createContext<Session | null>(null);
export const useSession = () => useContext(SessionCtx)!;

export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]): { data: T | null; error: string | null; loading: boolean; reload: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setLoading(true);
    fn().then((d) => { if (live) { setData(d); setError(null); } })
      .catch((e) => { if (live) setError(e.message); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}

// ---- small UI pieces --------------------------------------------------
export function Drawer({ title, onClose, children, footer }: { title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="drawer" role="dialog" aria-label={title}>
        <div className="drawer-head"><h2>{title}</h2><button className="ghost" onClick={onClose} aria-label="Close">✕</button></div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function FySelect({ value, onChange, years }: { value: number; onChange: (fy: number) => void; years?: number[] }) {
  const cur = currentFy();
  const opts = Array.from(new Set([...(years ?? []), cur, cur - 1, cur - 2, cur - 3])).sort((a, b) => b - a);
  return (
    <select value={value} onChange={(e) => onChange(Number(e.target.value))} aria-label="Financial year" style={{ width: "auto" }}>
      {opts.map((y) => <option key={y} value={y}>FY {fyLabel(y)}{y === cur ? " (current)" : ""}</option>)}
    </select>
  );
}

export function PropertySelect({ value, onChange, allowAll = true, label = "All properties" }: { value: number | ""; onChange: (id: number | "") => void; allowAll?: boolean; label?: string }) {
  const { properties } = useSession();
  return (
    <select value={value} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")} aria-label="Property" style={{ width: "auto" }}>
      {allowAll && <option value="">{label}</option>}
      {properties.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
    </select>
  );
}

export function CategorySelect({ value, onChange, includeEmpty, required }: { value: number | "" | null; onChange: (id: number | "") => void; includeEmpty?: string; required?: boolean }) {
  const { categories } = useSession();
  const groups: [string, string][] = [["income", "Income"], ["expense", "Expenses"], ["excluded", "Not claimed"], ["transfer", "Owner funds (not income or expense)"]];
  return (
    <select value={value ?? ""} required={required} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}>
      {includeEmpty !== undefined && <option value="">{includeEmpty}</option>}
      {groups.map(([k, l]) => (
        <optgroup key={k} label={l}>
          {categories.filter((c) => c.kind === k && (!c.archived || c.id === value)).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </optgroup>
      ))}
    </select>
  );
}

export function KindBadge({ kind }: { kind: string }) {
  const label = { income: "Income", expense: "Expense", excluded: "Not claimed", transfer: "Owner funds" }[kind] ?? kind;
  return <span className={`badge b-${kind}`}>{label}</span>;
}

/** Owners on a property's title – the only people who can contribute or draw funds for it. */
export function OwnerSelect({ propertyId, value, onChange, disabled }: { propertyId: number | ""; value: number | "" | null | undefined; onChange: (id: number | "") => void; disabled?: boolean }) {
  const { properties } = useSession();
  const prop = properties.find((p) => p.id === propertyId);
  const owners = prop?.ownerships ?? [];
  return (
    <select required disabled={disabled || !prop} value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}>
      <option value="">{!prop ? "Choose the property first" : owners.length ? "Choose owner…" : "Set ownership on the property first"}</option>
      {owners.map((o) => <option key={o.owner_id} value={o.owner_id}>{o.owner_name} ({o.share_percent}%)</option>)}
    </select>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  return error ? <div className="alert error" role="alert">{error}</div> : null;
}

export function useLocalState<T>(key: string, initial: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { const s = localStorage.getItem(key); return s ? (JSON.parse(s) as T) : initial; } catch { return initial; }
  });
  const set = (nv: T) => { setV(nv); try { localStorage.setItem(key, JSON.stringify(nv)); } catch { /* ignore */ } };
  return [v, set];
}

export const Icon = {
  dash: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>,
  list: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>,
  home: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 11 12 4l9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg>,
  upload: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 16V4M6 10l6-6 6 6M4 20h16"/></svg>,
  report: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></svg>,
  cog: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>,
  map: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/></svg>,
};
