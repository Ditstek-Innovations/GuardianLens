# 09 — Team Contribution

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 09 — Team Contribution (Week 1 deliverable) |
| Team size | 5 |
| Kuldeep | Team lead. Product ownership, market research (jointly with Mayank), and final review of all work. |
| Mayank | Market research (jointly with Kuldeep); human and AI validation; product implementation, software side. |
| Kapil | Hardware and software implementation and integration. |
| Kamal | Hardware and software implementation and integration. |
| Yashpal | Testing, with specific ownership of edge-case and failure-mode testing. |
| GitHub handles | Collected and administered by Kuldeep — see section 8. |
| Availability | Proposed weekly phasing to 14 August is set out in section 6. Each member confirms their own figure. |
| Contribution evidence | Populated as work proceeds — see section 8. |

> **Ownership is complete.** Every deliverable in the Week 1 set has a named owner, every member owns at least one document end to end, and the two documents that did not map directly onto a stated role — 05 and 08 — are assigned with reasoning in section 2. Section 6 sets out proposed availability worked back from the 14 August delivery date.

## 1. Role allocation

| Member | Function | Owns end to end | Reviews and supports |
|---|---|---|---|
| Kuldeep | Team lead, product owner, market research, final reviewer | Documents 00, 04, 05 and 10. Scope decisions, the control charter, the business model. Joint owner of market research with Mayank. | Final sign-off on every deliverable. Arbitrates scope disputes. Directs Q&A. |
| Mayank | Market research, human and AI validation, software implementation | Documents 01, 02 and 03. The customer-interview programme. Source register. Joint owner of market research with Kuldeep. | Second reviewer on 05 pricing evidence. Software contributor to the POC. |
| Kapil | Hardware and software implementation and integration | Document 06. Camera, edge device and network integration. GitHub repository ownership. | Reviews 07 technical classification. Delivers the live demo. |
| Kamal | Hardware and software implementation and integration | Document 07. Model selection, detection pipeline and evaluation approach. | Joint integration work with Kapil. Reviews 06 feasibility against real capacity. |
| Yashpal | Testing, edge cases and failure modes | Document 08. The edge-case test plan and the source verification log. | Reviews 06 exclusions. Q&A owner for limitations and failure modes. |

## 2. Ownership of documents 05 and 08

Two deliverables do not map directly onto any stated role. Rather than leaving them to be picked up implicitly, both are assigned here with reasoning.

#### 2.1 Document 05 — Business Model

Assigned to Kuldeep, with Mayank as second reviewer on the pricing and market evidence. The reasoning is that business model is a product-ownership question rather than a research or build question, and it sits naturally with the person holding scope authority. It also matters that the team lead owns substantive deliverables and not only review duties — a lead whose contribution record shows sign-off but no authored work reads poorly to an assessor, however much work the reviewing actually was.

#### 2.2 Document 08 — AI Output vs Human Corrections

Assigned to Yashpal, and this is a better fit than it first appears. Document 08 is fundamentally a verification exercise: opening each source, confirming each figure, and recording what was rejected and why. That is the same disciplined, adversarial mindset that edge-case testing requires — the habit of asking where does this break rather than does this work. The person testing the product for failure modes is the right person auditing the research for unsupported claims.

#### 2.3 Sequencing note on the research and software split

Market research is jointly owned by Kuldeep and Mayank, which distributes what would otherwise be an uneven load. Mayank still spans validation and software implementation, so the recommendation is to sequence rather than parallelise: research and validation in the first half of the period, moving to software implementation in the second once Kapil and Kamal have the integration layer stable enough for a third contributor to be productive. Context-switching between interview work and code work within the same day is costly, and the phasing in section 6 is built around avoiding it.

## 3. Hardware scope — a necessary clarification

Kapil and Kamal are assigned hardware implementation and integration. Document 06 excludes custom IoT and purpose-built camera hardware from the POC. These are not in conflict, but the distinction must be explicit so that neither document is read as contradicting the other.

| In scope for hardware work | Excluded |
|---|---|
| Camera integration — connecting a webcam or an existing IP camera over RTSP or ONVIF. | Designing or fabricating a camera. |
| Edge device setup — provisioning and configuring an edge compute unit to run inference locally. | Designing a custom edge board or enclosure. |
| Network and stream handling — bandwidth, latency, reconnection and stream stability. | Custom networking hardware. |
| Physical positioning tests — height, angle, distance and lighting, feeding the camera audit. | Permanent installation work at a customer site. |
| Benchmarking inference throughput on the chosen device. | Any claim of production hardware cost before Indian distributor quotes are obtained. |

The one-line version: the team integrates hardware, it does not build hardware. The product premise is that customers use cameras they already own, and building hardware would contradict that premise.

## 4. Yashpal's edge-case test plan

