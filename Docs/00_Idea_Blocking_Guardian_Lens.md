# 00 — Idea Blocking

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 00 — Idea Blocking (Week 1 deliverable) |
| Product name | Guardian Lens (single name used throughout; "SafeProof AI" is retired) |
| Research cut-off | 20 July 2026 |
| POC target date | 14 August 2026 |
| Geographic scope | India — registered manufacturing and warehousing sites |
| Evidence rule | Every statement is a verified fact, a labelled vendor claim, a transparent calculation, or an explicit unknown |

> **Evidence discipline.** This document does not invent a safety-specific market size, a Guardian Lens ROI figure, customer demand, pricing, or model accuracy. Where reliable public evidence could not be located, the document says so rather than estimating. Vendor marketing is labelled as vendor marketing and is never treated as independent proof of an outcome.

> **Scope note.** Section 3 states the full product vision and roadmap. Sections 4 onward define the narrower Week 1 approval scope. The difference between them is deliberate sequencing on the basis of available evidence, not a limit on the product. Guardian Lens performs no productivity or worker-activity monitoring at any horizon.

## 1. Decision requested

Approve the following problem statement for limited product analysis and a scoped proof of concept. This is not a request to approve full development or any commercial claim.

> **Problem statement.** Manufacturing and warehouse safety teams cannot continuously observe every camera feed they already own. Visually detectable safety-rule exceptions — initially missing required PPE and entry into configured restricted zones — are therefore identified inconsistently, late, or only during post-incident footage review. Guardian Lens analyses compatible existing camera feeds, produces candidate safety events, and requires an authorised human to accept, reject, or correct each event before it enters a formal record or triggers any follow-up.

This wording defines a testable problem and a testable response. It does not assert that Guardian Lens prevents incidents, has customers, or has demonstrated accuracy. None of those things is true yet.

## 2. Final domain

| Dimension | Definition |
|---|---|
| Primary domain | Occupational safety and health (OSH) technology |
| Product category | AI video analytics / computer vision for environmental, health and safety (EHS) workflows |
| Delivery model | Software layer over existing CCTV/IP cameras, with local or edge inference |
| Initial use cases | PPE-rule detection using an own model, and restricted-zone entry consumed from existing NVR analytics where present (see section 3.3) |
| Long-term product vision | A configurable safety-event platform on existing cameras, with operator-defined rules and mandatory human verification (see section 3) |
| Not the domain | Workforce productivity or activity monitoring, security/crime detection, consumer surveillance |

## 3. Product vision and roadmap horizons

Guardian Lens is intended to become a configurable safety-event platform: a layer over a site's existing cameras on which an operator can define the visually detectable safety rules that matter at that site, and have every candidate event pass through human verification before it becomes a record.

That is the destination. Week 1 approval and the August proof of concept are deliberately narrower than the destination, and the two are not in conflict. Approval is granted on evidence, and evidence currently exists for two use cases. The horizons below make the sequencing explicit so that a narrow Week 1 scope is not mistaken for a narrow product.

| Horizon | Timing | Contents | Gate to enter |
|---|---|---|---|
| H0 — Proof of concept | By 14 August 2026 | One detection class on one feed; human accept / reject / correct; event history; basic report. | None. Demonstrates workflow only, not accuracy. |
| H1 — Week 1 approval scope | Post-POC, pilot stage | PPE-rule detection (own model). Restricted-zone entry integrated from existing NVR analytics rather than detected independently. | Buyer validation, camera-feasibility test, and a technical test of NVR event integration. |
| H2 — Validated expansion | After a completed pilot | Man-Down / Possible-Collapse Detection. Phone use inside a designated hazardous zone, where a written site rule exists. | Separate feasibility validation per event type, on real site footage. |
| H3 — Configurable platform | Long term | Operator-defined safety rules; unsafe proximity to machinery, vehicles and stairs; multi-site aggregation; broader industry coverage. | Demonstrated configuration repeatability across sites without bespoke engineering. |

> **Why breadth is sequenced rather than parallel.** Each additional event type multiplies site-specific tuning work, and the mandatory human-verification design means every false positive consumes reviewer time by construction. Breadth costs more for this architecture than for a product that simply fires alerts into a dashboard. That is an argument for ordering the roadmap, not for shrinking it.

