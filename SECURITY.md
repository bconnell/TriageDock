# Security

TriageDock's Docker Compose setup binds the web server to `127.0.0.1`. It is intended for local use and evaluation, not exposure to the public internet.

If you discover a security issue, use GitHub's **Report a vulnerability** option for this repository if private reporting is enabled. If it is unavailable, open a general issue asking the maintainer for a private contact method. Do not post exploit details, access tokens, real incidents, or personal information in a public issue.

## Deployment boundaries

- Set unique secrets in a local `.env`; never commit it.
- External deployments require HTTPS, secure cookies, approved hosts and trusted origins, edge rate limiting, database backup/restore, and a dedicated secret manager.
- Readers can inspect incidents; only users granted `incidents.change_incident` can acknowledge or resolve. There is no per-incident authorization or multi-tenant isolation.
- The alert API uses a bearer-style API key in `X-TriageDock-Key`. It is **not** a cryptographic signature. A Redis-backed application throttle provides bounded abuse protection, not network-edge DDoS protection. Source-scoped keys can be revoked, and the legacy shared key can be disabled with `INGEST_SHARED_KEY_ENABLED=0`.
- Outgoing HTTPS webhooks are optional. Delivery is best effort with bounded retries and possible duplicates; receivers must deduplicate `event_id`.
- The `/health/` endpoint is a liveness response, not proof of database, Redis, or worker health.

## Dependency maintenance

The committed npm and Python locks fix dependency resolution for reviewed builds. Dependabot submits updates; update both the direct input and the corresponding lock before merging. CI rejects install errors and audits available vulnerability advisories. An audit result is a point-in-time check, not an assurance that no vulnerabilities exist.

## Evidence boundaries

Production deploys must use a managed TLS proxy, safe forwarded-header handling, TLS-only secure cookies, HSTS after HTTPS validation, strong unique secrets, and per-service network isolation. A configured outbound HTTPS host must not be internal; redirected webhook destinations are rejected. DNS rebinding and unrestricted destination hostnames remain risks unless outbound egress is restricted by the deployment.

Admin pages do not permit editing or deleting stored incident events. That is **not** cryptographic tamper-evidence against database owners or superusers with shell/database access. Use database privileges, independent logs, and approved retention before relying on audit history for compliance.

Backups are ignored by Git and generated under `backups/` only. Operators must secure them, test restoration into an isolated database, and manage their retention. No unverified availability, disaster recovery, or production safety certification is claimed.
