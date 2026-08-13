# Guardian Lens — Camera Integration, Technically

**The two integration phases, their preconditions, the API-level sequence, the edge runtime behaviour, and the acceptance checks that define "integrated"**

| Field | Value |
|---|---|
| Document | Technical runbook (Diátaxis: **how-to / reference**). Companion to [WORKFLOW.md](WORKFLOW.md) §3a–§3b, which stays authoritative where they overlap; endpoints normative in [TRD.md](TRD.md) §10; gate G1 normative in [GOVERNANCE.md](GOVERNANCE.md) §9 |
| Version | 1.0 |
| Date | 13 August 2026 |
| Owner | Kuldeep (Product) |
| Audience | The engineer performing the integration |
| Companion explainer | [CAMERA_ONBOARDING.md](CAMERA_ONBOARDING.md) — why a camera, in plain language |

---

## 1. Two phases, two start conditions

| Phase | What it integrates | When it can start |
|---|---|---|
| **1 — Stream** | Camera → edge agent → control plane: frames sampled, health beating, coverage gaps honest, events path live | **Immediately.** Every prerequisite is built, tested and UI-operable; the whole phase is ~1 hour once the camera is mounted |
| **2 — Detection** | A real model firing rules on those frames | The day a model clears gate **G1** (model card + dataset datasheet + measured, condition-stratified evaluation, named approver). Zero reconfiguration of Phase 1 |

Phase 1 satisfies TRD §20.2 step 5: **stream reliability under real conditions**.
It proves nothing about detection, deliberately — in `--source rtsp` the
detector is `NullDetector` until G1 admits an artefact.

## 2. Phase 1 preconditions, in dependency order

| # | Precondition | How to verify |
|---|---|---|
| 1 | Tenant provisioned, FF-11 attested, `active` — `make onboard TENANT=… ADMIN_EMAIL=… ADMIN_NAME=… SITE_NAME=… TZ=…` (real site: fresh isolated database, no demo data — [WORKFLOW.md](WORKFLOW.md) §3b) | `make attest TENANT=…` reports 28/28 registry objects; login succeeds |
| 2 | Key material on both ends: `GL_CAMERA_KEY` + `GL_CAMERA_KEY_ID` (AES-256-GCM) — control plane **seals**, edge **unseals**; generated once into `.env` by `make run` | Same values in the control plane's `.env` and the edge box's environment |
| 3 | Edge box on the camera's network: Python 3.11+, repo, `pip install -e ".[edge-camera]"` (OpenCV decode) | `python -c "import cv2"` succeeds |
| 4 | Camera RTSP reachable **from the edge box** (the control plane never contacts cameras — TRD §12.6 A10) | `ffprobe "rtsp://user:pass@ip:554/<path>"` or VLC, run on the edge box |
| 5 | `[OPEN]` thresholds decided per deployment — required CLI inputs with **no defaults**: outbox warning/critical bytes (OQ-4), failure window + degraded/halt rates (ADR-009), decode-failure streak (MOD-1) | Written down before step 4 of §3 |

## 3. Phase 1 sequence — what each call does

All configuration is a confirmed submit in the panel (Administration →
Configuration); the API calls beneath it, with their server-side effects:

| Step | Call (role) | Server-side effect |
|---|---|---|
| 1 | `POST /api/v1/cameras` (site_admin) | `stream_url` sealed immediately (AES-256-GCM under `GL_CAMERA_KEY`); `stream_url_encrypted` + `stream_url_key_id` stored; plaintext does not outlive the request. `camera.created` audit row and the site `config_version` bump commit in the **same transaction** (BR-C-01) |
| 2 | `POST /api/v1/agents` (site_admin) | Agent principal row with Argon2id `credential_hash`; the response carries `slug:agent_id:secret` **exactly once** → edge env `GL_AGENT_CREDENTIAL`. Audited (`agent.registered`, never credential material). An agent principal can never hold a review role — the grant relation does not exist (BR-S-02, migration 0003) |
| 3 | `POST /api/v1/zones` (site_admin) | Zone polygon in normalised 0–1 space (full frame at MVP). Audited; `config_version` bump |
| 4 | `POST /api/v1/rules` (safety_manager+) | Rule created **inactive, always** — the schema has no `is_active` field to send (BR-001) |
| 5 | `POST /api/v1/rules/{id}/activate` (safety_manager+) | `is_active`, `activated_by` (from the token — no parameter exists), `activated_at`; audited; `config_version` bump. Monitoring of that zone begins at the agent's next config sync |
| 6 | Start the edge agent (site box): | — |

