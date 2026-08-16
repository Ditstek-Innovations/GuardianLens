# Guardian Lens — Running the System, End to End

**How to run every part of Guardian Lens, and what happens at each step of the workflow — from a detection on a site to a verified record in a report**

| Field | Value |
|---|---|
| Document | Runbook / workflow description (Diátaxis: **how-to** + **explanation** — per [GOVERNANCE.md](GOVERNANCE.md) §19.2 these are kept distinct from reference; the reference documents are linked, not restated) |
| Version | 1.1 |
| Date | 12 August 2026 |
| Owner | Kapil (Engineering) |
| Status | Development / pilot form. Production deployment is [TRD.md](TRD.md) §20.3 `[V1]` |
| Companions | [TRD.md](TRD.md) §20.2 (deployment sequence this implements) · [ARCHITECTURE.md](ARCHITECTURE.md) (structure) · [DATABASE.md](DATABASE.md) (data) · [BACKEND_CODING_RULES.md](BACKEND_CODING_RULES.md) · [FRONTEND_CODING_STANDARDS.md](FRONTEND_CODING_STANDARDS.md) |

> **Status warning, carried from every companion document.** Gate **G0** has not been passed and 25 of 45 rules in [RULE_BOOK.md](RULE_BOOK.md) are `PROPOSED`. What runs here is the development form of TRD §20.2 **steps 1–4**: the workflow is real, the detector is synthetic ("the MVP tests the workflow, not the detector" — TRD §13.2). **No customer-site deployment may happen from this document.**

---

## 1. One command

```bash
make run
```

That is the whole thing. It brings up, in order, each through the production code path:

| Step | What happens | Where specified |
|---|---|---|
| 1 | PostgreSQL 16 in Docker, waits for healthy | [TRD.md](TRD.md) §13.2 |
| 2 | Control schema migrated (`c0001`) | [DATABASE.md](DATABASE.md) Appendix B.2 |
| 3 | Demo tenant `pilot` provisioned: create → migrate → identity → seed → **FF-11 attestation** → `active`. A tenant that fails attestation never serves | [DATABASE.md](DATABASE.md) §13.5.1 |
| 4 | First admin bootstrapped (`admin@guardianlens.local`), first site created, `site_admin` granted — idempotent on re-run | TRD §20.2 note: steps 1–3 need no camera and no model |
| 5 | **API on http://localhost:8000** and **review UI on http://localhost:5173**, both in the foreground; Ctrl-C stops both | — |

Login: `admin@guardianlens.local` / `guardian-dev-1` (override with `GL_BOOTSTRAP_PASSWORD`).

Then, in a second terminal, feed it events from a simulated site:

```bash
make edge-demo
```

This ensures a camera, zone and **explicitly activated** rule exist (activation names the acting user — BR-C-02), registers an edge agent principal, and runs the real edge agent against the live API with a two-frame scenario. One candidate event lands in the review queue. Open http://localhost:5173, press **A** to accept it (or **R** with a reason, **C** to correct), and watch it appear in Reports as a verified record — with the reviewer's name permanently attached.

## 2. Every command, individually

| Command | Does |
|---|---|
| `make run` | Everything above, one process group |
| `make edge-demo` | Simulated site → real events into the running stack |
| `make api` | Control plane only (uvicorn on :8000) |
| `make web` | Review UI only (Vite on :5173) |
| `make up` / `make down` | Just the database / stop everything and delete the volume |
| `make migrate-control` | Control schema to head |
| `make provision TENANT=acme` | Provision a tenant (code path only — never by hand) |
| `make onboard TENANT=… ADMIN_EMAIL=… ADMIN_NAME=… SITE_NAME=… TZ=…` | Going real (§3b): fresh attested tenant + first admin, no demo data |
| `make attest TENANT=<url>` | FF-11: verify every constraint and trigger is present and enabled |
| `make bypass` | The business-rule bypass suite (TRD §19.4) |
| `make e2e` | The full-workflow test (§5 below) |
| `make test` / `make coverage` / `make unit` / `make lint` | Full suite / with coverage / no-database tests / bandit |

Environment (`.env.example` → `.env`, never committed — TRD §12.5):