Edge-case testing is unusually important in this product, for a structural reason. Because every candidate event must be reviewed by a human, each false positive consumes reviewer time by construction. A failure rate that a dashboard-only competitor could tolerate may be fatal here. Testing is therefore not a quality function bolted on at the end — it tests the metric that decides whether the design survives.

The test matrix below is derived from failure modes documented in the peer-reviewed literature rather than invented, which makes it defensible in review.

| # | Condition to test | Basis in the literature | What a failure would mean |
|---|---|---|---|
| T1 | Occlusion — worker partially hidden by equipment or another worker | Detection accuracy degrades under variable illumination, occlusion and worker clustering; systematic reviews name occlusion as a leading unresolved challenge. | Missed events in exactly the crowded areas where risk concentrates. |
| T2 | Congested scene with overlapping workers | Indian sites are described as more labour-intensive and congested, producing occlusions and overlapping frames. | The India-specific failure mode. Highest priority for this market. |
| T3 | Variable and poor lighting | Illumination change is repeatedly identified as a source of real-world performance variability. | Shift-dependent reliability — the system works by day and fails at night. |
| T4 | PPE colour variation | Prediction suffers from colour mismatching in the Indian construction study. | Site-specific failure whenever helmet colour differs from training data. |
| T5 | Viewing angle, camera height and distance | Optimal camera positioning, resolution and distance are named open research questions. | Feeds directly into the camera audit and the deployment feasibility test. |
| T6 | Face blurring enabled | Helmet-class accuracy on blurred faces decreased by 7%; person and vest classes unaffected. | Quantifies the cost of the privacy control the product commits to. |
| T7 | Semantic ambiguity — helmet carried, not worn | Object detection captures presence, not meaning; a model may identify an object without distinguishing whether the situation is hazardous. | The most credible false-positive source, and the case for the triage layer in document 07. |
| T8 | Class difficulty comparison | Non-helmet exceeds 92% accuracy; non-shoes falls to roughly 83.5%. | Confirms or challenges the choice of helmet for the POC. |
| T9 | Reviewer load under sustained volume | The design converts every error into reviewer labour. | Establishes the abandonment threshold — the point at which a reviewer stops using the system. |

> **T9 is the most valuable test the team can run.** Every competitor can quote a detection accuracy figure. Almost none reports how many events a human must adjudicate per shift. Because Guardian Lens's differentiator is the human gate, the number of events per reviewer per shift is the metric that determines whether the product is usable — and measuring it in the POC would be a genuinely distinctive result to present.

## 5. Work packages

| # | Work package | Owner | Output |
|---|---|---|---|
| W1 | Source verification log | Yashpal | Document 08 sections 6 and 7 fully populated with names and dates. |
| W2 | ASI filtering, steps 2 and 3 | Mayank | PPE-relevant NIC codes and employment-size bands from published ASI tables. Free, and closes two named unknowns. |
| W2b | Apply corrections to document 02 | Mayank | Four corrections identified in document 08 section 5.2: Visionify pricing, the superseded brief, the market-sizing gap, and four missing competitors. |
| W3 | Buyer interview programme | Mayank and Kuldeep | 5-8 interviews at Factories Act-registered sites. The guide must ask about current practice before the product is mentioned. |
| W4 | Physical camera audit and NVR capability check | Kapil, with Kamal | Camera count, position, height, angle, resolution and network access at 3+ sites. Also record NVR make, model and whether AcuSense, IVS or equivalent analytics are present and licensed — this determines whether the integration-layer position is viable at each site. |
| W5 | POC build — review workflow first | Kapil, Kamal | Human review interface and verified event log against stubbed detections, before any detector work begins. |
| W6 | POC build — detector | Kamal, with Mayank | Single-class helmet detection on selected recorded footage. |
| W7 | Edge-case test execution | Yashpal | Results against T1-T9, including the reviewer-load figure. |
| W8 | Integrator conversations | Kuldeep | 2-3 CCTV integrator discussions. Highest-leverage acquisition channel per document 05. |
| W9 | Presentation build and rehearsal | Kuldeep, all | Seven-minute deck rehearsed against a clock, with Q&A preparation. |

> **Sequencing instruction that matters more than any other in this document.** W5 precedes W6. Build the human review interface and the verified event log against fake detections before building the detector. The detector can be improved until the final day; the review workflow cannot be added at the end. A POC with a crude detector and a working human gate demonstrates Guardian Lens. A POC with an excellent detector and no human gate demonstrates a competitor's product.

## 6. Availability and phasing

Worked back from the 14 August delivery date. At the 20 July research cut-off this leaves three and a half weeks: three full weeks plus a four-day final week.

