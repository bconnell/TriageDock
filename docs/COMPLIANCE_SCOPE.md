# Privacy and compliance applicability review

This is a **scope assessment**, not a legal opinion or compliance certification.
TriageDock currently ships as a loopback-only local evaluation application. It
does not include public registration, tenant separation or internet-facing
deployment instructions.

| Category | Current source observation | Required before broader deployment |
| --- | --- | --- |
| Personal data and privacy requests | An authorized monitor can submit arbitrary alert titles, keys and descriptions. Operators can read them. No automatic data-subject request workflow is implemented. | Decide data classification, retention, access/deletion/export procedures, incident-response owner, and applicable notice/rights obligations. |
| Children and COPPA | No child-focused experience, age registration or user profiles were found in the inspected UI/API. Alert text could still carry third-party personal information. | Prevent child data collection where not intended; review actual audience, data flows and applicable laws before accepting public traffic. |
| External fonts, analytics and tracking | The inspected `frontend/index.html` and `frontend/src/styles.css` use local application assets/system font fallbacks; no remote font URL appears there. The inspected API client uses same-origin requests. | Inventory any newly added third-party scripts, cookies or processors; update disclosures/consent where legally required. |
| Session replay, interception and consent | The inspected application code does not implement session-replay capture. Django sessions and CSRF protections are in use. | Review any newly integrated observability/session tools for interception, consent, retention, processor contracts and security. |
| Marketing, CAN-SPAM, electronic communications | There is no newsletter, email marketing or direct-message campaign feature in the current incident interface. Optional outbound HTTPS webhooks are machine notifications. | Apply relevant marketing consent, identification, unsubscribe and recordkeeping rules if messaging features are added. |
| Subscriptions, renewal, billing and consumer claims | No checkout or recurring subscription system exists in the current application. | Establish truthful pricing, renewal disclosure, cancellation, refunds, taxes and consumer protections before monetization. |
| User uploads, copyright and DMCA | No public user-media upload or hosting feature was identified. Alert text is stored, and project dependencies/icons have their own license terms. | Review redistribution notices and IP provenance; create complaint/notice handling and designated agent procedures if user-hosted content is introduced and applicable. |
| Sensitive incident history and backup recovery | Incident records and backups can contain operational secrets or incidental personal data. Django Admin does not allow editing incident history, but a database owner can still modify rows. No encryption-at-rest or retention enforcement is promised. | Restrict database and backup access, set appropriate retention, independently test restoration, consider encryption and separate tamper-evident audit storage where needed. |

## Operating controls

- Never commit `.env`, actual alerts, backup archives or personally identifying
  records. The repository ignores `backups/`, local environments and transcripts.
- Keep all new dependencies and visual assets subject to license and
  origin review before distributing a build.
- Do not represent the application as HIPAA-ready, SOC 2 certified,
  GDPR-compliant, COPPA-certified, PCI-compliant, or production-ready without
  independent, applicable assessment and evidence.
- The current deployment is not configured for public internet exposure;
  network-edge rate limiting, trusted TLS, stronger operational monitoring,
  backup security and access policies remain external responsibilities.
- Human oversight is necessary for real notices, deadlines and legally
  required registrations. Automation does not replace legally responsible staff.

Each category must be reassessed whenever new features, deployments, target
audiences or third-party services change. This document describes source
observations and missing policies rather than claiming a passed legal audit.
