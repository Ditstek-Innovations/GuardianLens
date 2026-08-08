# 02 — Competitive Research

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 02 — Competitive Research |
| Original author | Prepared independently by a senior reviewer, without AI assistance, as an external check on the Week 1 research set. |
| Version | v1.1 — four corrections applied 21 July 2026. Original findings, structure and recommendations preserved. |
| Scope | Global — 12+ vendors across North America, Europe, Middle East, Asia-Pacific and India |
| Status | Secondary research, source-verified. Primary research pending. |
| Companion documents | 00 Idea Blocking · 01 Market Research · 03 Problem Validation · 04 Product Vision · 05 Business Model |
| Corrections recorded in | Document 08 section 5.2 |

> **Standing of this document.** This is the competitor analysis for the Guardian Lens Week 1 set. It was produced independently of the AI-assisted research in documents 00, 01 and 03, which is what gives it value: two separately produced bodies of work checked against each other, with corrections running in both directions. Its central finding changed the product scope. Document 00 section 3.1 records that change.

## Amendment record — v1.1

Four corrections were identified when this document was checked against documents 01 and 03. Each is listed with what changed and why. No original finding was removed, and no recommendation was reversed.

| # | Section | Original statement | Correction applied |
|---|---|---|---|
| A1 | 6 — Pricing opacity | No vendor examined publishes fixed pricing. | Visionify publishes a USD 3,000 starter kit covering up to ten cameras with three months of subscription and a Mac Mini M4 edge server; NAVA markets a zero-cost proof of concept on AWS Marketplace. Verified from vendor pages. The claim is restated as opacity for deployment pricing. The opportunity is unaffected. |
| A2 | 5.2 — Hardware threat | Cited prolonged inactivity as one of five detection events in the Guardian Lens brief. | Superseded. Prolonged inactivity was removed from the brief and replaced with Man-Down / Possible-Collapse Detection at Horizon 2. Recalculated against the current scope. |
| A3 | 10 — Evidence gaps | Gap 5 stated that the only market figure located was for physical PPE equipment. | Document 01 holds India video analytics sizing from IMARC and global sizing from Fortune Business Insights and Grand View Research. Not safety-specific, but materially closer than PPE equipment. Gap narrowed rather than closed. |
| A4 | 3 — Competitor set | Four active vendors absent. | Added Staqu, Mikshi AI, IntelliSee and Hanwha Vision. Hanwha strengthens this document's own hardware-displacement argument, being a camera manufacturer publishing safety analytics research. |

*One further addition: a Verdantix survey data point present on a source already cited here but not previously extracted. It appears in section 3.2.*

## 1. Executive summary

AI-powered workplace safety monitoring is an established, well-funded global category — not an emerging opportunity. This research examined more than twelve active vendors across five regions. The findings are presented without softening, because a positioning strategy built on inaccurate competitive assumptions will fail at the first serious customer conversation.

#### The four conclusions that matter

**One. The category is mature and capitalised.** Leading vendors have raised between USD 27 million and USD 94 million. Intenseye alone has raised USD 94.4 million across four rounds and states it processes 22 billion images daily across more than 25 countries. Guardian Lens will not win on capability depth against this field.

**Two. Most of the proposed differentiation is already standard.** Of the seven differentiators in the original product brief, four are offered by effectively every serious competitor: working with existing cameras, edge or on-premise processing, audit trails, and compliance reporting. These are entry requirements, not advantages.

**Three. The core detection technology is commoditised from two directions.** PPE and helmet detection is a solved problem in the published academic literature. Separately, mainstream CCTV hardware from Hikvision and Dahua already ships on-device AI covering restricted-zone and intrusion detection. The detection model cannot be the moat.

**Four. Two genuine advantages remain, and they are commercial rather than technical.** Deployment pricing is opaque across the entire field, and no vendor markets a mandatory human-verification gate as a designed product workflow. These are the defensible positions available to Guardian Lens.

> **Strategic verdict.** Guardian Lens should not be positioned as better AI. It should be positioned as the first transparently priced, human-verified safety layer built for businesses the funded incumbents do not serve. The wedge is the commercial model and the review workflow — not the computer vision.

