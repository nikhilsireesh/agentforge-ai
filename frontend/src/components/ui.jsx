// Small, reusable UI building blocks (cards, buttons, badges, modals...).
import { AlertTriangle, Loader2, X } from "lucide-react";
import { useEffect } from "react";
import { humanize } from "../utils/format";

export function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function Card({ className = "", children, ...props }) {
  return (
    <div className={cx("bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_3px_rgba(15,23,42,0.05)]", className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, icon: Icon, actions, className = "" }) {
  return (
    <div className={cx("flex items-start justify-between gap-3 px-5 pt-5 pb-3", className)}>
      <div className="flex items-start gap-3 min-w-0">
        {Icon && (
          <div className="mt-0.5 rounded-lg bg-violet-50 p-2 text-violet-600">
            <Icon size={16} />
          </div>
        )}
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900 truncate">{title}</h3>
          {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

const BUTTON_VARIANTS = {
  primary: "bg-violet-600 text-white hover:bg-violet-700 shadow-sm shadow-violet-600/20",
  secondary: "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50",
  success: "bg-emerald-600 text-white hover:bg-emerald-700",
  warning: "bg-amber-500 text-white hover:bg-amber-600",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "text-slate-600 hover:bg-slate-100",
};

export function Button({ variant = "primary", size = "md", icon: Icon, loading, className = "", children, disabled, ...props }) {
  const sizes = { sm: "px-2.5 py-1.5 text-xs gap-1.5", md: "px-3.5 py-2 text-sm gap-2", lg: "px-5 py-2.5 text-sm gap-2" };
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer",
        BUTTON_VARIANTS[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 size={size === "sm" ? 13 : 15} className="animate-spin" /> : Icon && <Icon size={size === "sm" ? 13 : 15} />}
      {children}
    </button>
  );
}

const STATUS_STYLES = {
  pending: "bg-slate-100 text-slate-600 ring-slate-200",
  running: "bg-blue-50 text-blue-700 ring-blue-200",
  in_progress: "bg-blue-50 text-blue-700 ring-blue-200",
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  approved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  passed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  covered: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  live: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  ok: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  failed: "bg-red-50 text-red-700 ring-red-200",
  error: "bg-red-50 text-red-700 ring-red-200",
  rejected: "bg-red-50 text-red-700 ring-red-200",
  critical: "bg-red-50 text-red-700 ring-red-200",
  not_covered: "bg-red-50 text-red-700 ring-red-200",
  high: "bg-orange-50 text-orange-700 ring-orange-200",
  waiting_approval: "bg-amber-50 text-amber-800 ring-amber-200",
  awaiting_approval: "bg-amber-50 text-amber-800 ring-amber-200",
  revision_requested: "bg-amber-50 text-amber-800 ring-amber-200",
  changes_requested: "bg-amber-50 text-amber-800 ring-amber-200",
  partial: "bg-amber-50 text-amber-800 ring-amber-200",
  medium: "bg-amber-50 text-amber-800 ring-amber-200",
  mock: "bg-amber-50 text-amber-800 ring-amber-200",
  unavailable: "bg-amber-50 text-amber-800 ring-amber-200",
  unverified: "bg-amber-50 text-amber-800 ring-amber-200",
  cancelled: "bg-slate-100 text-slate-500 ring-slate-200",
  skipped: "bg-slate-50 text-slate-400 ring-slate-200",
  draft: "bg-slate-100 text-slate-600 ring-slate-200",
  archived: "bg-slate-100 text-slate-500 ring-slate-200",
  low: "bg-slate-100 text-slate-600 ring-slate-200",
};

const DOT_STYLES = {
  running: "bg-blue-500 animate-pulse",
  in_progress: "bg-blue-500 animate-pulse",
  waiting_approval: "bg-amber-500 animate-pulse",
  awaiting_approval: "bg-amber-500",
};

export function StatusBadge({ status, label, className = "" }) {
  if (!status) return <span className="text-slate-400 text-xs">—</span>;
  const style = STATUS_STYLES[status] || "bg-slate-100 text-slate-600 ring-slate-200";
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap", style, className)}>
      <span className={cx("h-1.5 w-1.5 rounded-full bg-current opacity-70", DOT_STYLES[status])} />
      {label || humanize(status)}
    </span>
  );
}

export function Spinner({ label = "Loading…", className = "" }) {
  return (
    <div className={cx("flex items-center justify-center gap-2 py-10 text-sm text-slate-500", className)}>
      <Loader2 size={18} className="animate-spin text-violet-500" /> {label}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6">
      {Icon && (
        <div className="rounded-2xl bg-violet-50 p-3 text-violet-500 mb-3">
          <Icon size={22} />
        </div>
      )}
      <h3 className="font-semibold text-slate-800">{title}</h3>
      {description && <p className="text-sm text-slate-500 mt-1 max-w-md">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBanner({ error, className = "" }) {
  if (!error) return null;
  return (
    <div role="alert" className={cx("flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700", className)}>
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <span>{error}</span>
    </div>
  );
}

export function Notice({ tone = "info", icon: Icon, children, className = "" }) {
  const tones = {
    info: "border-violet-200 bg-violet-50 text-violet-800",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  };
  return (
    <div className={cx("flex items-start gap-2 rounded-xl border px-4 py-3 text-sm", tones[tone], className)}>
      {Icon && <Icon size={16} className="mt-0.5 shrink-0" />}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function StatCard({ label, value, icon: Icon, hint, tone = "violet" }) {
  const tones = {
    violet: "bg-violet-50 text-violet-600",
    blue: "bg-blue-50 text-blue-600",
    green: "bg-emerald-50 text-emerald-600",
    red: "bg-red-50 text-red-600",
    amber: "bg-amber-50 text-amber-600",
    slate: "bg-slate-100 text-slate-600",
  };
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        {Icon && (
          <div className={cx("rounded-lg p-2", tones[tone])}>
            <Icon size={16} />
          </div>
        )}
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}

export function PageHeader({ title, description, actions, children }) {
  return (
    <div className="mb-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
          {description && <p className="mt-1 text-sm text-slate-500 max-w-2xl">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1 mb-5" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={cx(
            "whitespace-nowrap rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors cursor-pointer",
            active === tab.id ? "bg-white text-violet-700 shadow-sm" : "text-slate-600 hover:text-slate-900",
          )}
        >
          {tab.label}
          {tab.count !== undefined && <span className="ml-1.5 text-xs text-slate-400">{tab.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Modal({ open, title, onClose, children, footer, wide }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px]" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-label={title}
        className={cx("relative w-full rounded-2xl bg-white shadow-xl max-h-[90vh] flex flex-col", wide ? "max-w-3xl" : "max-w-lg")}>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 cursor-pointer" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4 overflow-y-auto">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export const inputClass =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-100 transition";

/** Same look as inputClass but sized to its content (for inline selects). */
export const inlineInputClass = inputClass.replace("w-full", "w-auto");

export function Field({ label, hint, children, required }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-slate-700">
        {label} {required && <span className="text-red-500">*</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function KeyValue({ items }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {items.map(([key, value]) => (
        <div key={key} className="min-w-0">
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">{key}</dt>
          <dd className="mt-0.5 text-sm text-slate-800 break-words">{value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Table({ columns, rows, empty = "No data", rowKey }) {
  if (!rows?.length) return <p className="px-5 py-8 text-center text-sm text-slate-500">{empty}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
            {columns.map((column) => (
              <th key={column.key} className={cx("px-5 py-2.5 font-medium", column.className)}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, index) => (
            <tr key={rowKey ? rowKey(row) : index} className="hover:bg-slate-50/60">
              {columns.map((column) => (
                <td key={column.key} className={cx("px-5 py-3 align-top text-slate-700", column.className)}>
                  {column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BulletList({ items, empty = "None recorded." }) {
  if (!items?.length) return <p className="text-sm text-slate-400">{empty}</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((item, index) => (
        <li key={index} className="flex gap-2 text-sm text-slate-700">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-400" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
