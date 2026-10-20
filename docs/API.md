# API contract (v1)

All operator routes are cookie-session authenticated and require CSRF on mutations.

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

`source` (80 chars), `external_key` (160), `title` (200), `severity` (low/medium/high/critical) required. `description` optional, max 4000. Identity is SHA256 of length-prefixed source and external key. These strings are case-sensitive; callers must keep them stable. Identical identities yield HTTP 200 and increment occurrences. First occurrence yields 201. Repeating resolved identities reopens them. Missing/wrong intake key yields 401. Invalid payloads yield 400. No incoming webhooks require a user session, but never expose the endpoint without TLS, authentication and edge rate limiting.

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
Consumers **must deduplicate by `event_id`**: after network success, a worker crash before database commit can lead to duplicate HTTP delivery.