> **Status of this verdict.** Accepted. Document 00 section 3.1 repositions restricted-zone entry as an integration feature; document 04 adopts the revised positioning statement; document 05 adopts published pricing as a commercial posture. The recommendations in section 8 have been implemented rather than noted.

## 2. Methodology and confidence framework

This research is based on public sources gathered in July 2026: vendor product and pricing pages, funding announcements from technology press and company databases, peer-reviewed academic literature, deployed customer case studies, and security-industry hardware documentation.

#### 2.1 How claims are graded

| Level | Meaning | Example in this document |
|---|---|---|
| Verified | Confirmed against a primary or independent source. | Funding amounts; specific product capabilities stated on vendor pages; published price points. |
| Vendor-stated | Claimed by the company itself; not independently audited. | All accuracy percentages and all customer outcome figures. |
| Unverified | Could not be confirmed. Explicitly flagged as a gap. | Deployment pricing; local integrator landscape. |

#### 2.2 Two deliberate exclusions

**Vendor-published comparison rankings are excluded.** A large share of the "top 10" and "X versus Y" content available for this category is published by competitors on their own domains. Such content has been used only for verifiable factual anchors such as funding amounts, never for rankings or competitive judgements.

**Accuracy percentages are excluded from all comparison tables.** No independent benchmark exists for this category. Every accuracy figure in circulation is self-reported by the vendor claiming it, measured under undisclosed conditions. Presenting these side by side would imply a comparability that does not exist.

*Both exclusions have since been adopted into document 01.*

## 3. Finding one: a funded, global competitive field

#### 3.1 Principal competitors

| Vendor | Base | Capital raised | Positioning and verified detail |
|---|---|---|---|
| Intenseye | US / Turkey | USD 94.4M (4 rounds) | Enterprise scale. Founded 2018. Series B of USD 64M in February 2024 led by Lightspeed Venture Partners. States 22 billion images processed daily across 25+ countries; 50+ documented unsafe-act categories; compatible with 90% of IP cameras. |
| Voxel | United States | USD 44M (Series B) | Site-intelligence platform on existing camera infrastructure. States 48-hour deployment. Offers worker body-blurring anonymisation. |
| Protex AI | Ireland | USD 36M (Series B, Jan 2025) | Emphasises local and on-premise processing with configurable data-residency controls. Connects to existing CCTV networks. Generates trend-based compliance reports. |
| CompScience | United States | USD 27.6M (Series B, Feb 2025) | Distinct commercial model: bundles safety monitoring with workers' compensation insurance. Led by Sands Capital. States coverage of 50+ behavioural and environmental hazards. |
| viAct | Hong Kong | Raised Apr 2025 (undisclosed) | Widest geographic footprint observed. 200+ EHS vision modules on one dashboard. States 1-5 business day deployment via RTSP on existing CCTV. |
| Buddywise | Sweden | EUR 3.5M seed + EUR 1.2M pre-seed | Founded 2020. Strictest privacy architecture found: analyses feeds in real time without storing data, uses no facial recognition, does not identify subjects. |
| Surveily | Europe | Not disclosed | Positions on anonymisation and explicit GDPR and EU AI Act compliance. Published case study claims a 75% incident reduction at Orlen. |
| Invigilo | Singapore | Not disclosed | States Saudi Aramco as a customer. Differentiates energised from unenergised machinery for proximity detection — unusually sophisticated contextual logic. |
| Visionify | United States | Not disclosed | Manufacturing focus. States detection of 15+ PPE types. Integrates with existing IP cameras, VMS and NVR via RTSP. Publishes a fixed starter-kit price (section 6). Lists Godrej, Adani, Hindware and Premier Energies as customers. |

#### 3.2 Additional vendors, including those added at v1.1

