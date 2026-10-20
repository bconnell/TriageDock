# Security

TriageDock's Docker Compose setup binds the web server to `127.0.0.1`. It is intended for local use and evaluation, not exposure to the public internet.

If you discover a security issue, use GitHub's **Report a vulnerability** option for this repository if private reporting is enabled. If it is unavailable, open a general issue asking the maintainer for a private contact method. Do not post exploit details, access tokens, real incidents, or personal information in a public issue.

## Deployment boundaries

- Set unique secrets in a local `.env`; never commit it.
- External deployments require HTTPS, secure cookies, approved hosts and trusted origins, edge rate limiting, database backup/restore, and a dedicated secret manager.
- All authenticated Django users are operators. There is no per-incident authorization or multi-tenant isolation.
- The alert API uses a bearer-style API key in `X-TriageDock-Key`. It is **not** a cryptographic signature, and it does not include built-in rate limiting.
- Outgoing HTTPS webhooks are optional. Delivery is best effort with bounded retries and possible duplicates; receivers must deduplicate `event_id`.
- The `/health/` endpoint is a liveness response, not proof of database, Redis, or worker health.

## Dependency maintenance

The committed npm and Python locks fix dependency resolution for reviewed builds. Dependabot submits updates; update both the direct input and the corresponding lock before merging. CI rejects install errors and audits available vulnerability advisories. An audit result is a point-in-time check, not an assurance that no vulnerabilities exist.
