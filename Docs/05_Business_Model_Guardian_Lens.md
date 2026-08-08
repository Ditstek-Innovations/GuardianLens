# 05 — Business Model

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 05 — Business Model (Week 1 deliverable) |
| Companion documents | 00 Idea Blocking · 01 Market Research · 02 Competitive Research · 03 Problem Validation · 04 Product Vision |
| Research cut-off | 20 July 2026 |
| Verified price points available | Three, all from competitors: one US starter kit, one free proof of concept, one vague Indian floor figure. |
| Guardian Lens price | Not set. Setting one now would be invention. |
| Status | A structured set of hypotheses with named unknowns, not a financial plan. |

> **Why this document contains no revenue projection.** A revenue projection requires a price, a conversion rate, a sales cycle length and a churn assumption. Guardian Lens has none of these, and no public source supplies them for Indian SME safety software. Any projection would be four invented numbers multiplied together, and multiplying invented numbers produces a confident-looking figure with no information in it. This document instead sets out the model structure, the two verified external price points, the cost drivers that can be checked, and a ranked list of what must be measured before any number is credible.

## 1. Who pays, and why they would

#### 1.1 The payer

The hypothesised economic buyer is the plant head, factory owner, operations head or EHS head at a Factories Act-registered site. Document 03 records that no customer interview has been conducted, so even this is unvalidated — including the basic question of whether safety technology is bought from a safety budget, an operations budget, an IT budget or a capital budget at an Indian SME. That question alone changes the sales motion completely and can be answered in five interviews.

#### 1.2 The separation problem

| Role | Guardian Lens |
|---|---|
| Who benefits most | The worker on the floor. |
| Who does the work | The EHS or safety officer, who absorbs the review workload. |
| Who pays | The plant head or owner. |
| Who can block it | IT or the network administrator; workers or their representatives; the CCTV integrator whose contract may be affected. |

Four distinct parties, none of whose interests automatically align. This is the structural reason the sales cycle is likely to be slower than the product's simplicity suggests, and it should be assumed to be slow until measured otherwise.

#### 1.3 Candidate reasons to pay

Ordered by how well each is currently supported. All are hypotheses.

| Reason | Argument | Support |
|---|---|---|
| Governance and evidence | Employers carry statutory duties under the OSH Code, now in force. A structured, human-verified record is defensible in a way that recollection and paper are not. | Statutory duty is a fact. That buyers will pay for better evidence of it is unvalidated. |
| Observation capacity | Continuous rule checking without adding headcount, freeing safety staff from rote scanning. | The premise is supported by academic and professional-body commentary (doc 03 section 6), not by buyer evidence. |
| Insurance or claims position | Timestamped evidence may assist in claims and liability discussions. | Plausible. No Indian evidence located that insurers price this. Do not assert it. |
| Incident cost avoidance | Fewer or less severe incidents. | Cannot be claimed. No Guardian Lens outcome data exists and no reliable Indian cost-per-event figure was located. |

> **The commercially awkward truth.** The reason that would sell fastest — "this prevents injuries and saves money" — is the one Guardian Lens cannot support. The reasons it can support are slower and less emotive. Building the pitch on the unsupportable claim is the most likely way this product loses credibility with a serious buyer, and the most likely way it fails a pilot it promised too much for.

## 2. Reference pricing evidence

This is the complete set of pricing evidence located. It is thin, and its thinness is itself the finding on which the recommended commercial position rests.

| Data point | Detail | Applicability to India |
|---|---|---|
| Visionify PPE Starter Kit | USD 3,000 one-time, including three months of subscription, support for up to ten cameras, a Mac Mini M4 edge server and a 30-day money-back guarantee. | US-listed price. The only verified public package price in the category. Not an Indian price. |
| NAVA Vision AI: SafetyView | Listed on AWS Marketplace offering PPE, unsafe behaviour, restricted-zone and near-miss detection on existing cameras, marketed with a zero-cost proof of concept. | Establishes that free entry-stage evaluation exists in the category. |
| Intenseye | G2 lists no entry-level pricing. A free trial is available. | Enterprise contact-sales model with a free evaluation path. |
| All other specialist vendors reviewed | Demo or contact-sales flows with no published pricing. | No price may be inferred from the absence. |
| Indian SME price point or budget range | NOT FOUND. No credible public source located. | — |
| Per-camera or per-month industry benchmark | NOT FOUND. | — |