| Vendor | Relevance |
|---|---|
| Staqu Technologies (India) | ADDED v1.1. JARVIS platform deployed at a primary steel plant monitoring 2,000 workers for PPE and safety compliance, with fire and smoke identification and perimeter security, on existing camera infrastructure with no hardware replacement. |
| Mikshi AI (India) | ADDED v1.1. Real-time slip-and-fall and man-down detection on existing CCTV, with visual incident evidence and audit-ready reports. Directly competitive with the Guardian Lens Horizon 2 capability. |
| IntelliSee | ADDED v1.1. Person-down detection without identity: no facial recognition, no PHI collected, no video stored, processing locally on an on-premises appliance over ONVIF and RTSP. A useful design precedent as well as a competitor. |
| Hanwha Vision | ADDED v1.1. A camera manufacturer, not a software vendor. Published a slip-and-fall detection white paper in January 2026 positioning automated detection as support for emergency response obligations. Direct additional evidence for the hardware-displacement argument in section 5.2. |
| Also confirmed active | Spot AI, Remark Holdings, SafetyWhat, EasyFlow, Videoloft, NAVA, inviol and Avigilon (Motorola). In India: Videonetics, Uncanny Vision, AllGoVision, Vehant, Intozi, Agrex.ai, DataToBiz, LogicLens and Tentosoft. |

> **Analyst-surveyed buyer intent (added v1.1).** Verdantix survey data reported that 61% of industrial decision-makers plan to increase investment in this area. This is independent analyst research rather than vendor marketing. It is global and industrial, however, not Indian and not SME, and should not be presented as evidence of Indian SME demand.

> **Implication for Guardian Lens.** A client or investor will assume this space is empty. It is not. Acknowledging the field directly, and explaining precisely which part of it Guardian Lens does not intend to compete in, is a stronger opening than claiming novelty that does not survive a search engine.

## 4. Finding two: feature convergence

Independently of region or funding level, competitor feature sets have converged. The table below audits each differentiator from the Guardian Lens product brief against what competitors already offer.

| Proposed differentiator | Verdict | Evidence |
|---|---|---|
| Works with existing cameras | Table stakes | Universal. Protex AI connects to existing CCTV networks; Visionify supports any existing IP camera, VMS and NVR via RTSP; Voxel and Intenseye both build on installed infrastructure. |
| Local / edge processing for privacy | Behind frontier | Protex AI offers configurable data residency; viAct offers edge deployment. Buddywise goes further — real-time analysis with no data storage and no facial recognition. Surveily claims GDPR and EU AI Act compliance. Document 04 has been revised to grade this as behind the frontier rather than merely undifferentiated. |
| Audit trail for every event | Table stakes | viAct centralises violation histories and heatmaps; Protex AI supports documents, actions and comments attached to safety events. |
| Compliance reporting | Table stakes | Protex AI produces trend and non-compliance reports. In India, Tentosoft already markets reporting aligned to the Factories Act 1948 and OSH Code 2020. |
| Detects events without examining phone content | Weak claim | No competitor examines phone content either. This describes an absence of a feature nobody offers; it will not read as a differentiator to an informed buyer. |
| Affordable for SMEs | HOLDS | No competitor publishes deployment pricing, and the funded vendors target large enterprise. The gap is genuine. Note that document 05 separately grades Guardian Lens's ability to occupy that gap profitably as unproven — the gap existing and Guardian Lens being able to fill it are distinct claims. |
| Human review before action | HOLDS | Competitors alert supervisors and support workflows, but none markets a mandatory verification gate as the central product concept. This is a defensible design and governance position. |
| Low-commitment pilot | HOLDS (weakly) | viAct states 1-5 day deployment and Voxel states 48 hours, so speed is contested. NAVA offers a zero-cost proof of concept, so entry price is contested too. Commercial terms after the pilot, not technical speed, are where this can hold. |

> **Net result.** Three of seven differentiators survive scrutiny: SME affordability, the human-verification gate, and low-commitment pilot terms. All three are commercial or workflow positions. None is a technical capability. The pitch must be rebuilt on this narrower and more honest base.

## 5. Finding three: the detection technology is commoditised

#### 5.1 The academic literature

Safety helmet and PPE detection is a thoroughly solved research problem with an extensive published body of work. Documented peer-reviewed implementations include approaches built on Faster R-CNN and on successive YOLO generations including v3, v4, v5 and v7, published across venues such as IJCNN, Scientific Reports and Expert Systems with Applications. Work in this area extends back to at least 2018, including research from the Chinese Academy of Sciences on helmet detection for power-substation surveillance.

Critically, one documented implementation runs helmet detection on an NVIDIA Jetson Nano — low-cost, widely available edge hardware. Others address adjacent problems including welding-helmet use and PPE verification in nuclear decommissioning.

> **Risk.** A competent engineering team, or a university group, can reproduce the Guardian Lens core detector from freely published papers on inexpensive hardware. Any defensibility claim resting on model accuracy will not survive technical due diligence.

