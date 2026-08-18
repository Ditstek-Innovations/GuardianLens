# 04 — Product Vision

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 04 — Product Vision (Week 1 deliverable) |
| Companion documents | 00 Idea Blocking · 01 Market Research · 02 Competitive Research · 03 Problem Validation · 05 Business Model |
| Research cut-off | 20 July 2026 |
| Status of this document | Statement of intent. It describes what Guardian Lens is being built to do, not what it has been shown to do. |
| Relationship to evidence | Every claim of achieved benefit is marked as a hypothesis. Document 03 records what is and is not validated. |

> **Vision statement.** Guardian Lens is the verification and evidence layer above a workplace's existing cameras and analytics — turning detections, whether its own or the site's, into a record that no machine may write alone. Nothing becomes a compliance record until a named human has confirmed it.

## 1. What Guardian Lens will accomplish

Four outcomes, stated as intent. The evidence status of each is shown, because a vision document that does not distinguish ambition from proof is a sales document.

| Outcome | What it means in practice | Evidence status |
|---|---|---|
| Continuous observation of defined rules | Configured safety rules are checked continuously through the shift rather than during inspection rounds. PPE rules are detected by Guardian Lens; zone rules are consumed from the site's existing NVR analytics where present. | Category capability demonstrated by competitors. Not demonstrated by Guardian Lens. |
| Human-confirmed events, not machine accusations | No detection becomes a record until an authorised person accepts, rejects or corrects it. The machine proposes; a person decides. | Design commitment. Buyer value unvalidated (doc 03, gap 3). |
| A structured record of what actually recurs | A verified event log showing which rule exceptions repeat, where, on which shift, and how they were dispositioned. | Hypothesis. Benefit must be measured in a pilot. |
| Evidence that survives scrutiny | Each verified event carries its time, camera, zone, the detection, the reviewer decision and the reviewer identity — a defensible chain for internal governance, insurers or regulators. | Design commitment. Legal sufficiency requires review; no claim of regulatory acceptance is made. |

> **What Guardian Lens will not accomplish, and will not claim.** It does not prevent incidents. It does not replace supervision, training, risk assessment, machine guarding, barriers or PPE. It is an observation aid layered on top of existing controls, and it fails safe: if it sees nothing, the site's existing controls are exactly as effective as they were before.

## 2. Who benefits

| Party | What changes for them | What they give up or risk |
|---|---|---|
| The worker on the floor | A hazard they are exposed to is more likely to be noticed and fixed. A collapse in a low-traffic area is more likely to be seen quickly once man-down detection is validated. They are not identified, scored, ranked or timed. | They are within the field of view of an analysed camera. This requires transparency and, where representation exists, consultation. Trust is a precondition, not a by-product. |
| The EHS or safety officer | Primary user. Gains continuous coverage of specific rules and a structured record instead of recollection and paper. Retains the decision on every event. | Gains a review workload. Every false positive costs their time by construction. This is the central design risk. |
| The shift or floor supervisor | Learns about a rule exception in the zone they are responsible for, closer to when it happened. | A new alert channel competing for attention during a shift. |
| The plant head or owner | Visibility into whether safety rules are actually followed, and a defensible record for governance, audit or insurance discussions. | Cost, deployment effort, and accountability for what the record now shows. A verified log can document a problem as easily as it can document diligence. |
| The IT or network administrator | Local or edge processing keeps video on site, avoiding the bandwidth and data-residency problems of cloud streaming. | A new system on the network to maintain, secure and patch. |

> **An honest asymmetry.** The party who benefits most is the worker, who is not the buyer and not the user. The party who bears the most new workload is the EHS officer, who is the user. Any product whose costs and benefits fall on different people has an adoption problem, and this one does. It is a reason to make verification fast and low-friction, and a reason the false-positive rate is an existential metric rather than a quality metric.

## 3. How the process improves

The comparison below describes the intended change. The "today" column is a process model to be confirmed in interviews, not a measured baseline — document 03 records that no customer interviews have been conducted.

| Step | Today (to be confirmed) | With Guardian Lens (intended) |
|---|---|---|
| Observation | Periodic inspection rounds and supervisor attention, competing with production duties. | Continuous checking of defined rules, with humans freed from the rote scanning task. |
| Detection | Depends on who is present, where they are looking, and the time of day. | Consistent against the same configured rule regardless of shift or observer. |
| Judgement | Made in the moment by whoever is present. Rarely recorded. | Made explicitly by an authorised reviewer, and recorded with the decision. |
| Recording | Paper, spreadsheet, or nothing. CCTV footage exists but is reviewed only after something goes wrong. | A structured verified event at the moment of review, with the footage reference attached. |
| Analysis | Difficult. The underlying data is inconsistent or absent. | Aggregation by zone, rule, shift and time becomes possible because the records are structured. |
| Action | Corrective action taken and recorded through whatever system exists. | Unchanged. Guardian Lens informs the action; it does not take it. |

