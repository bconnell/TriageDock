# API contract (v1)

The default branch is a hardening candidate beyond tagged v1.0.0; verify your local build before use.


Incident listing, details, counts, and status changes require an authenticated Django session. Login and logout use the browser session flow; POST requests using that session require a valid CSRF token. The session status route can be called before login. Alert intake uses an independent `X-TriageDock-Key` header and does not require a Django session.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/v1/session/` | Current session and CSRF cookie |
| POST | `/api/v1/login/` | Session login (`username`, `password` JSON) |
| POST | `/api/v1/logout/` | End session |
| POST | `/api/v1/alerts/` | Ingest alert using `X-TriageDock-Key` header |
| GET | `/api/v1/incidents/` | Paginated incidents; `status`, `severity`, `q`, `page` filters |
| GET | `/api/v1/incidents/stats/` | Summary counts |
| GET | `/api/v1/incidents/{uuid}/` | Incident, most recent 50 history events, more-history flag, deliveries |
| GET | `/api/v1/incidents/{uuid}/events/?page=1` | Full audit history, paged in groups of 50 |
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

`source` (80 chars), `external_key` (160), `title` (200), `severity` (low/medium/high/critical) required. `description` optional, max 4000. Identity is SHA256 of length-prefixed source and external key. These strings are case-sensitive; callers must keep them stable. Further alerts with the same identity return HTTP 200 and increment occurrences, even when their titles, severities, or descriptions change. The first alert for a new identity returns HTTP 201. Repeating resolved identities reopens them. Missing/wrong intake key yields 401. Invalid payloads yield 400. Alert intake authenticates callers with either the configured shared key or a source-scoped credential, not a cryptographic payload signature. Source-scoped credentials must match the request's `source`; revoked credentials return HTTP 401. Set `INGEST_SHARED_KEY_ENABLED=0` after migrating all senders to scoped keys. The API rate limit is 60 requests per minute per remote address regardless of submitted key, with an additional edge limit needed if externally reachable. This is a loopback-only development deployment. Before allowing external traffic, configure TLS and appropriate edge rate limits.

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
Consumers **must deduplicate by `event_id`**. A worker can successfully deliver a notification and crash before the database commits its success, resulting in a repeated HTTP delivery. The `status`, `severity`, and `title` values are snapshotted when the event is recorded. The incident may have changed by the time the worker sends the request.

### Operator authorization and abuse handling

All signed-in users can read incidents; status mutation requires `incidents.change_incident` (superusers qualify). Unsupported state changes return HTTP 409; insufficient permission returns HTTP 403. Repeated failed sign-in attempts are temporarily blocked (HTTP 429, `Retry-After`). Rate limits are defense in depth, not guaranteed distributed denial-of-service protection. Redis must be healthy for shared rate-limiter state.

### Status and consistency

Repeated alerts increase occurrence counts and preserve the highest severity while an incident remains active. A newly received alert for a resolved incident starts a new open cycle with the incoming severity. The `/health/` response is liveness only. `/ready/` reports PostgreSQL, Redis cache and a recently observed Celery worker heartbeat; it returns HTTP 503 if any check fails.

The detail response carries no more than the 50 most recent events, with `events_has_more`. Notification deliveries are also capped at 50 per detail response, with `deliveries_has_more`. For complete immutable API-managed history use the paginated events route. Django Admin is read-only for incidents, history and delivery records. A database owner with direct SQL access can still change data; database-level tamper-proof audit storage is outside this application.