```bash
GL_AGENT_CREDENTIAL='<slug:agent_id:secret>' \
GL_CAMERA_KEY='<hex>' GL_CAMERA_KEY_ID='<id>' \
python -m guardian_lens_edge --source rtsp \
  --api https://<control-plane> \
  --agent-id <uuid-from-the-agents-list> --site <uuid> \
  --data-dir /var/lib/guardian-lens \
  --outbox-warning-bytes <n> --outbox-critical-bytes <n> \
  --failure-window <n> --degraded-failure-rate <f> --halt-failure-rate <f> \
  --decode-failure-threshold <n>
```

Secrets ride the environment, never argv (TRD §12.4).

## 4. What the edge runtime then does

1. **Auth**: exchanges `GL_AGENT_CREDENTIAL` at `POST /api/v1/auth/agent` for a
   short-lived agent JWT; re-exchanges on expiry.
2. **Config sync** (every `--config-interval`, default 30 s): `GET
   /api/v1/agents/{id}/config` with `If-None-Match` — an unchanged
   `config_version` costs one 304. The document carries the site's cameras
   (sealed URLs + key id), zones and **active rules only**.
3. **Unsealing**: stream URLs decrypt in memory only, inside
   `UnsealedStreamUrl` with a redacted `repr` — no plaintext in logs, argv or
   disk.
4. **Capture**: one thread per camera, sampling at that camera's
   `sample_rate_fps` (default 2.0); bounded frame queue across cameras
   (`--queue-capacity`), newest-dropped-and-counted on overflow.
5. **Loss handling**: reconnect with exponential backoff 1→60 s; after
   `--decode-failure-threshold` consecutive decode failures the camera is
   reported degraded and a `stream_lost` coverage gap opens — including for a
   camera that never connects at all.
6. **Health**: `POST /api/v1/agents/health` every `--health-interval`
   (default 30 s) — updates `last_seen_at`/`last_health_at`, measures clock
   skew (ADR-007: timestamps are never silently corrected), and is what
   agent-down gap inference keys on.
7. **Durability**: events and gaps land in the SQLite outbox (WAL,
   `synchronous=FULL`) before any network attempt; the publisher tick (every
   `--publish-interval`) posts `POST /api/v1/events` at-least-once, deduplicated
   server-side on `event_id`. Outbox growth past the warning/critical byte
   thresholds degrades and then **halts loudly** — buffered events are never
   evicted to keep monitoring alive (T-5: the record beats the uptime).

## 5. Acceptance checks — the definition of "integrated"

| Check | Pass criterion |
|---|---|
| Agent liveness | Configuration → Edge agents: status flips `Offline → Active` on the first health beat; Last seen updates each interval |
| Camera liveness | Cameras table shows the stream `Active` |
| **Gap honesty (the one that matters)** | Pull the camera's cable → after the decode-failure streak, a `stream_lost` gap **opens** (Reports → coverage gap minutes rises). Reconnect → the gap **closes**. Both transitions observed |
| Durability | Stop the control plane briefly with the agent running → outbox pending count rises; restart → drains to zero, no duplicates in the queue (`event_id` dedup) |
| Audit | Every configuration step above has its row in the audit log, named and timestamped |

When all five hold, Phase 1 is done. Day-two operations stay in the panel:
wrong stream password → **Replace credential** (write-only; the old one is
never displayable); maintenance → **Disable** / **Enable** (stops/resumes
watching at next sync); every change confirmed and audited.

## 6. Phase 2 — detection, through gate G1

1. Produce the artefact: fine-tune a detector on labelled site frames
   (pipeline-compatible baseline: a YOLO-decode model exported to ONNX —
   `OnnxDetector` implements manifest + SHA-256 verification, YOLO decode,
   NMS), measure held-out **and condition-stratified** performance (night,
   rain, occlusion).
2. Register the evidence: `POST /api/v1/model-versions` — version, `sha256:`
   artefact hash, classes, model-card ref, datasheet ref.
3. Approve: `POST /api/v1/model-versions/{id}/approve` — refuses without both
   references (422); approver is the token's principal; audited
   (`model.approved`). Deployment without approval is impossible at the
   database (`chk_model_deployed_requires_approval`, migration 0004).
4. Ship the ONNX artefact + manifest to the edge box; `OnnxDetector` refuses
   any artefact whose SHA-256 does not match the manifest.
5. From that moment the Phase-1 camera, zone and rule produce real candidates
   into the review queue — no reconfiguration. Accuracy claims still require
   the measured evaluation, per BR-M-01: a green pipeline demonstrates the
   workflow, never the model.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-08-13 | Initial technical runbook: two phases with start conditions, dependency-ordered preconditions, API-level sequence with server-side effects, edge runtime behaviour, acceptance checks, G1 detection path. | Kuldeep |