The improvement claim is deliberately narrow: consistency of observation and quality of the record. It is not a claim about fewer injuries, and no such claim will be made without a measured pilot.

## 4. What humans will continue to control

This section is the product, not a policy appendix. Everything below is a design constraint that the architecture must enforce, not a promise that operators are trusted to keep.

#### 4.1 The control charter

| Decision | Who holds it |
|---|---|
| Which rules are monitored at all | The customer. Guardian Lens ships no rule enabled by default. Every monitored rule is switched on deliberately by the site, and should correspond to a written site rule. |
| Where cameras look and which are connected | The customer. Guardian Lens never expands coverage on its own. |
| Whether a detection is real | An authorised human reviewer. A detection that is not accepted is not an event. It cannot enter the record, trigger a report, or appear in a trend. |
| Whether an event warrants action, and what action | The site's existing safety and HR processes, entirely outside the product. Guardian Lens has no disciplinary function and no interface to one. |
| What the record says | The reviewer. A reviewer can reject or correct a detection, and the correction is what is recorded. |
| Retention and deletion | The customer, configured per site, consistent with purpose-linked erasure obligations. |
| Turning it off | The customer, at any time, without vendor involvement. |

#### 4.2 Architectural non-negotiables

1. No facial recognition, identity matching, biometric templates or emotion classification. The system detects a condition in a frame, not a named person.
1. No automatic action of any kind. There is no code path from a detection to a consequence for a worker.
1. No productivity, activity, idle-time, presence-at-station, work-rate or output measurement — at any horizon. The system is not built to produce these outputs.
1. Local or edge processing by default, so video does not need to leave the site.
1. No audio capture.
1. Every verified event carries its reviewer decision and reviewer identity, so the record shows a human made the call.
1. Rejected detections are retained as rejected, so the system's own error rate remains visible to the customer rather than being quietly discarded.

> **The last point is unusual and deliberate.** Most systems hide their false positives. Guardian Lens should expose its own reject rate to the customer, because a safety instrument whose error rate is invisible cannot be trusted by the people it observes — and because a customer who can see the reject rate falling has a reason to keep paying.

#### 4.3 A trade-off stated openly

Peer-reviewed work found that helmet-class detection accuracy on blurred faces decreased by 7%, while person and vest classes were unaffected. Face blurring is a privacy control Guardian Lens intends to adopt. The evidence indicates it carries a measurable accuracy cost on the most central PPE class. Guardian Lens will take the privacy cost knowingly and disclose it, rather than discovering it during a pilot or quietly dropping the control to improve a metric.

## 5. How Guardian Lens differs

> **Read document 01 section 6 first.** Existing-camera PPE and zone detection, at the edge, with Factories Act-aligned reporting, is already sold in India by domestic vendors. Guardian Lens has no capability-based differentiation available, and this document does not manufacture one.

#### 5.1 The revised positioning statement

> Guardian Lens is the transparently priced, human-verified safety and compliance layer for workplaces the enterprise platforms do not serve — turning existing cameras and existing analytics into auditable safety evidence, where no event becomes a record until a named person has verified it.

This replaces the earlier framing of a privacy-conscious AI safety layer. That description remains accurate but is no longer distinguishing: the funded competition occupies it, and in the case of Buddywise and Surveily occupies it more credibly. The revised statement rests on the three positions that survive scrutiny — commercial transparency, the verification gate, and evidence integrity — none of which is a detection capability.

#### 5.2 Who Guardian Lens actually competes against

The realistic competitor for a small or medium Indian manufacturer is not a funded enterprise platform they will never evaluate. It is the status quo: a clipboard, a periodic walkthrough, and CCTV footage reviewed only after an incident has already happened. Positioning against Intenseye or Voxel invites a comparison Guardian Lens loses on every capability axis. Positioning against manual inspection and passive recording is both winnable and true.

#### 5.3 Differentiation claims, graded