#### 5.2 The threat from CCTV hardware

The second commoditisation pressure comes from below. The camera hardware that target customers already own increasingly ships with on-device AI:

1. Hikvision AcuSense embeds a deep-learning algorithm in the camera or NVR, classifying targets as human, vehicle or other, and supports line-crossing and region-entry detection filtered by target type. Hikvision markets it as available at only a small incremental cost.
1. Dahua IVS provides line crossing, intrusion and abandoned-object detection, with WizMind running classification on a dedicated on-camera neural chip without a cloud round trip.
1. Both capabilities are available across a wide range of price points, with Dahua offering AI on lower-tier hardware than the equivalent Hikvision entry tier.
1. Hanwha Vision, a further manufacturer, published slip-and-fall detection research in January 2026 — evidence that hardware vendors are extending upward into safety analytics rather than remaining at security analytics.

> **Corrected at v1.1.** The original text assessed this against a superseded brief that included prolonged inactivity as a detection event. That capability was removed and replaced with Man-Down / Possible-Collapse Detection at Horizon 2. Recalculated against the current scope: of the two Horizon 1 detection events, restricted-zone entry is substantially addressable using firmware the customer has already paid for, while PPE compliance is not. The conclusion is unchanged and, if anything, sharpened — the single genuinely differentiated Horizon 1 detection is PPE compliance.

> **Recommendation, and its status.** Reposition restricted-zone entry as an integration feature rather than a headline capability, and lead on PPE compliance plus the verification and evidence workflow. Claiming to sell what the customer's existing NVR already does invites an immediate and damaging objection. ACCEPTED AND IMPLEMENTED: document 00 section 3.1 now assigns zone detection to the customer's NVR and assigns verification, unified record and reporting to Guardian Lens.

## 6. Finding four: pricing opacity

> **Corrected at v1.1.** The original claim was that no vendor examined publishes fixed pricing. Two exceptions were subsequently verified and are recorded below. The claim is restated as: no vendor publishes deployment pricing, and the only published figures are entry-level packages. The opportunity is unaffected — arguably it is strengthened, because the two published prices demonstrate that publishing is possible rather than structurally impossible in this category.

| Vendor | Pricing disclosure |
|---|---|
| Visionify | PUBLISHES A PRICE. USD 3,000 one-time for a PPE starter kit, including three months of subscription, support for up to ten cameras, a Mac Mini M4 edge server and a 30-day money-back guarantee. Verified on the vendor's own page. This is an entry package, not deployment pricing. |
| NAVA | PUBLISHES A COMMERCIAL TERM. Lists a zero-cost proof of concept on AWS Marketplace for PPE, unsafe behaviour, restricted-zone and near-miss detection on existing cameras. |
| viAct | States explicitly that it does not publish fixed pricing. Cost depends on camera count, modules selected, site size and deployment model. Offers both project-based and subscription models. |
| Tentosoft (India) | On-premise agreements priced per site by camera count and feature requirements. Directs buyers to request a site-specific quote. |
| Intenseye | No published pricing. G2 lists no entry-level price. A free trial is available. |
| Voxel, Protex AI, Invigilo, CompScience, Buddywise, Surveily | No published pricing. All route to a sales or demo request. |

One low-end reference point was found: an Indian supplier listing AI-based PPE detection on existing 4MP+ CCTV from approximately INR 10,000, with pricing subject to project scope. This establishes a floor a value-conscious buyer may anchor against. It is too vague to use directly — it is unclear whether the figure is per camera or per site, one-time or recurring, and which detections are included. Clarify before treating it as a benchmark.

> **This is the opportunity, not a research gap.** Near-universal opacity means every buyer in this category must enter a sales process before learning what a deployment costs. For a smaller business, that friction alone is often disqualifying. Published, simple, self-serve pricing would make Guardian Lens the only transparently priced option in its field. The act of publishing is the differentiator, independent of what the number turns out to be — which converts pricing from an unsolved variable into a posture that can be chosen immediately. ACCEPTED: document 05 section 2.1 adopts this as the commercial position.

## 7. Finding five: identified white space

#### 7.1 Phone-use detection

