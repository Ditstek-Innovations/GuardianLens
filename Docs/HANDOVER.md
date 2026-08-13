# Guardian Lens — Developer Handover

**Where the implementation stands, how to run and verify it, and where the next developer starts**

| Field | Value |
|---|---|
| Document | Orientation / handover (Diátaxis: **explanation**). **Non-normative** — it points at the authoritative documents and restates nothing; where this file and any companion disagree, the companion wins |
| Version | 1.0 |
| Date | 13 August 2026 |
| Owner | Kapil (Engineering) |
| Status | Development / pilot form. Gate **G0** not passed; no customer-site deployment |
| Companions | [WORKFLOW.md](WORKFLOW.md) (how to run — read it after this file) · [ARCHITECTURE.md](ARCHITECTURE.md) · [DATABASE.md](DATABASE.md) · [TRD.md](TRD.md) · [RULE_BOOK.md](RULE_BOOK.md) · [GOVERNANCE.md](GOVERNANCE.md) · [PRD.md](PRD.md) · [BACKEND_CODING_RULES.md](BACKEND_CODING_RULES.md) · [FRONTEND_CODING_STANDARDS.md](FRONTEND_CODING_STANDARDS.md) |

---

## 1. The one thing to know before touching anything

**The entire implementation is uncommitted working-tree state on `master`.**
Roughly ninety files — migrations, backend, frontend, edge agent, tests, docs —
exist only on this machine. Nothing has been committed, deliberately, pending
review. The first engineering task is therefore to review and land this work in
coherent chunks, honouring one rule while doing so: **T3
([GOVERNANCE.md](GOVERNANCE.md))** — a business-rule *enforcement* change and
its *bypass-suite* change never travel in the same PR.

Second thing: `.env` is machine-specific and never committed
([TRD.md](TRD.md) §12.5). Copy `.env.example`, or run against your own
PostgreSQL — `scripts/run_dev.sh` probes `POSTGRES_HOST:POSTGRES_PORT` and uses
an existing server if one answers, falling back to the Docker `db` service.

## 2. What Guardian Lens is