```bash
GL_CONTROL_DB_URL=postgresql+psycopg://guardian:guardian@localhost:5432/gl_control
GL_TENANT_DB_URL=postgresql+psycopg://guardian:guardian@localhost:5432/gl_tenant_pilot
GL_JWT_SECRET=<32+ bytes>          # HS256 dev signing; RS256 is the V1 target
GL_BOOTSTRAP_PASSWORD=<first-login password for bootstrap>
GL_EVIDENCE_ROOT=./var/evidence    # filesystem evidence store [MVP]
GL_AGENT_CREDENTIAL=slug:agent_id:secret   # edge agent only
```

## 3. The workflow, step by step

What actually happens between a condition on the shop floor and a line in a report. Numbers refer to the runtime scenarios in [ARCHITECTURE.md](ARCHITECTURE.md) §6.

```mermaid
sequenceDiagram
    autonumber
    participant CAM as Camera / scenario
    participant EDGE as Edge Agent (site)
    participant API as Control Plane API
    participant DB as Tenant Database
    participant UI as Review UI
    participant REV as Reviewer (human)

    Note over EDGE: pulls config; only rules a named<br/>user activated exist (BR-001)
    CAM->>EDGE: frame
    EDGE->>EDGE: detect → threshold → zone → dwell → debounce<br/>(deterministic D1 — every discard is COUNTED)
    EDGE->>EDGE: build candidate: rule_snapshot at detection time,<br/>UUIDv7 event_id, evidence frame → SQLite outbox
    EDGE->>API: POST /events (agent token; at-least-once)
    API->>DB: INSERT status='unverified'<br/>(CHECK constraints make any other status impossible)
    API-->>EDGE: 201 (or 200 duplicate — success)
    UI->>API: GET /events (cursor-paginated queue)
    REV->>UI: opens candidate — decision buttons stay DISABLED<br/>until the evidence frame has loaded
    REV->>UI: A / R+reason / C
    UI->>API: POST /events/{id}/decision {decision, version}
    API->>DB: ONE transaction: decision + audit entry<br/>(audit fails → decision rolls back, BR-AU-03)
    Note over DB: reviewer_id from the token only;<br/>immutable once written (trigger)
    UI->>API: GET /reports/summary
    API-->>UI: verified_events_only + coverage gaps<br/>+ rejection counts (BR-R-01/02/03)
```

The properties that hold at every step — and where each is proven:

| Property | Enforced by | Proven by |
|---|---|---|
| Nothing is monitored by default | `is_active DEFAULT FALSE`; agent has no rules until pull | FF-8 clean instance; E2E asserts `is_active: false` on creation |
| The safety path after detection is deterministic | MOD-3 is pure code; no inference below IF-E2 | 27 rule-evaluator unit tests (boundary cases per TRD §19.2) |
| No record without a human | Edge can only emit `unverified`; ingest rejects `status`; only the decision route transitions; **CHECK constraint** | Bypass suite DB-1/DB-2 (direct SQL); E2E |
| Every record carries its reviewer | Identity from the token; NOT NULL + CHECK; immutable by trigger | DB-3/DB-4/DB-5; E2E asserts the reviewer's name on the record |
| A decision that cannot be audited does not exist | Decision + audit in one transaction | Integration test with a failing audit write → rollback |
| Reports draw only from verified records | Repository-level filter, partial index | FF-7; E2E report assertions |
| Tenants cannot see each other | One database per tenant; `tenant_identity` asserted per connection | DB-21…DB-27; FF-11 attestation, continuously |
| An outage loses nothing and duplicates nothing | SQLite outbox, oldest-first drain, idempotent `event_id` | 14 publisher tests; E2E drains to zero |

## 3a. Connecting a camera — TRD §20.2 step 5

Step 5 verifies **stream reliability under real conditions** — connection,
sampling, reconnects, honest gaps. It deliberately proves nothing about
detection: a real model reaches a site only through gate **G1**
([GOVERNANCE.md](GOVERNANCE.md) §9), and until then RTSP mode runs a
`NullDetector` (frames counted, nothing detected).