#### 3.1 The hardware layer — a scope decision, not a concession

Mainstream CCTV hardware that target customers already own now ships with on-device analytics. Hikvision AcuSense embeds deep-learning algorithms into selected cameras and video recorders, classifies objects as human, vehicle or other, and provides region entrance detection which detects people entering a predefined restricted zone, configurable at either the camera or the recorder. Hikvision markets this as available at only a small incremental cost. Dahua IVS provides comparable line-crossing, intrusion and abandoned-object detection, with classification running on a dedicated on-camera neural chip.

> **Consequence, stated plainly.** Restricted-zone entry is substantially addressable using firmware many target customers have already paid for. Selling it as a headline capability invites an immediate and damaging objection from any buyer who knows their own equipment. Guardian Lens therefore does not compete with the NVR on zone detection.

The decision taken is to reposition restricted-zone entry as an integration feature. Where a site already runs NVR analytics, Guardian Lens consumes those zone events, routes them through the same mandatory human verification, and writes them into the same audit trail alongside PPE events. Where a site has no such analytics, Guardian Lens can generate the zone event itself, but this is a fallback rather than the proposition.

| Layer | Position |
|---|---|
| Detection of zone entry | Owned by the customer's existing NVR where present. Guardian Lens does not duplicate it. |
| Detection of PPE compliance | Owned by Guardian Lens. This is the differentiated detection and the H1 headline. |
| Verification | Owned by Guardian Lens. Every event from either source passes through the same human gate. |
| Unified record and audit trail | Owned by Guardian Lens. One record spanning both sources, with reviewer decision attached. |
| Reporting and trend analysis | Owned by Guardian Lens. |

> **Why this is a stronger position than the original scope.** A product that competes with embedded camera firmware loses on price and distribution. A product that sits above it and makes its output verifiable and auditable is complementary to hardware the customer already trusts, and becomes more valuable as on-device analytics improve rather than less. The commoditisation of detection is a threat to a detection company and an asset to a verification company.

> **Unvalidated technical dependency.** This position assumes Guardian Lens can reliably receive alarm events from common NVRs — via ONVIF, vendor APIs or HTTP alarm callbacks. That integration path has not been tested. It is now a required item in the feasibility work, and it should be tested during the camera audit rather than assumed.

#### 3.2 Man-Down / Possible-Collapse Detection — definition and boundary

> **Definition.** A person detected in a prone or collapsed posture who remains motionless beyond a configured time threshold, within a monitored area. The event signals a possible medical emergency or injury requiring response. It is a lone-worker and emergency-response capability.

This capability is in the product scope and sits in Horizon 2. It is not in the Week 1 approval scope and it is not in the proof of concept, because its feasibility must be validated separately before it can be promised.

**It must never be described as, or implemented as, inactivity or idle-time detection.** The distinction is not cosmetic and it is not a matter of wording alone — it is a difference in what the system is built to detect. A prone, motionless posture is a safety signal. A person standing still at a workstation, moving slowly, taking a break, or producing less output is not a safety signal and must not generate an event. Guardian Lens does not detect, score, rank or report on worker activity levels, presence at a station, or productivity in any form. Any implementation that could produce such an output is out of scope by design, not by policy.

#### 3.3 Evidence that man-down is an established safety category

This is not a novel or speculative capability. Multiple vendors publish it as a distinct safety product on existing camera infrastructure:

| Vendor | Published position |
|---|---|
| Visionify | Operates dedicated Person Down and Slip & Fall use cases, described as AI detecting when a person has fallen and remains immobile, with alerts for lone workers, working over existing IP camera systems including VMS and NVR setups via RTSP. |
| IntelliSee | States that it detects person-down events rather than individual identities, uses no facial recognition, collects no PHI and stores no video, processing locally on an on-premises appliance connected to existing ONVIF and RTSP cameras. |
| Mikshi AI (India) | Markets slip-and-fall and man-down detection in real time using existing CCTV across factories, warehouses and construction, with visual incident evidence and audit-ready reports, deployable on-premises or cloud. |
| Hanwha Vision | Published a slip-and-fall detection white paper in January 2026 positioning automated detection as support for prompt emergency response obligations, and referencing ISO 45001's emphasis on continuous monitoring. |

