# Guardian Lens — A Camera Arrives: Why, What, and the Steps

**What a physical camera is for in this product, what the system does with its stream, and the exact path from unboxing to the first verified record**

| Field | Value |
|---|---|
| Document | Orientation + walkthrough (Diátaxis: **explanation / how-to**). **Non-normative** — commands and thresholds are authoritative in [WORKFLOW.md](WORKFLOW.md) §3a–§3b; rules in [RULE_BOOK.md](RULE_BOOK.md); endpoints in [TRD.md](TRD.md) §10 |
| Version | 1.0 |
| Date | 13 August 2026 |
| Owner | Kuldeep (Product) |
| Audience | Whoever stands in front of the new camera with a box cutter — site admin, installer, or founder |
| Companions | [WORKFLOW.md](WORKFLOW.md) · [CAMERA_INTEGRATION.md](CAMERA_INTEGRATION.md) (the technical runbook of the same journey) · [PRD.md](PRD.md) · [RULE_BOOK.md](RULE_BOOK.md) · [GOVERNANCE.md](GOVERNANCE.md) · [ARCHITECTURE.md](ARCHITECTURE.md) |

---

## 1. Why do we need a camera at all?

Most workplaces already own cameras. They record continuously into an NVR that
nobody watches, and the footage is opened only after something has gone wrong —
as evidence of an injury that already happened.

Guardian Lens exists to invert that: the camera stops being a passive recorder
and becomes the **sensor of a safety instrument**. Its job is narrow on
purpose:

- **It watches for configured safety rules, and nothing else.** "Helmet
  required in Bay 3" is a rule a named person wrote and explicitly activated
  (BR-001 — nothing is monitored by default). No rule, no watching.
