# 06 — Initial Features

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 06 — Initial Features (Week 1 deliverable) |
| Scope | POC feature set and priorities only. Architecture, data model and infrastructure are out of scope by instruction. |
| Delivery date | 14 August 2026 |
| Time available | Approximately three and a half weeks from the 20 July research cut-off |
| Horizon | H0 in the roadmap defined in document 00 section 3 |
| Central claim under test | That a candidate event can be generated, routed to a human, verified, and written to an auditable record. |

> **The single most important scoping decision.** The POC demonstrates a workflow, not a detector. Model accuracy cannot be credibly established in three and a half weeks on one feed, and any attempt to present it as an accuracy demonstration will fail with an evaluator who knows the category. Everything below follows from that decision.

## 1. Prioritisation principle

Features were ranked by one question: does this feature carry the central claim? A feature that makes the demo look more impressive but does not carry the claim is optional at best. Two secondary rules applied:

1. Anything that increases the number of things that can fail live is deprioritised.
1. Anything that could be mistaken for productivity monitoring is excluded outright, regardless of build cost.

## 2. Must-have features

If any of these is missing, the POC does not demonstrate Guardian Lens. All seven are required.

| # | Feature | Definition | Why it is a must-have |
|---|---|---|---|
| M1 | Single live feed ingest | One webcam or one pre-recorded video file, processed locally. | Without a feed there is no product. Recorded video is an acceptable and lower-risk fallback for a live demo. |
| M2 | One detection class — PPE | Helmet presence or absence within a defined area. One class only. PPE is the detection Guardian Lens owns; zone detection is repositioned as an integration feature per document 00 section 3.1. | Peer-reviewed work reports non-helmet detection exceeding 92% accuracy while visually challenging classes fall to around 83.5% under occlusion. Helmet is the evidence-backed choice. |
| M3 | Candidate event generation | Each detection produces a structured record with timestamp, camera identifier, zone and event type. | Structure is what separates this from an alert light. It is the input to everything downstream. |
| M4 | Human review interface | An authorised reviewer can accept, reject or correct each candidate event. | This is the central claim. If only one feature is finished, it must be this one. |
| M5 | Verified event log | Accepted and corrected events are written to a persistent record carrying the reviewer decision and reviewer identity. Rejected events are retained as rejected. | The audit trail is the differentiator. Retaining rejections keeps the system's own error rate visible. |
| M6 | Event history view | A reviewable list of all candidate events and their dispositions. | Demonstrates that the record is usable, not just written. |
| M7 | Basic compliance report | Aggregation of verified events by zone and time period, exportable. | Closes the loop from detection to evidence, which is the outcome the product claims. |

> **If the schedule slips, cut in this order:** M7, then M6, then M3's zone field. Never cut M4 or M5. A POC with a crude detector and a working verified-and-attributed record demonstrates Guardian Lens. A POC with an excellent detector and no human gate demonstrates a competitor's product.

## 3. Optional features

Build only if the must-haves are complete and stable with time to spare. Each adds demonstration value; none carries the central claim.

| # | Feature | Value if included | Risk of including |
|---|---|---|---|
| O1 | Restricted-zone event consumed from an NVR | Demonstrates the integration-layer position from document 00 section 3.1 — a zone event arriving from the site's own hardware, then passing through the same human verification and into the same record. Strategically the most valuable optional feature. | Requires access to a compatible NVR and a working event path. If no NVR is available for testing, this cannot be built at all. |
| O2 | Own restricted-zone detection as a fallback | Covers sites without NVR analytics. | Duplicates what customers' hardware often already does. Build only if O1 proves impossible and a second class is still wanted. |
| O3 | Operator-drawn zone boundary | Makes configurability tangible on screen. | UI work that competes directly with M4 for the same build time. |
| O4 | Face blurring in stored snapshots | Demonstrates the privacy posture physically rather than verbally. | Peer-reviewed work found helmet-class accuracy on blurred faces decreased by 7%. Worth showing, but the trade-off must be stated aloud. |
| O5 | Live alert notification | Shows the alert reaching a person, not just a screen. | External dependency during a live demo. Low value for high fragility. |
| O6 | Reject-rate display | Shows the system reporting its own error rate — a genuine differentiator per document 04. | Meaningless on a tiny sample and may invite accuracy questions the POC cannot answer. |
| O7 | Multiple concurrent feeds | Suggests scale. | High cost, no new claim demonstrated. Recommend against. |