AI-assisted workplace-safety camera monitoring in which **no AI output becomes a
record of fact without a named human verifying it** (BR-004/BR-005 — the
system's spine). Edge agents watch site cameras, evaluate deterministic rules,
and ship candidate events to a control plane; reviewers accept, reject or
correct each candidate in a keyboard-first queue; reports draw **only** from
verified records; every material action lands in an append-only audit log.
Absence of monitoring is recorded honestly as **coverage gaps** — "we were not
watching" is always visible.

## 3. Documents — reading order and authority

Read in this order: [PRD.md](PRD.md) (what and why) → [RULE_BOOK.md](RULE_BOOK.md)
(the BR-* rules; 25 of 45 still `PROPOSED`) → [ARCHITECTURE.md](ARCHITECTURE.md)
(structure; ADRs) → [DATABASE.md](DATABASE.md) (schema, constraints, FF-11) →
[TRD.md](TRD.md) (how it is enforced; deployment sequence §20.2) →
[WORKFLOW.md](WORKFLOW.md) (running it) → the two coding-rules files.

Authority when documents overlap, as each declares in its own header:
**RULE_BOOK** prevails on what the rules require; **PRD** on product intent;
**GOVERNANCE** on process; **ARCHITECTURE**/**DATABASE** are normative for
structure and data, with TRD §2/§8–9 as summary views of them.

**Ownership is enforced socially, not by tooling:** Kapil owns TRD,
ARCHITECTURE, DATABASE, WORKFLOW and both coding-rules files. **Kuldeep** owns
RULE_BOOK, GOVERNANCE and PRD — those are amended **only** by Kuldeep; proposals
to them are queued as amendment lists (currently `AMD-RB-01…04`, `AMD-GOV-01`),
never applied directly. Cross-document amendment queues awaiting Kapil are
recorded in the documents themselves (`AMD-ARCH-*`, `AMD-DB-*`).

## 4. Repository map

| Path | What lives there |
|---|---|
| `Docs/` | All documents, including this one |
| `migrations/tenant/` (`0001`–`0011`) · `migrations/control/` (`c0001`) | Two Alembic lines, separate version tables. Tenant schema carries every business constraint; control holds routing only (ADR-017) |
| `src/guardian_lens/` | Control plane: FastAPI app factory, routes, services, repositories, the seven guards, tenancy router (ADR-016 database-per-tenant), provisioning + FF-11 attestation, rules registry, bootstrap CLI |
| `src/guardian_lens/rules/registry.py` | **The** enforcement registry — 28 named DB objects. FF-11 verifies each exists in every tenant DB before that tenant may be `active`. A new constraint is not real until it is registered here |
| `src/guardian_lens_edge/` | Edge agent: SQLite outbox, deterministic D1 evaluator, ADR-009 state machine, publisher, config sync, RTSP capture (`rtsp.py`, `multicamera.py`, `unsealer.py`), detectors. **Imports nothing from `guardian_lens`** — a test enforces this |
| `web/` | React + TypeScript review UI: auth flows, keyboard-first queue, reports, config; design tokens in `src/styles/tokens.css`, message catalogue in `src/constants/messages.ts` |
| `tests/` | `bypass/` (direct-SQL violation attempts DB-1…DB-27) · `api/` · `edge/` · `unit/` · `integration/` · `migrations/` · `e2e/` (full workflow) |
| `scripts/run_dev.sh` | Everything `make run` does: DB probe/fallback, control migration, tenant provision→attest→activate, `GL_CAMERA_KEY` generate-once into `.env`, bootstrap, API + Vite |
| `Makefile` · `docker-compose.dev.yml` · `.github/workflows/ci.yml` | Entry points, dev services (incl. `--profile camera` RTSP sim), CI |

## 5. What is built and verified

The full plane-by-plane state is [WORKFLOW.md](WORKFLOW.md) §4 — kept current
there, not duplicated here. In one line: **schema + bypass suite, control
plane, review UI, and the edge agent (synthetic replay *and* live multi-camera
RTSP) are done and tested; the ONNX detector is implemented but G1-gated; V1
items (retention worker, NVR connector, RS256, SMTP delivery) are not started.**

Verification as of this handover, on this machine (Python 3.11, user's own
PostgreSQL 18.4):

| Evidence | Result |
|---|---|
| Full Python suite (`.venv/bin/pytest`, `.env` sourced) | **377 passed, 2 skipped** — the skips are the two RTSP integration tests, which pass with `make camera-sim` up (suite map: [WORKFLOW.md](WORKFLOW.md) §5) |
| Web suite (`cd web && npx vitest run`) | **67 passed** across 15 files |
| `bandit -r src/` | clean |
| FF-11 attestation | 28/28 registry objects verified on the pilot tenant |
| E2E (`tests/e2e/test_full_workflow.py`) | provision → bootstrap → configure → activate → edge scenario → ingest → queue → evidence → decide → duplicate-decision 409 → verified-only report → audit |
| Live RTSP (`make camera-sim` + `tests/edge/test_rtsp_integration.py`) | real JPEG frames at the sample rate; stream kill → `stream_lost` gap opens; restore → gap closes |

## 6. Invariants a new developer must not break

Each is enforced somewhere that will fail loudly — this list is why the failure
is a feature, with the authority in brackets.

1. **No unverified AI output in any report or export** — repository-level
   verified-only filter, partial index, FF-7 [BR-004/BR-005].
2. **`audit_log` is append-only** — row- and statement-level triggers refuse
   UPDATE/DELETE/TRUNCATE. Tests that "clean up" audit rows are wrong by
   definition; assert on your own rows via `RETURNING` instead [DATABASE.md §5].
3. **Tenant isolation is physical** — one database per tenant; no `tenant_id`
   columns on business tables; `tenant_identity` asserted per connection;
   slug validation identical in code and CHECK constraint [ADR-016/017].
4. **Every enforcement object is registered** — add a constraint/trigger →
   register it in `rules/registry.py` → FF-11 attests it, or the tenant never
   activates. `PROPOSED`-rule failures are advisory; `ACTIVE` are blocking.
5. **T3 split** — enforcement and bypass suite never in the same PR; CI checks.
6. **`[OPEN]` values are never guessed** — thresholds marked `[OPEN]`
   (OQ-4 outbox bytes, ADR-009 rates, MOD-1 decode-failure streak) are
   *required* CLI/env parameters with no defaults, on purpose.
7. **No detection claims** — the detector is synthetic/Null until gate **G1**
   admits a model with card, datasheet and measured evaluation
   [GOVERNANCE.md §9; WORKFLOW.md §8].
8. **Secrets never in argv or logs** — agent credential and camera key are
   env-only; unsealed stream URLs live only inside `UnsealedStreamUrl` with
   redacted `repr`; the control plane seals camera credentials and **cannot
   read them back** [TRD §12.4].
9. **Frontend voice and design system** — messages come from the catalogue
   (`constants/messages.ts`; the literal strings "Success"/"Failed" are
   banned), validation stays inline, tokens from `tokens.css`
   [FRONTEND_CODING_STANDARDS.md §12].

## 7. Where to start, in order

1. **Land the working tree** (§1): review, chunked commits/PRs, T3 respected.
2. **Apply or reject the queued amendments** — `AMD-ARCH-*`, `AMD-DB-*`
   (Kapil); hand `AMD-RB-01…04`, `AMD-GOV-01` to Kuldeep.
3. **[WORKFLOW.md](WORKFLOW.md) §7 gap register** — the honest list, kept
   current there. Highest-leverage first entries: agent/model-version APIs
   (today seeded by direct SQL), RS256 swap point, SMTP delivery for password
   reset (integration point: `guardian_lens.reset_delivery` log line),
   remaining rate-limit tiers.
4. **Pilot-blocking open questions** — OQ-9 (cameras per edge device: benchmark
   on target hardware) and gate G1 evidence for any real model.
5. **V1 items** — retention worker MOD-11, NVR connector MOD-5, production
   deployment TRD §20.3.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-08-13 | Initial handover: uncommitted-state warning, reading order and authority, repo map, verification evidence, invariants, ordered next steps. | Kapil |
| 1.1 | 2026-08-13 | Post-handover work landed (uncommitted, same tree): panel shell + configuration redesign; Reports analysis view; WORKFLOW §7 gap 1 closed (agent + model-version APIs, G1 evidence gates); zone/rule creation in the UI, making WORKFLOW §3a executable end-to-end from the browser; CS-AD-03 confirmations. §5 evidence superseded by WORKFLOW §5 v1.3 (386 Python checks, 72 web). Companion versions: TRD 1.2, DATABASE 1.4, WORKFLOW 1.3. | Kuldeep |
