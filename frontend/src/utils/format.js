// Formatting helpers shared by every page.

/** Backend timestamps from SQLite may lack a timezone; they are always UTC. */
export function parseDate(value) {
  if (!value) return null;
  const text = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value) {
  const date = parseDate(value);
  return date ? date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";
}

export function formatTime(value) {
  const date = parseDate(value);
  return date ? date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—";
}

export function timeAgo(value) {
  const date = parseDate(value);
  if (!date) return "—";
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${Math.max(seconds, 0)}s ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86400)}d ago`;
}

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function formatPercent(ratio) {
  if (ratio === null || ratio === undefined) return "—";
  return `${(ratio * 100).toFixed(ratio === 1 || ratio === 0 ? 0 : 1)}%`;
}

export function formatNumber(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat().format(value);
}

export function humanize(value) {
  if (!value) return "";
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export const CHECKPOINT_LABELS = {
  requirements: "Requirements",
  architecture: "Architecture",
  code: "Code changes",
  test_execution: "Test execution",
  deployment: "Final delivery",
};

export const CHECKPOINT_PAGES = {
  requirements: "/requirements",
  architecture: "/architecture",
  code: "/code",
  test_execution: "/testing",
  deployment: "/testing",
};

export const ACTIVE_STATUSES = ["pending", "running", "waiting_approval"];

/** Short summary of an agent's structured output for cards. */
export function summarizeOutput(output) {
  if (!output || typeof output !== "object") return [];
  return Object.entries(output)
    .filter(([, value]) => value !== null && value !== "")
    .slice(0, 8)
    .map(([key, value]) => {
      let text;
      if (Array.isArray(value)) text = `${value.length} item${value.length === 1 ? "" : "s"}`;
      else if (typeof value === "object") text = `${Object.keys(value).length} fields`;
      else text = String(value).length > 70 ? `${String(value).slice(0, 70)}…` : String(value);
      return { key: humanize(key), text };
    });
}