## 4. Excluded features

Not deferred for time. Excluded by decision, with reasons that hold regardless of how much time is available.

| Excluded | Reason |
|---|---|
| Any productivity, activity, idle-time, presence-at-station, work-rate or output measurement | Excluded at every horizon by design, not policy. It has no safety justification and would destroy the product positioning. See document 00 section 4.2. |
| Man-Down / Possible-Collapse Detection | In the product scope at Horizon 2, but not in the POC. Vendor installation guidance documents that fall detection cannot be guaranteed when a person is occluded by another person or goes untracked beyond three seconds — routine factory conditions requiring a separate feasibility gate. |
| Facial recognition, identity matching, biometric templates, emotion classification | Architectural non-negotiable. The system detects a condition in a frame, not a named person. |
| Audio capture | No safety use case in the defined scope. |
| Any automatic action, notification to HR, or disciplinary integration | There must be no code path from a detection to a consequence for a worker. |
| Phone-use detection | Horizon 2 only, and only inside a designated hazardous zone where a written site rule exists. No such customer or rule exists yet. |
| Unsafe proximity to machinery, vehicles or stairs | Requires depth or calibrated geometry rather than a single flat camera view. Horizon 3. |
| Multi-site aggregation, user roles and permissions, custom rule builder | Product features, not POC features. They demonstrate nothing about the central claim. |
| Custom IoT or purpose-built camera hardware | The product premise is that existing cameras are used. Building hardware contradicts the premise. |
| Competing with embedded NVR analytics on zone or intrusion detection | Hikvision AcuSense and Dahua IVS already provide region entrance and intrusion detection with human classification on hardware customers own. Guardian Lens integrates with this layer rather than duplicating it. |
| Any accuracy, precision, false-positive, ROI or incident-reduction figure | A single feed over three weeks cannot support a performance number. Presenting one would be inventing evidence. |

## 5. Demonstration script

The POC should be demonstrated in this order, because it follows the claim rather than the technology.

- Show the feed and state the one rule being checked and where it was configured.
- Trigger a detection. Show the candidate event appearing with its timestamp, camera and zone.
- Pause on the review step. State explicitly that nothing has been recorded yet.
- Accept one event. Show it enter the verified log with the reviewer decision attached.
- Reject one event deliberately. Show that it does not enter the record but is retained as a rejection.
- Show the event history and the report.
- If O1 was built, show a zone event arriving from the NVR and passing through the same verification gate — this demonstrates the layer position more clearly than any slide.
- State the limitations before being asked: one feed, one class, no accuracy claim, no customer.

> **Step 5 is the demonstration.** Deliberately rejecting a detection in front of the audience is the clearest possible proof that the human is the gate rather than a spectator. Most competitor demos show the system being right. Showing the system being overruled is what distinguishes this product.

## 6. Build risks in the available time

| Risk | Severity | Mitigation |
|---|---|---|
| Detector performs poorly on available footage | High | Use recorded footage chosen in advance rather than live webcam. This is legitimate: the POC tests the workflow, not the detector. |
| Team builds the detector first and runs out of time for the review interface | High | Build M4 and M5 first against stubbed detections. The detector can be improved until the last day; the workflow cannot be added at the end. |
| Scope creep into a second detection class | Medium-High | Optional features are gated on M1-M7 being complete and stable. |
| Live demo failure | Medium | Record a backup video of a successful run. Present live, fall back if needed. |
| The demo implies accuracy claims it cannot support | Medium | Scripted limitation statement at step 7, delivered before questions. |
