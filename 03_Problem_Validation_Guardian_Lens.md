# 03 — Problem Validation

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 03 — Problem Validation (Week 1 deliverable) |
| Companion documents | 00 Idea Blocking · 01 Market Research · 02 Competitive Research · 04 Product Vision · 05 Business Model |
| Research cut-off | 20 July 2026 |
| Evidence types sought | Official research · peer-reviewed academic work · competitor adoption · independent analyst coverage · user reviews · expert input · customer interviews |
| Evidence types obtained | Six of seven. Customer interviews: none conducted. |
| Verdict | The problem is validated. The solution, the segment and the willingness to pay are not. |

> **The distinction this document rests on.** "The problem exists" and "our product solves it for a customer who will pay" are separate claims requiring separate evidence. The first is well supported by government statistics, peer-reviewed research, commercial adoption and expert commentary. The second has essentially no supporting evidence at present. This document deliberately reports the gap rather than blurring the two.

## 1. Validation scorecard

Each claim below is assessed against the strongest evidence located, and against the class of that evidence.

| Claim | Status | Strongest supporting evidence |
|---|---|---|
| Workplace injury is a large, officially recorded problem | VALIDATED | ILO global estimates; NCRB and DGFASLI series for India (section 2). |
| Continuous human observation of camera feeds is not achievable | VALIDATED | Independent academic and practitioner commentary, not only vendor claims (section 6). |
| Computer vision can detect PPE and zone conditions | VALIDATED, WITH LIMITS | Extensive peer-reviewed literature; accuracy varies sharply by class and conditions (section 3). |
| Organisations buy this category | VALIDATED | Named deployments, an analyst research stream, 72 independent user reviews of one vendor, and over USD 150 million of disclosed venture funding across three vendors alone (sections 4, 5). |
| The category works in Indian conditions | PARTIALLY VALIDATED | Peer-reviewed Indian construction-site work exists and documents specific difficulties; no Indian factory study located (section 3.3). |
| Indian SME manufacturers experience this as a priority problem | NOT VALIDATED | No evidence of any kind located. No interviews conducted. |
| Buyers value human verification before recording an event | NOT VALIDATED | No supporting or contradicting evidence located. |
| Indian SMEs will pay for this | NOT VALIDATED | No price benchmark, budget data or paid-pilot evidence located. |

> **Correction to document 01.** Document 01 stated that no independent study of detection accuracy under Indian conditions could be found. That was too strong. Peer-reviewed work on Indian construction sites exists and is summarised in section 3.3. The accurate statement is that no independent study of Indian *factory* conditions was located. Document 01 has been amended accordingly.

## 2. Official research and government data

| Source | Finding | Limitation |
|---|---|---|
| ILO (2023 report, reference year 2019) | Around 2.93 million work-related deaths annually and over 395 million non-fatal work injuries causing at least four days of absence. Of the deaths, approximately 2.6 million are disease-related and around 330,000 arise from occupational accidents. Asia-Pacific accounts for almost 63% of work-related deaths. | Dominated by disease, which no camera can observe. Not an addressable figure. |
| NCRB, Accidental Deaths and Suicides in India | Factory and machine accidents fell from 1,586 in 2010 to 742 in 2024; deaths from 1,043 to 660. | Police-reported only. Captures accidents that reach a police record. |
| DGFASLI via IndiaSpend RTI | Average 1,109 deaths and over 4,000 injuries per year in registered factories, 2017-2020. | Registered factories only; compiled from state chief inspectors. |
| Ministry of Labour, notification S.O. 5321(E) | The OSH Code, 2020 came into force on 21 November 2025 alongside the other three Labour Codes. | Central and certain State rules not yet fully in force; draft Central Rules gazetted 30 December 2025. |

The roughly 40% divergence between NCRB and DGFASLI is itself a validated finding: India has no single reliable, routinely published workplace-injury denominator. This strengthens the case for structured event records and simultaneously removes any basis for quantifying avoided harm.

## 3. Peer-reviewed academic evidence

This is the strongest independent evidence available, because it is neither government advocacy nor vendor marketing. It validates the technical premise and, more usefully, documents precisely where the premise breaks down.

#### 3.1 The technical approach is established

1. PPE detection using deep convolutional networks has been an active research area since CNNs became widely adopted, with early work establishing that hard-hat compliance could be detected from far-field surveillance footage at accuracy sufficient for practical deployment.
1. A dedicated construction dataset study comparing eight YOLO detectors across six classes found YOLOv5x achieved the best mean average precision at 86.55%, while YOLOv5s ran fastest at 52 FPS on GPU.
1. Multi-class PPE detection work using YOLOv3 reported mean average precision above 0.85 on construction-specific datasets.

#### 3.2 Accuracy is strongly class-dependent — this should drive POC choice