First camera, or explaining the why to someone new? Read
[CAMERA_ONBOARDING.md](CAMERA_ONBOARDING.md) — the orientation walkthrough
from unboxing to the first verified record. Performing the integration?
[CAMERA_INTEGRATION.md](CAMERA_INTEGRATION.md) is the technical runbook —
phases, preconditions, API-level sequence, acceptance checks. This section
stays the authoritative command reference.

| Step | Command / action |
|---|---|
| 1 | `make run` — on first run it generates `GL_CAMERA_KEY` into `.env`. The same key must be present wherever the edge agent runs: the control plane **seals** camera credentials with it and cannot read them back; the edge **unseals** them in memory only |
| 2 | No physical camera? `make camera-sim` — a synthetic RTSP test pattern at `rtsp://localhost:8554/cam1` ([TRD.md](TRD.md) §13.2). Stream-loss testing = `docker stop gl-rtsp-feed` |
| 3 | In the UI (site_admin): Administration → Configuration → **Cameras** → register the camera with its RTSP URL (`rtsp://user:pass@host/stream`). Registration is a confirmed submit (CS-AD-03); the credential is sealed on save and never returned by any API |
| 4 | Same screen, **Edge agents** → register the agent at its site (confirmed submit). The one-time composite credential (`slug:agent_id:secret`) is shown exactly once — copy it to the device now; the server stores only its Argon2 hash. The agent's id for step 6 is in the list below the form |
| 5 | **Zones** → create the zone on the camera (full-frame at MVP; polygon drawing is a refinement) — confirmed submit. **Detection rules** → create the rule (created inactive, always — BR-001), then **Activate** it — activation is its own confirmed, attributed act (BR-C-02) |
| 6 | Run the edge agent in live mode. Secrets come from the environment, never argv: `GL_AGENT_CREDENTIAL` (the step-4 credential), `GL_CAMERA_KEY`, `GL_CAMERA_KEY_ID`. Then: `python -m guardian_lens_edge --source rtsp --api http://localhost:8000 --agent-id <uuid> --site <uuid> --outbox-warning-bytes … --outbox-critical-bytes … --failure-window … --degraded-failure-rate … --halt-failure-rate … --decode-failure-threshold …` — the threshold flags are `[OPEN]` product values (OQ-4 / MOD-1), so they are **required with no defaults**; state them per deployment. The agent pulls config, unseals stream URLs in memory only, samples at each camera's `sample_rate_fps`, reconnects with 1→60 s backoff, and records a `stream_lost` coverage gap on any interruption — including a camera that never connects |
| 7 | Verify honesty before trusting anything else: kill the stream and watch the gap open in Reports; restore it and watch the gap close. "We were not watching" must be visible — that is the property this step exists to prove |

**Not answered by step 5, by design:** cameras per device (`[OPEN — OQ-9]`,
benchmark on target hardware); detection accuracy (gate G1, labelled site
footage). The `edge-camera` dependency extra (`pip install -e ".[edge-camera]"`)
carries OpenCV and is needed only where real streams are decoded.

## 3b. Going real — a clean tenant, no demo data

The `pilot` tenant is the development sandbox: `make run` bootstraps a dev
admin into it and `make edge-demo` seeds synthetic configuration and events
there. **A real site never shares a database with any of that** — isolation
is physical (ADR-016), so "no mock data" is a provisioning decision, not a
cleanup job. Every row in a real tenant exists because a person or a real
camera put it there.

| Step | Command / action |
|---|---|
| 1 | `make onboard TENANT=<slug> ADMIN_EMAIL=<email> ADMIN_NAME='<Full Name>' SITE_NAME='<Plant name>' TZ=<Area/City>` — provisions a fresh tenant database through the production code path (create → migrate → seed reference data → **FF-11 attest** → activate) and bootstraps the first admin with the real site. `GL_BOOTSTRAP_PASSWORD` must be exported; the admin changes it after first sign-in |
| 2 | Sign in as that admin at the review UI. The tenant is empty except the bootstrapped site — no demo camera, no synthetic events, no `demo-edge` agent |
| 3 | Follow §3a steps 2–7 with the real hardware: register the real cameras (name, location, RTSP URL), register the real edge device, create zones and rules, activate explicitly, run the edge agent on the site box with the stated `[OPEN]` thresholds |
| 4 | **Never run `make edge-demo` against this tenant.** It prints a DEMO-DATA warning and targets `GL_DEMO_TENANT` (default `pilot`) — leave that default alone on machines that also touch real tenants |
| 5 | What the queue then holds is real: frames captured from the real stream, events created by activated rules, decisions carrying real reviewer names, coverage gaps recording real interruptions. Reports draw only from those verified records (BR-004/BR-005) |