- **It produces candidates, never facts.** When a rule fires, the system
  creates a *candidate event* with a single still evidence frame. A candidate
  becomes a record only when a named human reviewer accepts, corrects or
  rejects it (BR-004/BR-005 — the product's spine).
- **It never watches people as people.** No identification, no per-worker
  tracking, no productivity metrics — those affordances do not exist in the
  build, for anyone (BR-002, TRD §7.4).
- **It is honest about not watching.** Any interruption — cable pulled, camera
  dead, agent offline — is recorded as a *coverage gap* that appears in
  reports. "Zero events" is never allowed to masquerade as "nothing happened"
  when the truth is "nobody was looking" (FR-005).

So the camera's purpose in one sentence: **feed frames to deterministic rules
so that humans can verify real safety exceptions, with an honest record of
when nothing was being watched.**

What it is deliberately **not**: not a video archive (evidence is a single
still frame, never video — BR-008), not an AI judge (confidence orders the
queue; it never decides — BR-V-03), and not a detector yet — see §5.

## 2. What the system does with the stream, end to end

```
camera (RTSP) ──► edge agent, on a box at the site
                    │  samples frames at the camera's sample_rate_fps
                    │  evaluates ACTIVE rules over configured zones
                    │  (detector: G1-gated — see §5)
                    ▼
                  SQLite outbox (survives network loss; nothing is dropped silently)
                    ▼  publish, at-least-once
control plane ──► ingest ► review queue ► a named human decides (A / R / C)
                    ▼                         ▼
              coverage gaps            verified records only
                    └────────► Reports ◄──────┘        └─► append-only audit log
```

Step by step:

1. The edge agent pulls its configuration from the control plane (cameras,
   zones, active rules). Stream credentials arrive **sealed** and are
   decrypted in memory only, on the edge box.
2. It connects to the camera over RTSP and samples frames — it does not record
   video. Connection loss triggers reconnects with 1→60 s backoff and opens a
   `stream_lost` coverage gap; recovery closes it.
3. When an active rule fires, it builds a candidate event — rule snapshot,
   confidence, timestamp, one evidence frame — into a durable local outbox,
   then publishes to the control plane. A network outage buffers; it never
   silently discards.
4. The candidate lands in the review queue. A reviewer sees the frame and the
   rule, and decides: accept (it becomes a verified event carrying their
   name), correct (fix a field; the original model output is retained), or
   reject (retained and visible in the rejection log — BR-007).
5. Reports and exports draw **only** from verified records, always shown
   against the coverage gaps of the same period. Every material step lands in
   the append-only audit log.

## 3. What you need before you start

**The camera itself**
- Any IP camera that speaks **RTSP** (virtually all ONVIF cameras do). You
  need its stream URL, usually `rtsp://user:password@<ip>:554/<path>` — the
  path is vendor-specific (check the camera's manual or admin page).
- Mounted so the frame actually covers the area the safety rule is about,
  powered (PoE or adapter), on a network the edge box can reach. The control
  plane never talks to the camera directly — only the edge box does.
- Sanity-check the URL from the edge box first, e.g. open it in VLC or
  `ffprobe "rtsp://…"`. If that fails, nothing downstream can succeed.

**An edge box at the site**
- Any Linux machine on the same network as the camera. Python 3.11+, this
  repo, and the decode extra: `pip install -e ".[edge-camera]"`.
- How many cameras one box can carry is an open question to benchmark on your
  hardware (`[OPEN — OQ-9]`).

**A running control plane and a real tenant**
- Dev: `make run`. Real site: `make onboard …` — a fresh, physically isolated
  tenant with **no demo data in it, ever** ([WORKFLOW.md](WORKFLOW.md) §3b).

**The parameters you will be asked for**

| Parameter | Where it is set | Meaning / guidance |
|---|---|---|
| Stream URL + credentials | UI → Cameras (write-only) | Sealed on save, never shown again; **Replace credential** is the only path afterwards |
| Location | UI → Cameras | Where the camera physically is — future-you will thank present-you |
| `stream_profile` | API (default `secondary`) | Which vendor stream to use; secondary/sub-stream is usually enough at 2 fps and far cheaper to decode |
| `sample_rate_fps` | API (default 2.0, max 30) | Frames sampled per second. Safety rules rarely need more than 2 |
| Zone | UI → Zones | Full frame at MVP; finer polygons are a refinement |
| Rule: type, confidence threshold, debounce, rule text, written-rule reference | UI → Detection rules | Threshold orders candidates (never decides); debounce is the quiet period before the same rule may fire again; the reference ties it to your written site safety rule (BR-011) |
| `GL_AGENT_CREDENTIAL` | edge box env | The one-time `slug:agent_id:secret` from UI → Edge agents |
| `GL_CAMERA_KEY` / `GL_CAMERA_KEY_ID` | edge box env | Copied from the control plane's `.env` — seals there, unseals here |
| Outbox warning / critical bytes; failure window / degraded / halt rates; decode-failure threshold | edge CLI flags | `[OPEN]` product thresholds (OQ-4, MOD-1): **required, no defaults** — you state them per deployment, deliberately |

## 4. The steps — "I have the camera in my hands"

Authoritative commands: [WORKFLOW.md](WORKFLOW.md) §3a (steps) and §3b (real
tenant). In prose:

1. **Mount and network the camera.** Point it at the area your written safety
   rule covers. Confirm the RTSP URL plays from the edge box (VLC/ffprobe).
2. **Have the real tenant ready** — once per site, `make onboard` with your
   real slug, admin, site name and timezone. Sign in. Everything you see from
   here on is real data, because nothing else has ever been written there.
3. **Register the camera** in Configuration → Cameras: name, location, the
   RTSP URL with its credentials. Confirmed submit; credential sealed.
4. **Register the edge agent** (Configuration → Edge agents) and copy the
   one-time credential to the box now — it is never shown again.
5. **Create the zone** on the camera, then **create the rule** (it is born
   inactive) and **activate it** — the activation carries your name.
6. **Start the edge agent** on the box: the env vars and the `--source rtsp`
   command line with your stated thresholds (WORKFLOW §3a step 6, verbatim).
7. **Prove honesty before anything else:** pull the camera's cable — a
   coverage gap opens in Reports; reconnect — it closes. This is the system
   working, not a problem.
8. **Watch it live.** Camera shows *Active*, the agent's health beats update
   its Last seen, and the queue receives candidates whenever an active rule
   fires (see §5 for when that starts). Reviewers decide; Reports fill with
   verified records only.

Day-two operations, all in the panel: wrong password → **Replace
credential**; camera out for maintenance → **Disable** (and later Enable);
new areas → more zones and rules, each activation named and audited.

## 5. The honest caveat: when does it actually *detect*?

Out of the box, a real camera proves **stream reliability and honest gaps** —
frames flow, interruptions are recorded, nothing is claimed. The detector on
real streams is a `NullDetector` until gate **G1** admits a real model with a
model card, a dataset datasheet, and measured, condition-stratified evaluation
([GOVERNANCE.md](GOVERNANCE.md) §9). The `/api/v1/model-versions` API is where
that evidence is registered and approved.

This is not a gap to route around — it is the product refusing to make
detection claims it cannot back. The moment a G1-approved model exists, the
same camera, zone and rule you configured above start producing candidates
with no further setup.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-08-13 | Initial orientation: why a camera, the stream's journey, prerequisites and parameters, unbox-to-verified-record steps, the G1 caveat. | Kuldeep |