> **Why this stays out of the POC.** Hanwha Vision's own installation guidance documents a material limitation: slip-and-fall detection cannot be guaranteed when a walking person is not detected for more than three seconds, or when the person is blocked by another person. Occlusion and tracking continuity are exactly the conditions a real factory floor produces constantly. A capability whose leading vendors publish these caveats cannot be responsibly demonstrated on a single webcam in three and a half weeks. It requires its own labelled test footage and its own feasibility gate — which is what Horizon 2 provides.

The IntelliSee position is also the design precedent Guardian Lens should follow: detecting a person-down posture without identifying the person is compatible with the non-biometric, minimal-retention posture set out in section 4.

## 4. Scope boundaries

Scope discipline is the core of this product, not a compliance afterthought. Every capability below was assessed against one test: can a reasonable worker representative read this scope and accept that the system is a safety control rather than a monitoring tool?

#### 4.1 In scope

1. Industrial and warehouse sites with documented, written PPE or restricted-zone rules
1. Existing compatible CCTV/IP camera feeds (RTSP/ONVIF), or a single webcam for the proof of concept
1. Candidate-event generation for missing required PPE within a defined area
1. Restricted-zone entry consumed from existing NVR analytics where present, or generated by Guardian Lens as a fallback where not
1. Mandatory human accept / reject / correct decision before any event is recorded as verified
1. Verified event log, audit trail, and aggregated trend reporting

#### 4.2 Explicitly out of scope

| Excluded | Reason for exclusion |
|---|---|
| Productivity or activity monitoring of any kind — idle time, time at station, work rate, output, attendance scoring | Guardian Lens does not detect, measure, score, rank or report on how hard, how fast or how continuously any worker is working. This is not a policy choice layered on top of a capable system; the system is not built to produce these outputs. Note the deliberate distinction from Man-Down / Possible-Collapse Detection defined in section 3.2, which detects a prone motionless posture as an emergency signal and is not an activity measure. |
| General phone-use monitoring | Retained only in the narrowed Horizon 2 form: phone use inside a designated hazardous zone where a written site rule exists. Anywhere else, phone-use detection is behaviour monitoring and is excluded. |
| Facial recognition, identity matching, emotion or biometric classification | Creates identifiability and DPDP exposure without serving either initial use case. |
| Audio capture | No safety use case in the defined scope. |
| Automatic disciplinary action, performance scoring, or worker ranking | The system produces reviewable evidence, not decisions about individuals. |
| Any claim that the product replaces supervisors, training, risk assessment, guarding, barriers, or PPE itself | Guardian Lens is an observation aid layered on top of existing controls. It is not a control. |
| Office/desk monitoring, crime detection, consumer home surveillance | Different domain, different buyer, different regulatory posture. |

#### 4.3 In the product, but not in the Week 1 approval scope

These capabilities are part of the product vision and appear in the roadmap horizons in section 3. They are excluded from the Week 1 blocking decision and from the proof of concept because each carries a distinct feasibility, data or market condition that must be satisfied first. Excluding them from approval is a sequencing decision, not a rejection.

| Capability | Horizon | Condition to be satisfied before it enters scope |
|---|---|---|
| Man-Down / Possible-Collapse Detection | H2 | Separate feasibility validation on real site footage. Vendor-published guidance in this category documents degraded performance under occlusion and interrupted tracking, both of which are routine on a factory floor. See section 3.3. |
| Phone use inside a designated hazardous zone | H2 | A customer must produce a written rule prohibiting phone use in a specific mapped area. Detection is of object and location only, never screen content. Without the written rule this is monitoring, not compliance. |
| Unsafe proximity to machinery, vehicles or stairs | H3 | Requires depth or calibrated geometry rather than a single flat camera view. Materially harder than PPE or zone detection and must not be promised alongside them as if equivalent. |
| Construction sites | H3 | Different buyer, frequently no permanent camera infrastructure, high site churn. Revisit after the fixed-site beachhead is validated. |
| Hospitals and laboratories | H3 | Video of patients or clinical areas raises a materially higher data-protection burden. Not a first market, notwithstanding that man-down detection has clear clinical demand. |

## 5. Target customer, user and buyer

