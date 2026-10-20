import type { Severity, Status } from "./types";

export const severityNames: Record<Severity, string> = {
  low: "Low", medium: "Medium", high: "High", critical: "Critical",
};

export const statusNames: Record<Status, string> = {
  open: "Open", acknowledged: "Acknowledged", resolved: "Resolved",
};

export function timeAgo(value: string, now = Date.now()): string {
  const seconds = Math.max(0, Math.floor((now - new Date(value).getTime()) / 1000));
  if (!Number.isFinite(seconds)) return "Unknown";
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit", timeZoneName: "short",
  });
}