A 2025 study in Scientific Reports using YOLOv10 and transformer architectures found that visually distinctive categories such as non-helmet exceeded 92% accuracy, while visually challenging categories such as non-shoes fell to roughly 83.5%, attributed to occlusion and visual ambiguity.

> **Direct implication for the 14 August POC.** Helmet detection is the most reliably detected PPE class in the published literature. If a single class must be chosen for the proof of concept, the evidence supports helmet over gloves, footwear or any low-contrast item. This is an evidence-based build decision, not a preference.

#### 3.3 Indian conditions — documented, and documented as harder

A study in Frontiers in Built Environment applied transfer learning to a YOLO model for Indian construction safety. Two findings are directly relevant:

1. The authors restricted detection to hard hat and safety jacket on the grounds that these are the most commonly used PPE on construction sites in India.
1. They note that construction sites in countries such as India are more labour-intensive and congested, which makes accurate prediction more difficult because of occlusions and overlapping frames of objects, and that prediction also suffers from colour mismatching. The reported processing rate was approximately 2 frames per second.

This is genuine independent evidence that the Indian operating environment is harder than the datasets most published accuracy figures are drawn from. It concerns construction rather than factory floors, so it is indicative rather than transferable — but it is far better evidence than the vendor assertions available elsewhere.

#### 3.4 The laboratory-to-field gap — the most important academic finding

A 2026 systematic review of computer-vision technologies for PPE compliance monitoring gives an explicit methodological warning: the compiled performance values represent the maximum reported figures drawn from heterogeneous studies differing in datasets, train and test splits, evaluation protocols and operating conditions, and are therefore not directly comparable and should not be read as a ranking of model superiority. The review gives particular attention to performance variability in real-world scenarios affected by illumination changes, occlusion, viewing-angle variation, worker movement, computational constraints and large-scale deployment requirements.

A separate systematic review reaches a similar conclusion, stating that only a minority of real-world challenges have been addressed in the literature, that future work must address employee tracking and body-part occlusion, and that this raises the open question of determining optimal camera positioning, resolution and distance to objects.

> **This validates the largest unknown in the Guardian Lens model.** Peer-reviewed reviewers independently identify camera positioning, resolution and distance as unresolved questions. Document 01 flags camera readiness at Indian SME sites as the single most load-bearing unknown. The academic literature agrees that this is the binding constraint — which means it must be tested physically, not researched further.

#### 3.5 A finding that has a direct cost for the Guardian Lens design

> The same study that reported YOLOv5x at 86.55% mAP also found that detection accuracy for helmet classes on blurred faces decreased by 7%, while person and vest classes were unaffected. Face blurring is a privacy control that Guardian Lens intends to adopt and that competitors advertise. The evidence indicates it carries a measurable accuracy cost on precisely the class most central to PPE detection. This trade-off should be stated openly in the product design rather than discovered during a pilot.

## 4. Competitor adoption

Adoption evidence establishes that organisations buy the category. It does not establish outcomes, and no figure in this section may be transferred to Guardian Lens.

| Evidence | Content | Class |
|---|---|---|
| Named global deployments | Voxel with NSG Group across global manufacturing sites; Intenseye with Coats at its Madurai facility in India; Protex AI with Marks & Spencer. | Vendor-published |
| Indian vendor deployments | Staqu deployed at a primary steel plant monitoring 2,000 workers for PPE and safety compliance on existing camera infrastructure with no hardware replacement; AllGoVision referenced at Indian Oil, Haldia. | Vendor-published |
| Foreign vendors inside Indian industry | Visionify publishes Godrej, Adani, Hindware and Premier Energies among its customers. | Vendor-published |
| Channel presence | NAVA Vision AI: SafetyView is listed on AWS Marketplace, offering PPE compliance, unsafe behaviour, restricted-zone violation and near-miss detection using existing cameras, marketed with a zero-cost proof of concept. | Marketplace listing |
| Breadth of the vendor field | Beyond the vendors in document 01, the category also includes Spot AI, Surveily, NAVA, inviol, Mikshi AI, viAct, Buddywise, Invigilo, CompScience and Vehant. Document 02 covers the full landscape. | Directory and vendor pages |
| Capital committed to the category | Intenseye has raised USD 94.4 million across four rounds, Protex AI USD 36 million in January 2025, and CompScience USD 27.6 million in February 2025. Investors include Lightspeed, Insight Partners and Sands Capital. | Funding databases and technology press |
| Analyst-surveyed buyer intent | Verdantix survey data reported that 61% of industrial decision-makers plan to increase investment in this area. Global and industrial, not Indian and not SME. | Independent analyst |

> **Commercially significant.** A competitor markets a zero-cost proof of concept through a major cloud marketplace. Guardian Lens's intended "low-commitment pilot" advantage is already matched, and matched at a lower price than free is capable of undercutting. This belongs in document 05 as an acquisition-strategy constraint.

