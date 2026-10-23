export type Role = "admin" | "editor" | "viewer";
export interface User { id: number; email: string; name: string; role: Role; is_active: boolean }
export interface Owner { id: number; name: string; email: string | null; notes: string | null }
export interface Ownership { owner_id: number; owner_name: string; share_percent: number }
export interface Property {
  id: number; name: string; address_line: string | null; suburb: string | null; state: string | null;
  postcode: string | null; property_type: string | null; purchase_date: string | null; purchase_price: number | null;
  first_rented_date: string | null; notes: string | null; archived: boolean; ownerships: Ownership[]; full_address: string;
}
export type Kind = "income" | "expense" | "excluded";
export interface AtoLabel { key: string; label: string; kind: Kind; order: number; help: string }
export interface Category {
  id: number; name: string; ato_key: string; ato_label: string; kind: Kind; keywords: string | null;
  archived: boolean; sort_order: number;
}
export interface Attachment { id: number; filename: string; content_type: string | null; size_bytes: number }
export interface Transaction {
  id: number; property_id: number; property_name: string; category_id: number; category_name: string; ato_key: string;
  kind: Kind; date: string; fy: number; amount: number; deductible_percent: number; claimable_amount: number;
  description: string | null; payee: string | null; reference: string | null; period_start: string | null;
  period_end: string | null; needs_review: boolean; notes: string | null; source: string; attachments: Attachment[];
}
export interface LoanBalance { id: number; as_of: string; balance: number; interest_rate: number | null }
export interface Loan {
  id: number; property_id: number; name: string; lender: string | null; account_hint: string | null;
  start_date: string | null; original_amount: number | null; rental_use_percent: number; notes: string | null;
  balances: LoanBalance[];
}
export interface Check { level: "error" | "warning" | "info"; message: string; property?: string }
export interface ReportLine { key: string; label: string; amount: number; gross_amount: number; categories: { name: string; amount: number }[] }
export interface PropertyReport {
  property: { id: number; name: string; address: string; purchase_date: string | null; purchase_price: number | null; first_rented_date: string | null };
  year: { weeks_rented: number | null; weeks_available: number | null; loan_refinanced: boolean; notes: string | null };
  income: ReportLine[]; expenses: ReportLine[]; excluded: ReportLine[];
  totals: { income: number; expenses: number; net: number; excluded: number };
  owners: { owner_id: number | null; owner_name: string; share_percent: number; income: number; expenses: number; net: number }[];
  loans: { id: number; name: string; lender: string | null; account_hint: string | null; rental_use_percent: number; balance: number | null; balance_date: string | null; interest_rate: number | null }[];
  transaction_count: number; checks: Check[];
}
export interface FyReport {
  fy: number; fy_label: string; start: string; end: string; properties: PropertyReport[];
  totals: { income: number; expenses: number; net: number; excluded: number };
  owners: { owner_name: string; income: number; expenses: number; net: number }[];
}
export interface YearSummary { fy: number; fy_label: string; income: number; expenses: number; net: number; by_label: Record<string, number> }
export interface Dashboard {
  fy: number; fy_label: string; current_fy: number; totals: FyReport["totals"];
  expenses_by_label: { key: string; label: string; amount: number }[];
  monthly: { month: string; label: string; income: number; expenses: number }[];
  years: YearSummary[]; checks: Check[]; needs_review: number; recent: Transaction[];
}
export interface PreviewRow {
  row_id: string; sheet: string; row_number: number; raw_date: string | null; description: string; amount: number | null;
  date: string | null; fy: number | null; category_id: number | null; suggested_category_id: number | null;
  action: "transaction" | "loan_balance" | "skip"; needs_review: boolean; issues: string[]; duplicate_of: number | null;
  interest_rate: number | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

function errorText(body: unknown, fallback: string): string {
  const d = (body as { detail?: unknown })?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (x as { msg?: string }).msg?.replace(/^Value error, /, "") ?? "").join("; ");
  return fallback;
}

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const init: RequestInit = { method: opts.method ?? (opts.body || opts.form ? "POST" : "GET"), credentials: "same-origin" };
  if (opts.form) init.body = opts.form;
  else if (opts.body !== undefined) {
    init.body = JSON.stringify(opts.body);
    init.headers = { "Content-Type": "application/json" };
  }
  const res = await fetch(path, init);
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  const body = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/api/auth")) window.dispatchEvent(new Event("rm:unauthorised"));
    throw new ApiError(res.status, errorText(body, `Request failed (${res.status})`));
  }
  return body as T;
}

export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

const aud = new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" });
const audWhole = new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 });
export const money = (n: number | null | undefined) => (n === null || n === undefined ? "–" : aud.format(n));
export const moneyShort = (n: number) => audWhole.format(n);
export const fmtDate = (s: string | null | undefined) => {
  if (!s) return "–";
  const [y, m, d] = s.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
};
export const fyLabel = (fy: number) => `${fy - 1}-${String(fy).slice(-2)}`;
export function currentFy(d = new Date()) { return d.getMonth() >= 6 ? d.getFullYear() + 1 : d.getFullYear(); }
export const today = () => new Date().toISOString().slice(0, 10);
