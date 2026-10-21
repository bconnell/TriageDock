export type Severity = "low" | "medium" | "high" | "critical";
export type Status = "open" | "acknowledged" | "resolved";

export interface Incident {
  id: string;
  source: string;
  external_key: string;
  title: string;
  description: string;
  severity: Severity;
  status: Status;
  occurrences: number;
  first_seen_at: string;
  last_seen_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface IncidentEvent {
  id: number;
  kind: string;
  actor: string;
  created_at: string;
}

export interface Delivery {
  id: number;
  event_kind: string;
  status: "pending" | "sent" | "failed";
  attempts: number;
  last_error: string;
  sent_at: string | null;
}

export interface IncidentDetail extends Incident {
  events: IncidentEvent[];
  events_has_more: boolean;
  deliveries: Delivery[];
}

export interface IncidentPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: Incident[];
}

export interface Stats {
  total: number;
  open: number;
  acknowledged: number;
  resolved: number;
  critical_active: number;
}

export interface Session {
  authenticated: boolean;
  username: string | null;
}