> These are proposed target definitions derived from the product scope. None has been validated against a real Indian buyer. Treat every line in this section as a hypothesis to be tested in customer discovery.

#### 5.1 Beachhead customer (one segment, not six)

The original concept listed six verticals. Six verticals is not a beachhead; it is a wish list, and it makes the POC unfocused and the market research unfalsifiable. The single Week 1 beachhead is:

> A small or medium Indian manufacturing plant or warehouse, registered under the Factories Act, that already operates IP CCTV covering a PPE-controlled or restricted area, and has a named person accountable for EHS or plant operations.

The site must additionally satisfy five conditions, none of which can be assumed:

- Compatible IP cameras (RTSP/ONVIF) already installed and positioned to view the relevant area
- An explicit, written safety rule that can be represented visually
- A named EHS, operations or facility-safety owner
- Legal and organisational ability to run transparent video processing, including worker communication
- Enough observation or review pain to justify evaluating a pilot

#### 5.2 Sizing the customer base — a correction

> **Correction to earlier draft.** An earlier version of this research used MSME registration data as the customer-base proxy. That was the wrong denominator and it overstated the addressable population by roughly forty-five times. It has been replaced.

The Ministry of MSME reports that as on 31 December 2024 a total of 5,77,03,550 MSMEs were registered including informal micro enterprises on the Udyam Assist Platform, of which 1,17,53,385 were registered in the manufacturing category. This is a registration count, not a site count. Udyam data also shows that the investment value of roughly 97% of registered MSMEs is below Rs. 50 lakh — overwhelmingly micro units with no CCTV, no EHS function and no IT administrator. Multiplying that number by any adoption rate would be meaningless.

The defensible proxy is the Annual Survey of Industries, which covers factories registered under sections 2m(i) and 2m(ii) of the Factories Act, 1948 — broadly, premises with ten or more workers using power. The ASI 2023-24 live frame contained 2,61,818 units. Roughly 2.6 lakh registered factories is the outer boundary of the population that plausibly has a statutory safety function and an existing camera estate. It remains an outer boundary, not a market.

#### 5.3 User, buyer and deployment stakeholders

| Role | Who |
|---|---|
| Daily user | EHS or safety officer; shift or floor supervisor |
| Economic buyer (hypothesis) | Plant head or factory owner; operations head; EHS/safety head. The actual budget owner is an open customer-discovery question. |
| Deployment stakeholders | IT/network administrator; CCTV or security-system integrator; HR/legal or privacy representative; worker representatives where a union or works committee exists |
| Protected party | Workers on the floor. They are not the customer and not the subject of evaluation. |

## 6. Current process

There is no single universal safety-observation process across Indian factories, and no public dataset describes one. This section therefore presents a process model to validate in interviews, not a measured finding.

- The employer defines safety responsibilities, risk controls, training, signage, equipment and site rules.
- Supervisors or safety staff carry out periodic observations, inspections and checks.
- Existing CCTV provides live views or recorded footage, generally used reactively.
- Observations, near misses and incidents are recorded through whatever system the site already uses — often paper or spreadsheet.
- Staff investigate, communicate and record corrective action.

With the Occupational Safety, Health and Working Conditions Code, 2020 now in force, employer duties in India rest on that Code rather than on the Factories Act, 1948 framework it replaces. Earlier drafts of this research cited UK HSE guidance as the process anchor; that has been replaced with the applicable Indian instrument. The claim that camera monitoring is periodic or incomplete originates mainly in safety-CV vendor material and must be treated as a category claim, not a neutral measurement.

## 7. The exact pain being tested

Guardian Lens is not attempting to address "workplace accidents" in general. The narrow operational pain under test is:

1. A human cannot continuously watch all relevant camera feeds during a shift.
1. Periodic inspection is, by definition, not continuous observation.
1. Recorded CCTV is useful after an event but does not automatically produce a structured safety record.
1. Manual review consumes supervisor attention and is inconsistent between reviewers and shifts.
1. Without structured, verified events, teams lack consistent data on which rule exceptions recur, where, and on which shift.

Only the last point is genuinely differentiating. The first four are the standard category pitch used by every vendor in this space and should not be presented as a Guardian Lens insight.

## 8. Evidence that the underlying problem exists

#### 8.1 Global scale (context only)