Until gate G1 admits a model (card, datasheet, measured evaluation —
[GOVERNANCE.md](GOVERNANCE.md) §9), a real camera proves **stream honesty**,
not detection: frames flow, gaps are recorded, nothing is claimed. That is
the correct MVP posture, not a limitation to work around.

## 4. What exists, and what does not yet

| Plane | State | Where |
|---|---|---|
| Data layer — 2 schemas, 10+1 migrations, every constraint | ✅ | `migrations/` |
| Control plane — auth, tenancy router, ingest, review, decision, reports, config (incl. agent-principal and gate-G1 model-version registration), audit, health, the seven guards, bootstrap CLI | ✅ | `src/guardian_lens/` |
| Review UI — login, keyboard-first queue, evidence-gated decisions, reports with verified-only analysis (bar-by-dimension, decision mix, gaps), config incl. edge-agent registration with one-time credential reveal; CS-AD-03 confirmations on camera/agent registration and sign-out | ✅ | `web/` |
| Edge agent — deterministic pipeline, outbox, publisher, config sync, state machine, live multi-camera RTSP mode | ✅ | `src/guardian_lens_edge/` |
| **Real detector (ONNX)** | 🟡 `OnnxDetector` implemented (manifest + SHA-256 artefact verification before load, YOLO decode, NMS) but it refuses any unverified artefact — and no admitted artefact exists | Gate **G1** blocks any model reaching any site — a model card, datasheet and measured evaluation must exist first ([GOVERNANCE.md](GOVERNANCE.md) §9). RTSP mode runs `NullDetector` |
| **RTSP / live camera ingestion** | ✅ `--source rtsp`: threaded multi-camera capture, sealed-credential unsealing, reconnect with capped backoff, honest `stream_lost` / `stream_degraded` reporting | §3a above; verified live against `make camera-sim` (mediamtx + ffmpeg). Real-hardware scale is `[OPEN — OQ-9]` |
| Retention worker MOD-11, `/users`, `/retention` | ❌ `[V1]` | The `[MVP]` retention gap is recorded — [DATABASE.md](DATABASE.md) §9.5 |
| NVR connector MOD-5 | ❌ `[V1]`, `[OPEN — OQ-2]` | |

## 5. How this is tested

**386 automated checks** across six suites (`make test` runs them all; counts as of 2026-08-13, v1.2):

| Suite | Count | Proves |
|---|---|---|
| `tests/bypass/` | 43 | Every ABSOLUTE rule is unviolable **via direct SQL** — the suite that TRD §19.4 says must never fail |
| `tests/api/` | 126 | The API rows of the bypass suite, D2 ladder, atomic audit, cross-tenant/site isolation, token rotation, agent/model-version registration (one-time credential, G1 evidence gates) |
| `tests/edge/` | 163 | D1 boundary cases, outbox state machine, backpressure halts loudly, publisher retry/park ladder, RTSP capture (2 of these need `make camera-sim` and skip without it) |
| `tests/unit/` | 28 | URL handling, enforcement-registry invariants |
| `tests/integration/` + `tests/migrations/` | 24 | Audit atomicity, concurrent decisions, clean instance, query plans, reversibility, provisioning lifecycle |
| `tests/e2e/` | 2 | **The whole loop, through the real code path of all three planes at once** — provision → bootstrap → configure → activate → edge scenario → ingest → queue → evidence → decide → 409 on the second decision → verified-only report → audit trail |

Plus, per run: FF-11 attestation, bandit, `tsc --noEmit`, the web build, and 79 vitest UI tests across 15 files. CI ([.github/workflows/ci.yml](../.github/workflows/ci.yml)) runs everything and additionally **fails any pull request that modifies rule enforcement and the bypass suite together** (GOVERNANCE §8.2 as a build failure).

