# Known Limitations

This platform is an engineering demonstrator. The following limitations are
explicit and must be addressed before operational use.

## Safety and engineering

1. **Not a certified safety system.** Risk scores, alerts, recommendations, and
   reports are decision-support outputs. They require review by a qualified tunnel
   engineer and do not replace statutory monitoring or emergency procedures.
2. **Demo thresholds.** Built-in moderate/high/critical values in
   `app/risk_engine.py` are demonstrator defaults, not site-approved control
   limits. Use `RISK_THRESHOLDS_JSON` and documented engineering approval.
3. **Anomaly logic is statistical.** Z-scores assume a roughly stable recent
   history; constant-baseline step changes are handled separately. Seasonal,
   sensor-drift, and multi-sensor correlation effects are not modelled.
4. **No calibration workflow.** Per-sensor calibration, zero offsets, and
   uncertainty budgets are not implemented.
5. **No real hardware path.** There is no MQTT/Modbus/OPC-UA gateway, device
   certificate provisioning, buffering, or clock-sync handling. Ingestion is HTTP
   with a client-asserted source field.
6. **Offline alerts are request-triggered.** Without a background scheduler, no
   offline alert is raised until `/api/iot/health/check` is called.
7. **No alert auto-resolution.** A resolved alert stays resolved; recurring
   out-of-threshold readings create a new active alert only after resolution.
8. **Notification gap.** Alerts are visible only in-app (10 s polling). There is
   no SMS, email, webhook, pager, or push integration.
9. **Simulated data.** The seeded fleet and simulator are labelled
   `source="simulated"`. They must not be presented as field measurements.
10. **Static/deterministic UI elements.** Several TBM, 3D, CCTV, AR, GIS, and
    dashboard visuals are demonstrations with static or generated feeds. They are
    not all connected to live plant telemetry.

## Data and persistence

11. **SQLite only by default.** Suitable for single-instance demos; no
    high-availability, replication, or concurrent-writer guarantees.
12. **No migrations.** Tables are created with SQLAlchemy `create_all`; schema
    changes require manual handling. Alembic is not configured.
13. **Demo seeding on startup.** `seed_demo_iot` runs during lifespan when no
    sensors exist. It does not overwrite existing sensors but is not gated by an
    explicit production flag.
14. **No retention policy.** Readings, assessments, alerts, and audit logs grow
    without archival, deletion, or export controls.
15. **No pagination on some lists.** Endpoints use bounded `limit` values but do
    not expose cursor pagination.
16. **Unit coverage is limited.** Length and pressure conversions are supported;
    other unit families require exact canonical units.
17. **Out-of-order data is flagged, not reordered.** Downstream consumers must
    handle flagged readings.
18. **Audit log is append-only in code but has no tamper-evident signing or
    external retention.**

## Security

19. **Development demo credentials.** Non-production startup still seeds
    `admin/admin123` and `operator/shield123` for local testing. Production
    refuses to create them and requires `SHIELD_ADMIN_PASSWORD`; there is no
    forced first-login password change, so rotate bootstrap secrets operationally.
20. **No password change/reset, MFA, or account lockout.**
21. **Single static ingestion key.** `IOT_INGEST_API_KEY` has no rotation,
    per-device identity, revocation list, or replay protection beyond `event_id`.
22. **Rate limiting is in-process.** Limits reset on restart and are not shared
    across workers or instances.
23. **Trusted proxy handling.** `X-Forwarded-For` is trusted when present; deploy
    behind a proxy that overwrites the header.
24. **CORS is environment-configured.** Production defaults to same-origin plus
    `RENDER_EXTERNAL_URL`; add `CORS_ORIGINS` only for a custom or separate
    frontend origin.
25. **No TLS termination in the app.** Run behind a TLS-terminating proxy; HSTS is
    not set by the application.
26. **AI endpoints are rate-limited but unauthenticated.** Callers can consume
    provider credits even though assistant endpoints are limited to 30 requests
    per minute per client.
27. **AI provider keys and prompts** are handled by existing provider modules;
    live-provider data handling, retention, and regional compliance are not
    validated here.
27. **Google Maps API key** is a frontend build-time value and is visible to
    browser clients; restrict it by origin and API in Google Cloud.

## Deployment

28. **No Render deployment or public URL has been verified.** No Render
    credentials or CLI are available in this environment.
29. **No Docker image build was run locally.** Docker/Podman is not installed;
    the Dockerfile and Render Blueprint were inspected and schema-validated, and
    the production start command was exercised directly with Uvicorn.
30. **SQLite remains a single-instance datastore.** A Render persistent disk
    preserves it across restarts, but there is no HA, migration framework, or
    automated restore drill.

## Testing and operations

31. **No frontend automated tests or browser E2E.** The production build is
    verified, not runtime behavior.
32. **No load, soak, or chaos testing.**
33. **No coverage gate.**
34. **External AI calls are mocked/optional in tests.** Provider quality and
    latency are not measured.
35. **No multi-tenancy or project isolation.** All data shares one database.
36. **Accessibility and mobile behavior** are not systematically tested.
37. **Single-process assumptions** for in-memory rate limiting, scheduler-free
    health checks, and local SQLite.
38. **Reports aggregate data without reviewer sign-off fields, exclusion lists,
    or full data-window provenance.**