> **The reframe that changes this document.** Pricing across this category is opaque. Almost every vendor routes buyers into a sales process before revealing any cost, and the only published figures are entry-level kits rather than deployment pricing. For a smaller business that friction is often disqualifying on its own. The consequence is that the act of publishing a price is itself the differentiator, independent of what the number turns out to be. That converts pricing from a variable Guardian Lens cannot yet solve into a posture it can choose today — and it is the single most immediately communicable position available to the product.

#### 2.1 Transparency as the commercial position

> **Guardian Lens should publish its price.** Not because the price will be low, and not because the number is known — it is not. Because being the only option a buyer can evaluate without entering a sales process is a real and defensible advantage in a category where nobody else offers it.

Two caveats keep this honest. The claim must be that pricing is opaque for deployments, not that no vendor publishes anything at all: Visionify publishes a USD 3,000 starter kit and NAVA markets a zero-cost proof of concept, so an absolute claim is falsifiable in one search. And a published price still has to be a viable price, which requires the cost work in section 5 and the willingness-to-pay evidence in section 7. Transparency is a posture that can be committed to now; the number remains unknown.

## 3. Pricing model options

Four structures, assessed on fit to the product and the segment. No price level is proposed, because no price level can be supported. What can be reasoned about now is the shape of the model.

| Model | Structure | Fit | Problem |
|---|---|---|---|
| Per camera per month | Recurring fee scaling with connected cameras. | Category-conventional. Scales with delivered value and with inference cost. | Penalises the customer for extending coverage — the opposite of the safety incentive. May cap adoption at the minimum viable camera count. |
| Per site per month | Flat recurring fee per site, within a camera band. | Simple to sell to an SME. Encourages full coverage. Predictable for the buyer. | Decouples revenue from cost, since inference cost rises with cameras. Needs banding to stay viable. |
| Hardware plus subscription | One-time edge appliance charge, then recurring software fee. | Matches the only verified competitor package. Recovers hardware cost up front. Familiar to Indian industrial buyers used to capex. | Raises the entry barrier in a segment where cost is a documented adoption barrier for smaller organisations. |
| Per verified event | Charge tied to events confirmed by a reviewer. | Aligns price with delivered value and is unusually honest. | Rejected. It creates an incentive to generate more detections, penalises the customer for having a hazardous site, and makes revenue fall as safety improves — the wrong incentive at every level. |

> **Leading hypothesis, to be tested rather than assumed.** A banded per-site subscription with a modest one-time onboarding charge, priced so that the first site is a decision an operations head can make without board approval. The rationale is that it encourages full camera coverage, is simple to explain to a first-time buyer, and matches the one structure with a verified competitor precedent. The approval-threshold assumption is itself unvalidated and is item 3 in section 7.

## 4. Customer acquisition

#### 4.1 The constraint

Guardian Lens will have no brand, no case study, no reference customer and no measured accuracy figure. Every conventional enterprise-software acquisition channel depends on at least one of those. The first customers must therefore be acquired on relationship and access rather than on marketing.

#### 4.2 Sequenced approach

