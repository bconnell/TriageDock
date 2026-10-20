# API contract (v1)

Incident listing, details, counts, and status changes require an authenticated Django session. Login and logout use the browser session flow; POST requests using that session require a valid CSRF token. The session status route can be called before login. Alert intake uses an independent `X-TriageDock-Key` header and does not require a Django session.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/v1/session/` | Current session and CSRF cookie |
| POST | `/api/v1/login/` | Session login (`username`, `password` JSON) |
| POST | `/api/v1/logout/` | End session |
| POST | `/api/v1/alerts/` | Ingest alert using `X-TriageDock-Key` header |
| GET | `/api/v1/incidents/` | Paginated incidents; `status`, `severity`, `q`, `page` filters |
| GET | `/api/v1/incidents/stats/` | Summary counts |
| GET | `/api/v1/incidents/{uuid}/` | Incident, history, deliveries |
| POST | `/api/v1/incidents/{uuid}/acknowledge/` | Acknowledge |
| POST | `/api/v1/incidents/{uuid}/resolve/` | Resolve |
| GET | `/health/` | Liveness, not dependency readiness |

Webhook body:
```json
{
  "source": "gateway-1",
  "external_key": "latency-p99",
  "title": "P99 latency too high",
  "description": "Latency exceeded threshold for 5 minutes",
  "severity": "critical"
}
```

`source` (80 chars), `external_key` (160), `title` (200), `severity` (low/medium/high/critical) required. `description` optional, max 4000. Identity is SHA256 of length-prefixed source and external key. These strings are case-sensitive; callers must keep them stable. Further alerts with the same identity return HTTP 200 and increment occurrences, even when their titles, severities, or descriptions change. The first alert for a new identity returns HTTP 201. Repeating resolved identities reopens them. Missing/wrong intake key yields 401. Invalid payloads yield 400. Alert intake authenticates callers with an API key, not a cryptographic payload signature. This is a loopback-only development deployment. Before allowing external traffic, configure TLS and appropriate edge rate limits.

Delivery payload (only when `NOTIFICATION_WEBHOOK_URL` is configured):
```json
{
  "event_id": 1,
  "kind": "created",
  "incident_id": "uuid",
  "title": "P99 latency too high",
  "severity": "critical",
  "status": "open"
}
```
Consumers **must deduplicate by `event_id`**. A worker can successfully deliver a notification and crash before the database commits its success, resulting in a repeated HTTP delivery. The `status` value reflects the incident when the worker sends the request, which may be different from the status when the event was recorded.