Across every competitor product page reviewed, the marketed detection categories were consistent: PPE compliance, restricted-zone entry, vehicle and forklift proximity, work-at-height and fall risk, missing barricades, spills, ergonomics, and fire or smoke detection.

**Phone-use detection was not marketed as a named safety capability by any vendor examined.** This is a real gap in the competitive set. It is not yet, however, a validated opportunity — the absence may equally indicate that buyers do not request it, or that it is commercially awkward because it sits close to employee surveillance. Secondary research cannot distinguish between these explanations.

> **How this white space is being treated.** Guardian Lens has placed phone-use detection at Horizon 2 and only in a narrowed form: inside a designated hazardous zone, where a written site rule exists, detecting the object and its location and never screen content. Given that this document identifies the surveillance adjacency as a plausible reason for the gap, that gating is the appropriate response to an unvalidated opportunity rather than an eager one.

#### 7.2 The verification gate

Competitors alert supervisory staff on detection and support subsequent workflow. None found positions mandatory human verification as the defining architecture of the product. For Guardian Lens this can be framed as governance rather than as a feature: no detection becomes a compliance record, and no record becomes grounds for action, until a named safety officer has accepted it. This directly addresses the strongest objection the product will face, which is worker and union resistance to automated monitoring.

#### 7.3 Transparent SME commercial model

Covered in section 6. Restated here as the third component of the recommended position.

## 8. Recommended positioning

The original brief proposed positioning Guardian Lens as a privacy-conscious AI safety layer for existing cameras. That framing is accurate but no longer distinguishing, because the funded competition occupies it and, in the case of Buddywise and Surveily, occupies it more credibly.

> **Proposed.** Guardian Lens is the transparently priced safety and compliance layer for workplaces that the enterprise platforms do not serve — turning existing cameras into auditable safety evidence, where no event becomes a record until a named human has verified it.

#### 8.1 What this changes

| Move away from | Move toward |
|---|---|
| "Privacy-conscious AI safety layer" | Human-verified compliance evidence with published pricing |
| Seven claimed differentiators | Three defensible ones, stated plainly |
| Competing on detection breadth | Competing on cost of ownership and governance |
| Restricted-zone entry as a headline feature | PPE compliance and verified evidence as the headline |
| Positioning against Intenseye and Voxel | Positioning against manual safety inspection and passive CCTV |

The final row is the most important strategic adjustment. The realistic competitor for a smaller manufacturer is not a funded enterprise platform they will never evaluate. It is the status quo: a clipboard, a periodic walkthrough, and CCTV footage reviewed only after an incident has already occurred.

*All five rows have been adopted. Document 04 sections 5.1 and 5.2 carry the revised positioning statement and the competitive framing.*

## 9. Principal risks

| Risk | Description | Mitigation |
|---|---|---|
| Technical commoditisation | The core detector is reproducible from published research on low-cost edge hardware. Capability alone is not defensible. | Compete on workflow, evidence integrity and commercial terms rather than on model performance. |
| Displacement by hardware | Hikvision and Dahua on-device AI already covers intrusion and zone logic, and continues to expand. Hanwha Vision is moving into safety analytics. | Integrate with rather than duplicate NVR analytics. Own the verification and audit layer above them. Implemented in document 00 section 3.1. |
| Deployment reality gap | A documented refinery deployment required PPE models tuned to site-specific kit and camera fields of view adjusted, because legacy placements were designed for surveillance rather than analytics. | Budget for per-site calibration. Do not price or promise as pure plug-and-play. |
| Worker and union resistance | The product monitors people. Phone-use detection heightens this materially. | Lead with the human-verification gate. Consider making detection scope worker-visible by design. |
| Regulatory exposure | The EU AI Act is already being addressed by competitors. Workplace monitoring rules vary by jurisdiction; in India the OSH Code and DPDP framework apply. | Treat compliance posture as a product requirement, not a later addition. |
| Price-floor pressure | Low-cost regional suppliers offer AI PPE detection from roughly INR 10,000, and a competitor offers a zero-cost proof of concept. | Compete on evidence quality, audit trail and support — not on being cheapest, and not on pilot entry price. |

## 10. Evidence gaps and required primary research

The following could not be established from public sources. They are stated openly so that no decision is taken on the assumption that they are known.