| # | Channel | Approach | Assessment |
|---|---|---|---|
| 1 | Direct founder outreach | Named approaches to Factories Act-registered sites, initially in West and Central India, which IMARC identifies as the largest regional share of the India video-analytics market at 34%. | The only channel that works with zero credibility. Slow, unscalable, and correct for the first five customers. |
| 2 | CCTV integrators and system integrators | Partner with firms that already installed and maintain the camera estate at target sites. | They hold the relationship, know the camera inventory, and can answer the camera-readiness question before a visit. Highest-leverage channel. Requires a margin share that must be modelled. |
| 3 | Industry associations and EHS bodies | Indian industry and safety professional associations. | Access to the buyer role at low cost. Also closes the practitioner-sentiment gap recorded in document 03 section 7. |
| 4 | Insurers and workers' compensation intermediaries | Approach parties with a financial interest in fewer incidents. CompScience has validated this model commercially, bundling safety monitoring directly with workers' compensation insurance on the back of a USD 27.6 million Series B. | A competitor has proven the model exists, which raises it above speculation. It remains untested in India, where workers' compensation operates differently. Worth one exploratory conversation, not a plan. |
| 5 | Cloud marketplaces | Listing as a distribution channel. | A competitor already does this. Realistic only after a reference customer exists. |
| 6 | Content and inbound marketing | Search-led demand capture. | The category is saturated with vendor SEO content, much of it carrying untraceable claims (document 01). Competing there without evidence would mean adding to that noise. |

> **The integrator channel deserves separate testing.** It is the only route that solves the largest unknown in the entire model — whether target sites have usable cameras — before a sales conversation starts, because the integrator already holds the camera inventory. Two or three integrator conversations may be worth more than twenty cold approaches to plants.

## 5. Cost drivers

#### 5.1 What can be verified

Edge compute is the one cost input with a public reference price, and even it carries substantial variance:

1. NVIDIA lists the Jetson Orin Nano Super Developer Kit at USD 249, delivering up to 67 TOPS, with the developer kit comprising an 8GB module and a reference carrier board supporting up to four cameras.
1. NVIDIA's own enterprise marketplace page lists the same kit at USD 399.
1. Third-party resellers list it between roughly USD 370 and USD 720, with some units shipping from overseas.
1. The comparison point is that Visionify's USD 3,000 starter kit ships a Mac Mini M4 as the edge server and covers up to ten cameras.

> **What this actually tells us.** A near-threefold spread between MSRP and street price on the single most quotable hardware item is a warning about the whole cost model. Landed cost in India — including import duty, GST, logistics and local availability — could not be verified and must be obtained from an Indian distributor quote before any margin figure is credible. Developer-kit pricing is also not production-hardware pricing.

#### 5.2 Cost driver map

| Driver | Behaviour | Status |
|---|---|---|
| Edge compute hardware | Per site, scaling in steps with camera count | Reference prices above. Indian landed cost UNKNOWN. |
| Model development and tuning | Largely fixed, but recurring per new event type | UNKNOWN. Literature indicates transfer learning is viable, which reduces but does not remove this. |
| Per-site configuration and commissioning | Per site, per rule | UNKNOWN and critical. This variable determines whether Guardian Lens is software or services. |
| Support and false-positive remediation | Recurring, scaling with event volume and reviewer dissatisfaction | UNKNOWN. Structurally higher for a human-verification product. |
| Cloud and storage | Low by design, since processing is local | The edge-first architecture is a genuine cost advantage, not only a privacy one. |
| Sales and acquisition | Per customer, front-loaded | UNKNOWN. Four-stakeholder sale implies a long cycle. |
| Integrator margin | Percentage of contract value, if that channel is used | UNKNOWN. Must be modelled before pricing is fixed. |

## 6. Unit economics — structure without numbers

The model below is what a pilot must populate. Every term is currently unknown; the structure is nonetheless decision-useful, because it identifies which two or three measurements actually determine viability.

| Term | Definition and note |
|---|---|
| ACV | Annual contract value per site. UNKNOWN. Must come from a paid pilot, not from a stated willingness to pay. |
| Gross margin | ACV less hardware amortisation, support and per-site configuration. Highly sensitive to configuration effort. |
| CAC | Fully loaded cost to win one site, including the pre-sale camera feasibility visit — which is a real cost that most software models omit. |
| Payback period | CAC divided by monthly gross profit. The number that determines whether this can be self-funded. |
| Retention | UNKNOWN, and unusually uncertain here: a customer whose reviewers are drowning in false positives churns fast, while one whose reject rate is visibly falling has a reason to stay. |
| Expansion | Additional cameras, zones, rules and sites within an existing customer. The most plausible growth path, since the second site at the same company requires no new trust. |