## 5. Independent analyst coverage and user reviews

#### 5.1 Analyst coverage

Verdantix, an independent research firm covering EHS and industrial software, maintains a research stream on video analytics for safety, including a Smart Innovators study on the topic. Its Green Quadrant methodology, applied across its EHS reports, involves live product demonstrations against pre-set scenarios, extensive factual questionnaires, interviews with corporate software customers, and global surveys of EHS decision-makers — 301 respondents in the studies referenced.

1. This is the closest thing to genuinely independent buyer research in the category, and it materially exceeds anything achievable from open sources.
1. It is paywalled. No findings from it are used in these documents.
1. A competitor's blog states that Protex AI ranked highest in a 2026 Verdantix video analytics report. This could not be independently verified and is recorded here only as an unverified third-party claim.

#### 5.2 Verified user reviews

G2 hosts verified user reviews for vendors in this category. This is the only independent user-sentiment evidence located.

| Data point | Finding |
|---|---|
| Intenseye rating | 4.6 out of 5 across 72 reviews. |
| Intenseye buyer mix | Mid-market accounts for 47.2% of reviews — the category is not exclusively enterprise. |
| Protex AI buyer mix | Reported market segment of 75% enterprise and 25% small business. |
| Pricing transparency | G2 lists no entry-level pricing for Intenseye. A free trial is available. |
| Reported strength | Reviewers value continuous facility monitoring and proactive detection of unsafe behaviours, and the ability to act before an incident rather than after it. |
| Reported weakness | A G2 comparison summary notes feedback that Intenseye's setup may not be as intuitive for all users. |

> **Two cautions on this evidence.** First, G2 reviews are solicited and skew positive across all software categories; a 4.6 rating is close to category-typical and should not be read as unusual satisfaction. Second, some negative sentiment encountered during research appeared in G2 category-level aggregations covering many products, and could not be reliably attributed to any specific vendor. It has therefore been excluded rather than assigned.

#### 5.3 What the mid-market share means for Guardian Lens

The finding that mid-market buyers account for 47.2% of Intenseye reviews is the single most encouraging data point located for the beachhead hypothesis, because it indicates the category is not purchased solely by large enterprises. It sits against IMARC's finding that large enterprises hold 62% of the broader India video-analytics market. The two are not contradictory — one measures reviewers of a specialist safety product, the other measures revenue across all video analytics in India — but neither validates the specifically Indian SME segment, and no source located does.

## 6. Expert input

Independent expert commentary on the core premise — that human review of continuous video is unreliable — was located from academic and professional-body sources rather than vendors.

| Source | Position |
|---|---|
| University of Illinois Chicago, School of Public Health and College of Engineering | A faculty initiative training occupational safety and health professionals in AI use describes a role for AI with more persistent observational capability than humans can reasonably apply, giving the example of detecting a worker removing a hard hat in a hazardous area and alerting a supervisor. The stated reasoning is that a human could monitor the same feed constantly, but the rote and mundane aspects of the task would likely hinder monitoring efficiency. |
| National Safety Council Safety Congress & Expo technical session (reported in Safety+Health) | Practitioners described AI-enabled cameras performing PPE checks, monitoring worker-machinery interaction, machine-guarding status and designated-area presence, framing the benefit as safety professionals not having to rely solely on observations, walkarounds or inspections. |

This matters because it is the one core premise of Guardian Lens that can be validated without a customer. The observation-gap argument is supported by an academic public-health source and a professional-body forum, not merely by companies selling cameras.

## 7. Professional community sentiment — not obtained

> **No substantive practitioner-community discussion was located.** Searches for safety-professional forum and community sentiment on AI safety cameras returned vendor marketing, vendor myth-busting content and legal commentary rather than practitioner discussion. Vendor pages asserting that conversations with safety leaders are almost always positive are marketing and are excluded. No claim about practitioner sentiment is made in this document. This remains an open evidence gap that could be closed cheaply through direct outreach to Indian EHS professional groups.

## 8. What is not validated

This section is the point of the document. Each item below is a live risk to the concept, ordered by severity.

| # | Not validated | Consequence if false |
|---|---|---|
| 1 | That any Indian SME manufacturer regards this as a priority problem worth money | The beachhead does not exist. This is unvalidated because zero customer interviews have been conducted — the largest single gap in the entire Week 1 body of work. |
| 2 | That target sites have cameras positioned, resolved and networked adequately for detection | The product cannot be deployed regardless of demand. Peer-reviewed reviews independently identify camera positioning and resolution as unresolved (section 3.4). |
| 3 | That buyers value mandatory human verification | The only remaining differentiator disappears. It is equally plausible that buyers experience verification as an unwanted workload. |
| 4 | That anyone will pay, and at what price | No revenue model is possible. No Indian price benchmark exists. |
| 5 | That detection performs acceptably in an Indian factory, as opposed to an Indian construction site or a research dataset | Pilot failure. The literature documents a substantial laboratory-to-field gap. |
| 6 | That workers and any union or works committee will accept the system | Deployment blocked at the site level irrespective of the buyer's decision. |
| 7 | That configuration is repeatable across sites | The business becomes services rather than software. A competitor blog alleges rivals require extensive per-site rule teaching, which corroborates the risk without proving it. |
| 8 | That a false-positive rate acceptable to a reviewer is achievable | The human-verification design amplifies this: every false positive consumes reviewer time by construction. |