The ILO estimates, for reference year 2019, that around 2.93 million workers die each year from work-related causes and that over 395 million workers sustain a non-fatal work injury each year — the injury figure counting injuries causing at least four days of absence. Of the fatalities, approximately 2.6 million are attributed to work-related disease and around 330,000 to occupational accidents. The Asia-Pacific region accounts for almost 63% of global work-related deaths.

> These totals must never be used as Guardian Lens's addressable impact. The overwhelming majority are disease-related and invisible to a camera. Only visible rule exceptions within adequate camera coverage are relevant to this product, and no source quantifies that subset.

#### 8.2 India-specific harm data

Two Indian government sources exist, and they disagree:

| Source | Finding | Limitation |
|---|---|---|
| NCRB (Accidental Deaths and Suicides in India) | India recorded 1,586 factory and machine accidents in 2010, falling to 742 by 2024; deaths fell from 1,043 to 660 over the same period. | Police-reported. Captures only accidents that reach a police record. |
| DGFASLI, Ministry of Labour and Employment | An average of 1,109 deaths and more than 4,000 injuries per year in registered factories over 2017-2020, obtained via RTI by IndiaSpend. | Compiled from state chief inspectors of factories. Covers registered factories only; excludes the informal sector. |

The roughly 40% divergence between these two official series is itself a finding. India has no reliable, routinely published workplace-injury denominator. That cuts both ways for Guardian Lens: it strengthens the case for a structured, verified event record, and it simultaneously removes any basis for computing avoided-incident value.

#### 8.3 Commercial evidence that organisations buy this category

1. Multiple established vendors sell PPE and restricted-area analysis over existing camera infrastructure, including Intenseye, Protex AI, Voxel and Visionify.
1. Named customer deployments are published by those vendors — including Voxel with NSG Group, and Intenseye with Coats at its Madurai New Mill facility in India.
1. Indian domestic vendors offer the same capability set to Indian industrial buyers (see section 9).

> **Correction.** The Intenseye Coats case is frequently cited as India-based evidence for PPE and zone detection. It is not. The published outcome concerns vehicle speeding at the facility — a 20% reduction in speeding detections in the first week, rising to over 50% reduction in speeding incidents. It is evidence of category adoption in India. It is not evidence for either of Guardian Lens's two initial use cases, and it is a vendor-published figure, not independent research.

## 9. Business, operational and compliance impact

#### 9.1 What can be supported

| Category | Supportable statement |
|---|---|
| Operational | Established products in this category generate structured alerts and event records from existing video streams. This is a demonstrated product capability, not a Guardian Lens result. |
| Safety management | Verified event data may help safety teams identify repeated rule exceptions and target review effort. This benefit is plausible and must be measured during a pilot; it is currently unproven. |
| Compliance / governance | Employers carry statutory OSH duties in India under the OSH Code, and video processing that identifies individuals may create data-protection obligations. Both are real; their exact application requires legal review. |
| Financial | Injuries and downtime carry financial consequences, but no reliable Indian SME cost-per-visible-event figure was located. No monetary saving is assigned to Guardian Lens anywhere in this document. |

#### 9.2 What is not established

1. Guardian Lens has demonstrated no incident reduction of any kind.
1. No Guardian Lens ROI, willingness-to-pay, false-positive rate or time-saving figure exists.
1. Vendor-reported reductions from Voxel, Intenseye or Protex cannot be transferred to Guardian Lens under any framing.
1. No accuracy claim can be made for Indian factory conditions. Peer-reviewed work on Indian construction sites exists and is summarised in document 03 section 3.3; it documents congestion, occlusion and colour mismatching as specific difficulties. No study of Indian factory-floor conditions was located, and construction findings are indicative rather than transferable.

## 10. Competitive reality check

> This section did not exist in the earlier draft and is the most significant change to the blocking decision.

The full worldwide landscape is documented in companion document 02 — Competitive Research. Summarised here are the three findings that bear directly on the blocking decision.

#### 10.1 The field is funded and global

Intenseye has raised USD 94.4 million across four rounds, including a USD 64 million Series B in February 2024 led by Lightspeed Venture Partners. Protex AI raised USD 36 million in a Series B in January 2025. CompScience raised USD 27.6 million in February 2025, bundling safety monitoring with workers' compensation insurance. Voxel, viAct, Buddywise, Surveily and Invigilo are also active internationally.