> **The two measurements that decide viability.** Per-site configuration hours and reviewer acceptance rate. If configuration does not fall sharply from the first site to the fifth, the gross margin is a services margin and the model does not scale. If the acceptance rate is low, reviewers abandon the system and retention collapses regardless of price. Everything else in this document is secondary to those two.

## 7. Assumptions requiring validation

| # | Assumption | How to test | If false |
|---|---|---|---|
| 1 | Target sites have cameras positioned, resolved and networked adequately for detection | Physical camera audit at 3+ sites, or via an integrator's inventory | No business at all. This is the binding constraint. |
| 2 | An Indian SME will pay anything for this | Ask for a small paid commitment, not interest | No business model exists. |
| 3 | The purchase can be approved without board-level sign-off | 5-8 buyer interviews; ask who signed off the last comparable purchase | Sales cycle and pricing model both change fundamentally. |
| 4 | Per-site configuration effort falls steeply with repetition | Measure hours for sites one through five | Services business, not software. Growth requires headcount. |
| 5 | Reviewer acceptance rate is high enough for the workflow to survive | Labelled footage test, then a live shift | The core design is unusable at scale. |
| 6 | Integrators will carry the product | 2-3 integrator conversations | Direct sales only; acquisition cost rises sharply. |
| 7 | Indian landed hardware cost is close to reference pricing | Obtain distributor quotes | Margin assumptions invalid. |
| 8 | Human verification is valued rather than resented | Direct question in buyer interviews and reviewer observation during pilot | Guardian Lens has no differentiation left. |
| 9 | Workers and representatives accept deployment | Consultation at one site | Deployment blocked irrespective of the commercial case. |

## 8. Revenue potential

No revenue projection is provided. The reasoning is set out on the cover of this document. What can be stated is the frame within which a projection would later be built, with each term marked sourced or unknown:

| Step | Term | Status |
|---|---|---|
| 1 | Registered factories in India (ASI 2023-24 live frame) | 2,61,818 — SOURCED |
| 2 | Narrowed to PPE-relevant NIC codes | CALCULABLE from published ASI tables — not yet done |
| 3 | Narrowed to target employment-size bands | CALCULABLE from published ASI tables — not yet done |
| 4 | Share with adequate existing camera coverage | UNKNOWN — must be measured |
| 5 | Share reachable through chosen channels | UNKNOWN |
| 6 | Conversion rate | UNKNOWN |
| 7 | ACV | UNKNOWN |
| 8 | Retention | UNKNOWN |

Steps 2 and 3 can be completed from public ASI data at no cost and should be done before the next review. Step 4 is the load-bearing unknown and cannot be researched — only measured.

## 9. What would falsify this business model

1. Fewer than roughly half of visited SME sites have a usable camera view of a PPE-controlled or restricted area.
1. Buyers consistently describe human verification as an unwanted extra step rather than a safeguard.
1. Per-site configuration effort does not fall materially between the first and fifth deployment.
1. Reviewers abandon the queue during a pilot because event volume exceeds what a shift can absorb.
1. No site will convert a free pilot into any paid commitment, however small.
1. Indian competitors are found to be priced at a level Guardian Lens cannot approach while covering hardware and configuration cost.
1. Buyers conclude that the zone and intrusion analytics already embedded in their Hikvision or Dahua equipment are sufficient, and that the PPE layer alone does not justify a separate purchase.

> Each of these is cheap to test and most can be tested before writing significant product code. A business model that names its own falsification conditions in advance is more defensible in review than one that projects revenue it cannot support — and considerably cheaper to be wrong about.