## 9. Validation plan

Ordered by ratio of decision value to cost. The first three items require no product and no spend.

| # | Action | Method | Question it answers |
|---|---|---|---|
| 1 | Buyer interviews at Factories Act-registered sites | 5-8 semi-structured interviews with plant heads, EHS leads and operations heads. Ask about current observation practice before mentioning the product. | Gaps 1, 3, 4 |
| 2 | Physical camera audit | Site visits to 3+ plants. Record camera count, positioning, height, angle, resolution, lighting, network access and whether the PPE-relevant area is actually in frame. | Gap 2 — the binding constraint |
| 3 | Worker and representative consultation | Structured conversation at one site including any union or works committee. | Gap 6 |
| 4 | Labelled footage test | Collect real Indian factory footage for helmet detection only. Measure precision and recall against hand labels. | Gap 5 |
| 5 | Reviewer workload simulation | Run the detector over a shift of footage and count events a human would have to adjudicate. | Gap 8 |
| 6 | Paid-pilot test | Ask for a small paid commitment, not an expression of interest. | Gap 4 |
| 7 | Practitioner community outreach | Approach Indian EHS professional associations and groups directly. | Section 7 gap |

> **Interview design warning.** Describing Guardian Lens and asking whether it would be useful will produce false positives, because people are agreeable about hypothetical products. The interviews must ask what the site does today, how often, who does it, what it costs them, and what they have already tried or rejected — before the product is mentioned at all.

## Additional sources used in this document

*These supplement the S1-S24 register in document 01. All accessed 20 July 2026.*

| ID | Source | Class | Supports / limitation |
|---|---|---|---|
| S25 | Systematic Review of Computer-Vision Technologies for PPE Compliance Monitoring, Computers, 2026 | Peer-reviewed | Real-world performance variability; explicit warning that compiled figures are maxima from heterogeneous studies and are not comparable. |
| S26 | Automated non-PPE detection using YOLOv10 and transformer architectures, Scientific Reports, 2025 | Peer-reviewed | Non-helmet exceeds 92% accuracy; non-shoes approximately 83.5% due to occlusion and visual ambiguity. |
| S27 | Fast PPE Detection for Real Construction Sites Using Deep Learning Approaches (CHV dataset) | Peer-reviewed | YOLOv5x mAP 86.55%; YOLOv5s 52 FPS on GPU; helmet-class accuracy on blurred faces decreases by 7%. |
| S28 | Detection of PPE Compliance on Construction Site Using CV Deep Learning Techniques, Frontiers in Built Environment, 2020 | Peer-reviewed | India-specific: congested labour-intensive sites, occlusion and overlapping frames, colour mismatching, approximately 2 fps; PPE limited to hard hat and safety jacket as most common in India. Construction, not factory. |
| S29 | A systematic review of computer vision-based PPE compliance in industry practice (Springer) | Peer-reviewed | Only a minority of real-world challenges addressed; open questions on tracking, occlusion, and optimal camera positioning, resolution and distance. |
| S30 | Verdantix — Smart Innovators / Green Quadrant research stream and methodology | Independent analyst | Confirms an independent analyst research stream on video analytics for safety and its buyer-interview and survey methodology. Paywalled; no findings used. |
| S31 | G2 — Intenseye product, comparison and alternatives pages | Verified user reviews | 4.6/5 across 72 reviews; mid-market 47.2%; no listed entry pricing; free trial; setup intuitiveness feedback. Solicited reviews skew positive. |
| S32 | G2 — Protex AI listing | Verified user reviews | Market segment reported as 75% enterprise, 25% small business. |
| S33 | University of Illinois Chicago, School of Public Health — AI for worker safety | Academic / institutional | Independent statement that rote continuous video monitoring degrades human monitoring efficiency. |
| S34 | Safety+Health (National Safety Council) — reporting of NSC Safety Congress & Expo technical session | Professional body | Practitioner framing of AI cameras as reducing reliance on walkarounds and periodic inspection. |
| S35 | AWS Marketplace — NAVA Vision AI: SafetyView listing | Marketplace listing | Competitor offering PPE, unsafe behaviour, restricted-zone and near-miss detection on existing cameras, marketed with a zero-cost proof of concept. |