#### 10.2 Indian domestic vendors already sell this capability

| Vendor | Publicly stated offering |
|---|---|
| Staqu Technologies (JARVIS) | Deployed at a primary steel plant monitoring 2,000 workers for PPE and safety compliance; real-time PPE detection, fire and smoke identification and perimeter security on existing camera infrastructure with no hardware replacement. |
| Agrex AI | India-focused edge AI for production-floor intelligence including PPE and safety compliance monitoring, integrating with existing CCTV. |
| AllGoVision, Uncanny Vision, Videonetics | Established Indian video-analytics suites including PPE, intrusion and fire detection modules. |
| Tentosoft and similar | PPE detection over existing CCTV via RTSP, marketed with audit-ready reports aligned to the Factories Act, 1948. |
| Visionify (US) | Already lists Indian industrial groups among its customers, including Godrej, Adani, Hindware and Premier Energies. Sells a $3,000 one-time PPE starter kit covering up to ten cameras with three months of subscription and a Mac Mini M4 edge server. |

#### 10.3 The threat from below

Commoditisation pressure comes from two directions at once. Above, funded platforms cover breadth of detection. Below, the camera hardware customers already own increasingly ships with on-device AI covering intrusion and zone logic, as set out in section 3.1. Separately, PPE and helmet detection is a thoroughly solved research problem with published implementations on Faster R-CNN and successive YOLO generations, including documented implementations running on low-cost edge hardware. A competent engineering team can reproduce the core detector from freely published papers.

> **Consequence for the idea.** Detection capability is not available as a differentiator from any direction. Funded platforms cover it above, Indian vendors cover it locally, published research commoditises it technically, and camera firmware covers zone logic from below. Guardian Lens cannot be blocked on detection. If it has a defensible position it is the mandatory human-verification gate, the resulting audit trail, and a transparent commercial model — and customer discovery must test all three, because no evidence currently shows a buyer will pay more for any of them.

#### 10.4 Differentiation claims, graded

| Claim | Status | Assessment |
|---|---|---|
| Works with existing cameras | Not differentiating | Every vendor listed above advertises this. It is a category requirement. |
| Local / edge processing for privacy | Not differentiating | Edge-based architecture is the dominant deployment pattern in India, at 55% of the market in 2025. Competitors already lead with it. |
| Does not examine phone content | Not differentiating | No vendor in this category examines phone content. Claiming this as an advantage implies competitors do, which is not supported. |
| Affordable for SMEs | Unproven | No Indian SME price point, budget range or willingness-to-pay evidence was found. Visionify's $3,000 kit is the only verified public price and it is a US-listed figure. |
| Human review before any record or action | Plausibly differentiating | Not observed as a headline design commitment among the vendors reviewed. This is the strongest candidate and should be the focus of validation. |
| Auditable evidence trail per reviewed event | Plausibly differentiating | Partially claimed by competitors as "audit-ready reports". The human-in-the-loop provenance is the distinguishing element, not the report itself. |
| Low-commitment pilot instead of enterprise contract | Unproven | Visionify already offers a $3,000 kit with a 30-day money-back guarantee, which is a low-commitment entry. This is a competitive response, not a moat. |

## 11. Why the problem matters now

#### 11.1 Supported factors

**Regulatory reset.** The Occupational Safety, Health and Working Conditions Code, 2020 was brought into force on 21 November 2025 by notification S.O. 5321(E), as part of the simultaneous commencement of all four Labour Codes, which together rationalise 29 existing labour laws. Critically, the Central rules and certain State rules are not yet fully in force — draft Central Rules were gazetted on 30 December 2025 for stakeholder objections. The compliance surface is therefore live but unsettled. That is a genuine reason for buyer attention, and equally a reason not to hard-code compliance-specific features prematurely.

**The technology category is established.** Intenseye, Protex AI, Voxel and Visionify all publish existing-camera safety analysis, and Indian vendors offer the same. This reduces market-education burden but also removes any first-mover advantage.

**Edge processing is commercially normal.** Edge-based architecture accounted for 55% of the India video-analytics market in 2025, and on-premises deployment for 68%. Local processing is therefore an expectation of the market, not a Guardian Lens innovation.