| Position | Status | Assessment |
|---|---|---|
| Mandatory human verification before any record exists | Candidate differentiator | Not observed as a headline architectural commitment among the vendors reviewed. Most position the human as a responder to alerts; Guardian Lens positions the human as the gate. Unvalidated: buyers may experience it as friction. |
| Reviewer-attributed audit provenance | Candidate differentiator | Competitors advertise audit-ready reports. The distinguishing element is that each record carries who confirmed it, not that a report exists. |
| Visible reject rate | Candidate differentiator | No vendor reviewed publishes its own false-positive rate to customers. Commercially uncomfortable, which is precisely why it is defensible. |
| Works with existing cameras | Not differentiating | Universal in the category. |
| Edge or local processing | Behind the frontier | Not merely undifferentiated but behind. Buddywise analyses feeds in real time without storing data and does not identify subjects; Protex AI offers configurable data residency; Surveily positions on GDPR and EU AI Act compliance. Edge architecture is also the India market default at 55%. Guardian Lens must meet this baseline, not claim it as an advantage. |
| Does not inspect phone content | Not differentiating | No vendor does. Claiming it implies otherwise. |
| Affordable for SMEs | Unproven | No Indian price benchmark exists. See document 05. |
| Low-commitment pilot | Already matched | A competitor markets a zero-cost proof of concept through AWS Marketplace. This cannot be a differentiator. |

The strategic reading: Guardian Lens is not differentiated on what it can see. If it is differentiated at all, it is on what it refuses to do with what it sees. That is a governance position rather than a technology position, and it will win or lose on whether buyers and workers value governance enough to choose it.

## 6. Roadmap horizons

Reproduced from document 00. The vision is broad; the approval scope is narrow; the difference is sequencing on evidence.

| Horizon | Timing | Contents | Gate to enter |
|---|---|---|---|
| H0 — POC | By 14 August 2026 | One detection class on one feed; human accept / reject / correct; event history; basic report. | None. Workflow demonstration only. |
| H1 — Approval scope | Post-POC, pilot | PPE-rule detection (own model). Restricted-zone entry integrated from existing NVR analytics rather than detected independently. | Buyer validation, camera-feasibility test, NVR event-integration test. |
| H2 — Validated expansion | After a pilot | Man-Down / Possible-Collapse Detection. Phone use inside a designated hazardous zone where a written rule exists. | Separate feasibility validation per event type on real site footage. |
| H3 — Configurable platform | Long term | Operator-defined safety rules; unsafe proximity to machinery, vehicles and stairs; multi-site aggregation; broader industries. | Demonstrated configuration repeatability without bespoke engineering. |

The end state is a platform on which a site defines its own visually detectable safety rules. Guardian Lens reaches that state by proving one rule at a time, because each additional event type multiplies site-specific tuning and reviewer workload.

## 7. How success would be measured

These are the metrics a pilot must produce. None has a target value, because setting a target before the first measurement would be inventing a number.

| Metric | Definition | Why it matters |
|---|---|---|
| Reviewer acceptance rate | Proportion of candidate events a reviewer accepts as real. | The product's honest accuracy measure in the field, as opposed to a dataset score. |
| Review time per event | Median seconds from alert to disposition. | Determines whether the product creates or consumes safety capacity. |
| Events per reviewer per shift | Volume a reviewer must adjudicate. | The abandonment threshold. Too many and the system is switched off. |
| Rule-exception recurrence | Whether the same verified exception repeats in the same zone over time. | Tests whether the record produces insight, not just data. |
| Configuration time per new rule | Hours to add and tune a rule at a site. | The services-versus-software test. This determines whether the business can scale. |
| Worker acceptance | Qualitative, from consultation at the site. | A deployment blocker independent of buyer decision. |

## 8. Risks to the vision

| Risk | Nature |
|---|---|
| Verification is friction, not value | The whole differentiation thesis rests on buyers valuing the human gate. If they want fewer steps rather than more defensible ones, the position collapses and Guardian Lens becomes an undifferentiated detector. |
| False positives consume the benefit | The design converts every detection error into reviewer labour. A rate that a dashboard-only product could tolerate may be fatal here. |
| Camera reality defeats the premise | Peer-reviewed reviews identify camera positioning, resolution and distance as unresolved questions. If SME sites lack adequate coverage, no amount of product quality helps. |
| Scope creep re-introduces surveillance | Commercial pressure to add "just one more" detection type is how a safety product becomes a monitoring product. The exclusions in document 00 section 4.2 exist to make that a visible decision rather than a drift. |
| The governance position is copied | Human verification is not technically hard. A larger competitor could adopt it in a release. The defensibility, if any, is in being trusted for it first, not in owning it. |
| The hardware layer absorbs the value | If camera manufacturers extend on-device analytics upward into verification and reporting, the layer Guardian Lens occupies narrows. Hanwha Vision publishing safety analytics research is early evidence of manufacturers moving in this direction. |
| Configuration does not generalise | If each site needs bespoke tuning, the vision of a configurable platform becomes a consulting practice with software attached. |

> **In one sentence.** Guardian Lens converts cameras a workplace already owns into a continuously watching, human-verified safety record — deliberately refusing to watch anything that is not a safety rule, and deliberately refusing to decide anything on its own.