## 6. Contract decisions made during integration

Three planes were built in parallel from [TRD.md](TRD.md) §10; where §10 was silent, the integration pass settled the shape. These are now the de-facto contract and belong in a future TRD §10 amendment:

| Surface | Settled shape |
|---|---|
| `POST /api/v1/auth/agent` | `{"credential": "slug:agent_id:secret"}` → agent JWT. Slug is routing only; the secret is verified in-tenant. Not in TRD §10.2 — new |
| `GET /api/v1/agents/{id}/config` | `{config_version, site:{id,name,timezone}, cameras:[{id,…,stream_url_sealed}], zones:[…], rules:[…]}`. **Only active rules ship, with no `is_active` field — the served set is the active set (BR-001).** The edge adapts at its boundary (`normalise_document`) |
| `POST /api/v1/coverage-gaps` | `{id, camera_id?, started_at, ended_at?, reason, detail?}` — `id` is the [DATABASE.md](DATABASE.md) §5.7 column name and the idempotency key |
| `POST /api/v1/agents/health` | `{sent_at, applied_config_version?, agent_version?}`, `extra="forbid"`. Richer edge state (halt reason, backlog) stays local until the contract grows fields for it |
| Decision 409 | §10.8 envelope with additive `error.existing_decision` |
| Reports summary | `from`/`to` query params; `decision_counts{accepted,corrected,rejected}`; `coverage_gaps_minutes` always present; `basis: "verified_events_only"` |
| Queue rows | Deliberately omit `rule_snapshot` (DATABASE.md §7.3); the detail endpoint carries it |
| `POST /auth/signup` · `/auth/password-reset-request` · `/auth/password-reset` | Self-service flows (CS-AU-10 v1.4): always-generic `202` acceptances (enumeration-safe, byte-identical bodies); signup gated by `GL_SIGNUP_ENABLED`, creates identity with **no role grants**; reset tokens single-use/30-min, delivered via the `guardian_lens.reset_delivery` log line (the SMTP integration point), and a successful reset revokes every session |

## 7. Known gaps and follow-ups, honestly stated

| # | Gap | Consequence | Follow-up |
|---|---|---|---|
| 1 | ~~Agent principals and model versions have no API~~ **Closed 2026-08-13**: `GET`/`POST /api/v1/agents` (one-time composite credential, Argon2-hashed at rest) and `GET`/`POST /api/v1/model-versions` + `/approve` (gate-G1 evidence refs required for approval), site_admin, audited, with a Configuration-screen section for agents. `edge-demo` still seeds by SQL for idempotent re-runs — an operator uses the API | — | TRD §10.6 v1.2, DATABASE.md §10.3 v1.4 |
| 2 | JWT is **HS256** from `GL_JWT_SECRET`. (`cryptography` **is** installed and camera sealing is real AES-256-GCM once `make run` generates `GL_CAMERA_KEY`; the placeholder sealer remains only for key-less environments) | Fine for dev; not the TRD §12.2 production posture | Switch `services/tokens.py` to RS256 — a single swap point |
| 3 | Migration `0010_refresh_tokens` is implemented but the table is not yet in [DATABASE.md](DATABASE.md) §5 | Spec lags code by one table | Recorded in DATABASE.md change log 1.2 with the spec — see [DATABASE.md](DATABASE.md) §5.13 |
| 4 | Only the login rate limiter exists; other §12.7 tiers are commented where they belong | MVP-acceptable | With the first pilot |
| 5 | Deprovisioning a tenant retires its slug forever (the tombstone keeps the UNIQUE slug) | Deliberate — identity is never reused — but worth knowing before naming tenants | None; documented behaviour |
| 6 | `tenant_databases.credential_ref` is not resolved in dev — connections derive from `GL_TENANT_DB_URL` | Dev-only shortcut | Secret-store integration at the commented points in `tenancy/` |
| 7 | The E2E found and fixed a real defect: **deprovision left `user_directory` rows behind**, routing dead tenants and blocking those addresses forever | Fixed in `provisioning.py` — the directory must not outlive the tenant | Covered by the E2E lifecycle now |