> **These are proposed figures, not measured ones.** They describe the shape of commitment the plan requires, not hours anyone has confirmed. Each member should replace their row with a realistic number before this document is submitted. If the totals cannot be met, the correct response is to cut scope — starting with the optional features in document 06 — rather than to compress the plan and miss the date.

#### 6.1 Proposed weekly hours

| Member | W1 21-27 Jul | W2 28 Jul-3 Aug | W3 4-10 Aug | W4 11-14 Aug | Total | Peak |
|---|---|---|---|---|---|---|
| Kuldeep | 14 | 12 | 10 | 16 | 52 | W4 |
| Mayank | 16 | 18 | 16 | 14 | 64 | W2 |
| Kapil | 12 | 16 | 20 | 18 | 66 | W3 |
| Kamal | 12 | 16 | 20 | 18 | 66 | W3 |
| Yashpal | 10 | 10 | 14 | 16 | 50 | W4 |
| Team total | 64 | 72 | 80 | 82 | 298 | — |

*Approximately 15 to 19 hours per person per week on average, rising in the final fortnight. W4 is four days, so its figures represent a heavier daily rate than the weekly total suggests.*

#### 6.2 Why the phasing is shaped this way

| Member | Phasing rationale |
|---|---|
| Kuldeep | Front-loaded on scope and market research, dips through the build weeks, rises sharply in W4 for final review of every deliverable and presentation rehearsal. A final reviewer who is busy in the final week is a bottleneck, so W4 capacity is protected deliberately. |
| Mayank | Peaks in W2 when customer interviews run, then steps down as he moves from research and validation into software implementation. This is the sequencing described in section 2.3 — research first, code second, not both in the same day. |
| Kapil | Builds through W2 to W4 with the camera audit in W2. Peak in W3 because the review workflow and the integration layer must both be stable before the final week. |
| Kamal | Mirrors Kapil. Detection pipeline work concentrates in W3 once the review workflow exists to receive its output. |
| Yashpal | The only member whose work can start immediately and independently: the source verification log needs no product. Front-load it in W1 and W2, then rise through W3 and W4 as builds land and edge-case testing becomes possible. |

> **The scheduling insight worth acting on.** Verification work (W1) requires no product and can be completed before any code exists. Testing (W7) requires builds and cannot start early. Yashpal should therefore finish the verification log in the first fortnight, while the build team is still working, rather than leaving both tasks to collide in the final week. This is the difference between a completed audit trail and fifteen empty boxes at submission.

#### 6.3 Milestones

| Date | Milestone | Condition for being on track |
|---|---|---|
| 27 Jul (end W1) | Research and setup complete | Verification log substantially complete; ASI filtering done; repository live; interview guide written; camera audit scheduled. |
| 3 Aug (end W2) | Evidence gathered | Buyer interviews conducted; camera audit complete at 3+ sites; review workflow running against stubbed detections. |
| 10 Aug (end W3) | Feature complete | All seven must-have features working end to end. Detector integrated. Edge-case testing underway. |
| 13 Aug | Freeze and rehearse | No new features. Test results recorded. Presentation rehearsed against a clock. |
| 14 Aug | Delivery | POC demonstrated; all documents submitted with verification log signed off. |

> **The W3 gate is the one that matters.** If the seven must-have features are not working end to end by 10 August, cut the optional features in document 06 immediately rather than attempting both. A complete narrow demonstration beats an incomplete broad one, and the central claim — candidate event, human review, auditable record — needs every one of the seven to hold together.

## 7. Claude Max allocation

Anthropic states that the Max plan provides 5x or 20x the usage of Pro per five-hour session, with higher output limits, billed monthly. Usage limits reset on a rolling five-hour session window, paid plans add weekly limits on top, and activity across Claude on web, desktop, mobile and Claude Code all draws from the same pool. Anthropic explicitly does not publish a fixed message count, stating that capacity depends on the length and complexity of conversations, the model chosen and the features used.

> **Two consequences to plan around.** Because no message count is published, allocation cannot be managed by counting messages — it must be managed by scheduling session windows. And Max is an individual plan, so five people cannot share one account; the team should confirm the correct licensing arrangement at claude.com/pricing before assuming otherwise, with the Team plan being the relevant product if a shared arrangement is needed.

| Member | Primary usage | Scheduling note |
|---|---|---|
| Kuldeep | Document drafting, scope reasoning, market research, business model, presentation | Heaviest in W1 and W4. Should hold the highest tier if tiers differ across the team. |
| Mayank | Research and source discovery, then Claude Code for software work | The only member whose usage pattern changes mid-project. Long research conversations with search consume capacity quickly; plan for higher usage during the research phase. |
| Kapil | Claude Code for integration and the review interface | Sustained build sessions. Claude Code and chat draw from the same pool. |
| Kamal | Claude Code for the detection pipeline and model evaluation | Sustained build sessions in the same period as Kapil. |
| Yashpal | Verification work, test design, edge-case analysis | Lighter and more intermittent, rising sharply during the test window. |