| # | Gap | How to close it |
|---|---|---|
| 1 | Competitor deployment pricing. Two entry-level prices are published; no vendor publishes deployment rates. | Request quotes as a prospective buyer. Three to five vendors would establish a real range. |
| 2 | Independently verified accuracy. All published figures are vendor self-reported and unaudited. | Benchmark internally against a held-out dataset captured in real target-site conditions. |
| 3 | Whether phone-use detection is a wanted feature or an unwanted one. | Direct discovery interviews with 10-15 safety and operations managers. |
| 4 | Local systems-integrator competition in the immediate target region, which is not indexed online. | Field calls to CCTV installers and integrators serving local industrial customers. |
| 5 | NARROWED at v1.1. Safety-specific software market sizing. Document 01 holds India video analytics at USD 316.08 million in 2025 rising to USD 1,005.36 million by 2034 (IMARC), and global video analytics from Fortune Business Insights and Grand View Research. None is safety-specific, and IMARC does not name manufacturing as an end-user category at all. | No purchase of an analyst report is required for a market ceiling. What remains genuinely absent is a safety-specific figure, which document 01 concludes does not exist in public data. |
| 6 | Willingness to pay among target buyers. | Price-sensitivity testing during pilot conversations. |
| 7 | ADDED at v1.1. Whether Guardian Lens can reliably receive alarm events from common NVRs, and how many target sites have such analytics present and licensed. | Test ONVIF, vendor APIs and HTTP alarm callbacks during the camera audit. This is now a dependency of the recommended positioning. |

> **Note on market sizing.** A frequently cited figure places the Asia-Pacific personal protective equipment market at USD 11.28 billion in 2025, growing to USD 15.30 billion by 2030. This measures physical protective equipment — helmets, vests, gloves — and not detection software. It must not be presented as the addressable market for Guardian Lens. Doing so would be materially misleading to an investor or client.

## 11. Source register

*All sources accessed July 2026. Vendor pages are cited as evidence of positioning and stated capability, not as independent verification of performance.*

#### Vendor sources

1. Protex AI — PPE detection product pages
1. Voxel — industry insights and product pages
1. viAct — PPE detection and AI modules pages
1. Visionify — PPE compliance and starter kit pages (starter kit price verified directly, v1.1)
1. Surveily, Invigilo, SafetyWhat, EasyFlow, Videoloft, Tentosoft — product pages
1. Staqu Technologies — JARVIS platform materials (added v1.1)
1. Mikshi AI — fall and collapse detection use case (added v1.1)
1. IntelliSee — fall detection solution page (added v1.1)
1. NAVA Vision AI: SafetyView — AWS Marketplace listing (added v1.1)

#### Funding and company data

1. Tracxn — Intenseye company profile, USD 94.4M total across four rounds
1. Business Wire and technology press — Intenseye USD 64M Series B, February 2024, led by Lightspeed Venture Partners
1. Reported Series B rounds — Protex AI (January 2025) and CompScience (February 2025, led by Sands Capital)
1. Verdantix — blog on computer-vision safety startup funding, and survey finding that 61% of industrial decision-makers plan to increase investment (extracted v1.1)
1. Tech.eu, EU-Startups, Startups Magazine — Buddywise seed and pre-seed rounds
1. The Next Web — reporting on Buddywise privacy architecture

#### Academic literature

1. Li, Zhao, Bian and Tan — Automatic Safety Helmet Wearing Detection, Chinese Academy of Sciences (arXiv 1802.00264)
1. Vision Language Model for Interpretable and Fine-grained Detection of Safety Compliance in Diverse Workplaces (arXiv 2408.07146)
1. Dynamic Attention and Bi-directional Fusion for Safety Helmet Wearing Detection (arXiv 2411.19071)
1. Additional implementations across IJCNN, Scientific Reports, Expert Systems with Applications and Advances in Civil Engineering

#### Hardware and deployment

1. Hikvision — AcuSense technology pages and NVR documentation, including region entrance detection and human/vehicle/other classification
1. Dahua — IVS and WizMind on-device analytics documentation
1. Hanwha Vision — slip and fall detection white paper and installation guide, January 2026 (added v1.1)
1. Manufacturing Today India — Vehant deployment case study at Chennai Petroleum Corporation Limited
1. MarketsandMarkets — Asia Pacific personal protective equipment market (physical equipment only; not the addressable market)