## 8. What may not be inferred from a green run

Per BR-M-01 `[PROPOSED]` and AP-2, and because the detector is synthetic: **nothing about detection accuracy, latency or event volume is demonstrated by anything in this document.** A green E2E proves the *workflow* — the gate, the audit trail, the isolation. Accuracy claims require labelled footage from a real site, measured, per class, which does not exist yet (PRD OQ-5). A slide that says otherwise breaks the rule book's most breakable rule.

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-08-12 | Initial runbook: one-command run, edge demo, workflow narrative, contract decisions from the three-plane integration, gap register. | Kapil |
| 1.1 | 2026-08-13 | §3a camera how-to gains the real `--source rtsp` CLI; §4 updated: live RTSP ingestion ✅, `OnnxDetector` implemented but G1-gated; §7 gap 2 narrowed to the RS256 swap (sealing is real AES-GCM now). | Kapil |
| 1.2 | 2026-08-13 | §7 gap 1 closed: agent-principal + model-version APIs (TRD §10.6 v1.2, DATABASE.md §10.3 v1.4) with API tests. §4 updated: Reports carries the verified-only analysis view (single-hue bar by dimension, decision-mix bar, chart tokens per FRONTEND_CODING_STANDARDS §12.1); Configuration gains the edge-agents section; CS-AD-03 confirmations on camera/agent registration and sign-out. | Kuldeep |
| 1.3 | 2026-08-13 | Real-camera readiness: zone and rule **creation** exist in the UI (zone = full-frame at MVP with a CS-AD-03 confirm; rules created inactive per BR-001, activation unchanged), so §3a is now executable end-to-end from the browser — its steps renumbered 1–7 with the agent-registration step added. Whole flow verified in-browser: camera → agent (one-time credential) → zone → inactive rule → attributed activation. §5 web test count 72. | Kuldeep |
| 1.4 | 2026-08-13 | **§3b Going real**: `make onboard` (provision + FF-11 attest + first-admin bootstrap) gives a real site a physically isolated tenant carrying no demo data; edge-demo now prints a DEMO-DATA warning. UI completes site administration: site creation, camera location, **credential replace** (CS-AD-06's replace action) and camera disable/enable — all confirmed submits. §5 web test count 79. | Kuldeep |
| 1.5 | 2026-08-13 | §3a points at the new [CAMERA_ONBOARDING.md](CAMERA_ONBOARDING.md) — the non-normative unbox-to-verified-record orientation (why a camera, the stream's journey, parameters, steps, G1 caveat); commands remain authoritative here. | Kuldeep |
| 1.6 | 2026-08-13 | §3a also points at [CAMERA_INTEGRATION.md](CAMERA_INTEGRATION.md) — the technical integration runbook: two phases with start conditions, dependency-ordered preconditions, API-level sequence with server-side effects, edge runtime behaviour, five acceptance checks, and the G1 detection path. | Kuldeep |
| 1.7 | 2026-08-14 | Detection made runnable in the dev sandbox: edge CLI gains `--model`/`--model-manifest` (OnnxDetector with SHA-256 verification; NullDetector remains the default), and [MODEL_INTEGRATION.md](MODEL_INTEGRATION.md) documents the full dev-evaluation path — export, manifest, registration + approval via `/model-versions`, run, wave test. A dev-only hard-hat model (`hardhat-yolov8n-0.1.0-dev`, card + datasheet under `Docs/models/`) is registered in the pilot sandbox. **Gate G1 for site deployment remains unpassed**; `scripts/status.sh` added earlier gives the one-command stack health check. | Kuldeep |
| 1.8 | 2026-08-14 | **SCR-4 Event History built** (`/history`, all roles): every capture with its evidence thumbnail, timestamp, camera·zone, rule, confidence, **analysing model** (GET /events now returns `model_version`, FR-013) and disposition chip; status filter URL-backed, cursor-paged, end-of-list stated. Configuration decluttered: add-forms collapsed behind per-section buttons, item-count badges; new **Detection models** section shows the registered versions and their G1 approval/deployment state. | Kuldeep |
