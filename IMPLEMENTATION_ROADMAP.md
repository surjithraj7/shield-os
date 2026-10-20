# Implementation Roadmap

Ordered by risk reduction. Each phase has measurable exit criteria. This is an
engineering roadmap, not a claim that the platform is currently production-ready.

## Phase 0 - Completed in this work

- [x] Audit existing backend, frontend, data model, and test baseline.
- [x] Add IoT sensor registry, validated ingestion, dedupe, out-of-order flags,
      health states, demo seeding, and simulator.
- [x] Add explainable threshold + statistical risk engine with environment
      overrides.
- [x] Add persisted alert lifecycle with dedupe, escalation, acknowledge/resolve,
      SQL summary counts, and audit records.
- [x] Add ingestion API key, login/ingest/write rate limits, restricted CORS,
      security headers, and safe 500 responses.
- [x] Integrate IoT window and live alert log in the React frontend.
- [x] Add IoT/risk/alerts sections to regulatory reporting with simulated-data
      labelling and non-certification wording.
- [x] Add 24 automated tests; full suite 106 passed; frontend build passed.
- [x] Produce status, inventory, roadmap, test, and limitations documents.

## Phase 1 - Deployment safety (highest priority)

1. **Credentials and secrets**
   - [x] Production startup no longer creates `admin/admin123` or
     `operator/shield123`; bootstrap requires `SHIELD_ADMIN_PASSWORD`.
   - [ ] Add forced first-login password change.
   - [ ] Add password reset and session revocation endpoints.
   - [x] Read production bootstrap secrets and provider keys from environment.
   - [ ] Move secrets to a managed secret store with rotation.
   - Exit criterion: no default credential can authenticate in staging/production.

2. **Database lifecycle**
   - Introduce Alembic migrations for all tables and seed actions.
   - Separate schema creation from demo seeding; gate demo data behind an
     explicit environment flag.
   - Exit criterion: repeated deploy/rollback against a copy of production data
     succeeds without data loss.

3. **Distributed controls**
   - Replace in-memory rate limiting with Redis (or equivalent) so limits hold
     across workers.
   - Add request IDs, structured logs, health/readiness probes, and metrics.
   - Exit criterion: two or more workers enforce one shared limit and expose
     metrics.

4. **Transport security**
   - Enforce HTTPS, HSTS, and trusted-proxy handling for `X-Forwarded-For`.
   - Define explicit production `CORS_ORIGINS`; fail closed when unset.
   - Exit criterion: security review with no high-severity findings.

## Phase 2 - Field data path

1. Define a gateway contract: device identity, certificates/keys, buffering,
   clock sync, sequence numbers, and replay protection.
2. Implement at least one real adapter (MQTT or OPC-UA) plus a simulated gateway
   that uses the same contract.
3. Add per-sensor calibration metadata and unit tests for each supported unit
   family.
4. Add a scheduled health monitor (Celery/RQ/APScheduler) that raises offline
   alerts without relying on a UI request.
5. Add retention/archival and export policies for readings, assessments, alerts,
   and audit logs.
6. Exit criteria: 72-hour soak test with reconnects, duplicate bursts,
   out-of-order packets, and sensor dropouts; no duplicate readings or alerts.

## Phase 3 - Engineering validation

1. Replace built-in thresholds with site-approved control limits and document the
   approval source for each sensor type.
2. Validate risk categories against labelled incidents and false-alarm rates;
   publish precision/recall by sensor type.
3. Add alert notification delivery (email/webhook/SMS) with escalation and
   acknowledgement SLAs.
4. Have a qualified tunnel engineer review recommendations and alarm wording.
5. Add report provenance: data window, sensor calibration, exclusions, and
   reviewer sign-off.
6. Exit criteria: signed site acceptance test and a reviewed alarm philosophy
   document.

## Phase 4 - Frontend and usability

1. Add browser end-to-end tests for login, IoT simulator, alert acknowledge, and
   resolve.
2. Replace remaining static/deterministic dashboard feeds with API-backed data or
   label them visibly as demonstrations.
3. Add pagination, filtering, and export to the alert log.
4. Add accessible keyboard navigation and screen-reader labels for windows,
   tables, and dialogs.
5. Code-split the 1.47 MB production bundle.
6. Exit criteria: E2E suite passes on desktop and mobile viewports; no unlabelled
   simulated metric remains on an operational screen.

## Phase 5 - Scale and operations

1. Evaluate PostgreSQL with connection pooling and backups.
2. Add multi-tenancy/project isolation if multiple tunnels or clients are needed.
3. Add role granularity (`viewer`, `engineer`, `operator`, `admin`) and audit-log
   review UI.
4. Add disaster recovery runbooks and restore drills.
5. Add capacity/load tests for ingestion and alert queries.

## Suggested backlog order

1. Remove demo credentials and gate demo seeding.
2. Alembic migrations.
3. Redis rate limiting and scheduled health checks.
4. Real gateway adapter and calibration.
5. Site-approved thresholds and engineer review.
6. Browser E2E tests and bundle splitting.