> **Capacity risk specific to this team.** Three people — Kapil, Kamal and Mayank — will be running build sessions in the final week, not two. If capacity is constrained, stagger their five-hour windows rather than allowing all three to open sessions simultaneously, and keep Yashpal's test runs outside those windows. Confirm current plan details at claude.com/pricing and support.claude.com before committing, as plans change.

## 8. GitHub contribution evidence

> **Handles are collected by Kuldeep; evidence accumulates as work proceeds.** Contribution evidence is generated by working, not by planning, so the right-hand columns fill in over the three and a half weeks. What can be done immediately is collecting the five handles and creating the repository — both are W1 tasks and both are prerequisites for anything else in this section being measurable.

| Member | GitHub handle | Commits | Areas owned in the repository | PRs reviewed |
|---|---|---|---|---|
| Kuldeep | [ ] | [ ] | Documents, scope decisions, presentation | [ ] |
| Mayank | [ ] | [ ] | Research artefacts, interview notes, software modules | [ ] |
| Kapil | [ ] | [ ] | Integration layer, review interface, repo administration | [ ] |
| Kamal | [ ] | [ ] | Detection pipeline, model evaluation | [ ] |
| Yashpal | [ ] | [ ] | Test plan, test results, verification log | [ ] |

#### 8.1 Practices that make contribution visible

1. Every member commits under their own account. No shared accounts, and no commits pushed on another member's behalf.
1. Non-code work is committed too. Documents, the interview guide, interview notes, the camera audit, the test matrix and the verification log all belong in the repository. This is the mechanism by which research, validation and testing become visible contribution rather than invisible effort.
1. Feature branches with pull requests, and at least one reviewer per pull request. Review comments are contribution evidence in their own right.
1. Commit messages reference the work package, W1 to W9, so activity maps to the plan.
1. Test results are committed as they are produced. A test that found nothing is still evidence that the test was run.

> **The specific distribution risk for this team.** With Kapil, Kamal and Mayank all writing code, commit history will concentrate in three people, and Kuldeep and Yashpal will appear underweight on a raw commit count. Committing documents, interview notes, the verification log and test results to the same repository is the single most effective correction, and it costs nothing. Yashpal in particular should commit test artefacts continuously rather than reporting results at the end.

## 9. Presentation responsibility

| Member | Presentation role | Rationale |
|---|---|---|
| Kuldeep | Primary presenter — problem, scope, vision, business model, ask. | Seven minutes does not accommodate five speakers. Hand-offs consume time and break the narrative. |
| Kapil | Live demonstration, approximately 90 seconds. | Built the integration and can answer questions about it under pressure. |
| Mayank | Q&A owner — market, sizing, competitors, sources, validation status. | Owns 01 and 03 and holds the source register. |
| Kamal | Q&A owner — models, accuracy, agentic architecture, technical feasibility. | Owns 07 and the detection pipeline. |
| Yashpal | Q&A owner — limitations, failure modes, test results, verification process. | Owns 08 and the edge-case testing. The most credible person in the room to answer what does not work. |

All five attend the Q&A. Kuldeep directs each question to its owner rather than answering everything, which demonstrates distributed ownership far more convincingly than splitting the seven-minute presentation five ways.

> **Yashpal has the most valuable Q&A role in the room.** The hardest questions in a founder review are about what does not work. Having a named person who tested for failure modes and can answer with specific results — rather than the lead deflecting — is unusually strong. Prepare him to answer the reviewer-load question in particular, because that number is the one no competitor publishes.

## 10. Distribution check

| Member | Docs owned | Work packages | Build or delivery role | Q&A area | Repo output |
|---|---|---|---|---|---|
| Kuldeep | 00, 04, 05, 10 | W3, W8, W9 | Product owner, presenter, final reviewer | Vision, scope, business | Docs |
| Mayank | 01, 02, 03 | W2, W2b, W3, W6 | Research, validation, software | Market, validation, competitors | Research and code |
| Kapil | 06 | W4, W5 | Integration lead, demo | Demo, deployment | Code |
| Kamal | 07 | W4, W5, W6 | Detection pipeline | Technical, models | Code |
| Yashpal | 08 | W1, W7 | Testing and verification | Limitations, failures | Tests and log |

Every member owns at least one document, at least two work packages, and one Q&A area. Three carry build work; one carries research and validation alongside build; one carries testing and verification; the lead carries product, business model and delivery.

> **The test that actually matters.** If any member reaches the end of the period with no artefact committed under their own name, the distribution has failed regardless of what this table claims. Check this at the halfway point, not at submission, when there is still time to correct it.