**Data governance is material.** The Digital Personal Data Protection Act, 2023 and its 2025 Rules establish obligations around lawful processing, accuracy where personal data is used in decisions affecting a person, security safeguards and purpose-linked erasure. Identifiable workplace video may fall within scope. This is a legal interpretation requiring case-specific review, and the staged commencement schedule must be re-checked against the gazetted Rules at deployment time rather than assumed from this document.

#### 11.2 Honest limitation

> Verdantix survey data reported that 61% of industrial decision-makers plan to increase investment in this area. This is independent analyst research rather than vendor marketing, and it partially supports the timing argument. It is global and industrial, however, not Indian and not SME. No source was found showing that Indian SMEs specifically are increasing budgets for AI workplace-safety cameras. That remains the central unvalidated "why now" assumption and should not be presented as closed.

## 12. Proof of concept — scope for 14 August 2026

Approximately three and a half weeks are available from the research cut-off. The POC must demonstrate the workflow claim, not the model quality claim, because model quality cannot be credibly established in that window on a single webcam. This is Horizon 0 in section 3 — the smallest slice that proves the central architectural claim.

#### 12.1 In the POC

1. One webcam or a pre-recorded factory-floor video feed
1. One detection class only: missing PPE (helmet or high-visibility vest), OR restricted-zone entry — chosen on the basis of which produces cleaner labelled test footage, not both
1. Real-time candidate-event generation with timestamp, camera ID and zone
1. Human accept / reject / correct interface — the central demonstrable claim
1. Event history with the reviewer decision and reviewer identity recorded
1. A basic compliance report aggregating verified events by zone and time

#### 12.2 Deliberately not in the POC

1. Custom IoT or purpose-built camera hardware
1. Multi-camera or multi-site operation
1. Man-down, phone-use, proximity or stair-safety detection — all sit in Horizon 2 or 3 and each needs its own feasibility gate
1. Any accuracy, precision or false-positive claim — the POC demonstrates a workflow, and a demo on one feed cannot support a performance number
1. Any ROI or incident-reduction claim

> **State this explicitly in the demo.** The POC proves that a candidate event can be generated, routed to a human, verified, and written to an auditable record. It proves nothing about detection accuracy in a real plant. Presenting it as an accuracy demonstration is the fastest way to lose credibility with an evaluator who knows the category.

## 13. Blocking decision and remaining evidence gaps

| Question | Status |
|---|---|
| Is the occupational-safety problem real? | Yes — supported by ILO, NCRB and DGFASLI data, with the caveats in section 7. |
| Is the solution category commercially real? | Yes — multiple funded global vendors and multiple Indian vendors sell it, with named deployments. |
| Is the Indian SME segment a validated market? | No. Not quantitatively validated. No safety-specific SAM exists in public data. |
| Is Guardian Lens differentiated? | Not on detection capability. Possibly on mandatory human verification and audit provenance. Unproven. |
| Is there evidence of willingness to pay? | None found. |
| Is camera readiness at Indian SME sites known? | No. No public data on CCTV penetration among Indian SME manufacturing sites was located. This is the single most load-bearing unknown in the model. |

> **Recommended decision.** Approve the problem for limited product analysis and a workflow-only proof of concept, conditional on direct buyer validation and a controlled camera-feasibility test. Do not approve broad development, and do not permit any performance, ROI or market-size claim in external materials.

#### 13.1 Minimum next evidence, in priority order

- Five to eight interviews with Indian plant heads, EHS leads or operations heads at Factories Act-registered sites — specifically probing whether human verification is a valued feature or an unwanted extra step
- Documented current observation process and actual review workload at three or more sites
- Direct confirmation of camera presence, positioning, resolution and network access at candidate sites — this closes the largest unknown in the model
- Written privacy and worker-communication requirements from at least one site, including any union or works-committee position
- Evidence of paid-pilot interest, not expressions of general interest
- A labelled video test on real Indian factory footage for the single chosen use case

*Companion documents: 01 — Market Research (sizing, TAM/SAM/SOM position, buyer behaviour, source register) and 02 — Competitive Research (the full worldwide competitor landscape, funding data and hardware-displacement analysis).*
