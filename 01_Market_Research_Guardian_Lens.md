# 01 — Market Research

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 01 — Market Research (Week 1 deliverable) |
| Companion documents | 00 — Idea Blocking · 02 — Competitive Research |
| Research cut-off | 20 July 2026. All links accessed on that date. |
| Market scope | India — AI video analytics applied to industrial safety on existing cameras |
| Sources | 20 distinct sources across four evidence classes (see section 1 and the source register) |
| Evidence rule | No market figure, price, adoption rate or performance number appears unless it is traceable to a named source or shown as an explicit unknown |

> **Headline finding.** The broad video-analytics category is large, growing and well documented. The specific intersection Guardian Lens targets — camera-observable safety events at Indian SME industrial sites — has no published market size, and the segment is already served by both global and Indian vendors. This document therefore reports a TAM ceiling, a geographic proxy, and an explicitly uncalculable SAM with a defined research path to close it.

## 1. Research method and evidence classes

Every source used in this document falls into one of four classes. The class determines what the source is allowed to prove.

| Class | Examples used | What it may be used to establish |
|---|---|---|
| Authoritative public | ILO, ILOSTAT, MoSPI/ASI, NCRB, DGFASLI, Ministry of MSME, MeitY, Ministry of Labour | Facts of record: statutory dates, official counts, official statistics — subject to each source's own stated coverage limits. |
| Commercial market research | Fortune Business Insights, Grand View Research, IMARC | Market estimates only. Methodologies and underlying datasets are proprietary and unverifiable. Figures from different firms are not comparable. |
| Official vendor / product | Intenseye, Protex AI, Voxel, Visionify, Staqu, Agrex AI | What a vendor publishes about its own product, packaging, pricing and named customers. Never independent proof of an outcome. |
| Derived | Calculations in this document | Permitted only where every input and the arithmetic are visible on the page. |

#### 1.1 Two deliberate exclusions

1. Vendor-published comparison rankings are excluded. Much of the "top 10" and "X versus Y" content in this category is published by competitors on their own domains. Such pages are used only for verifiable factual anchors such as funding amounts, never for rankings or competitive judgements.
1. Accuracy percentages are excluded from all comparison tables. No independent benchmark exists for this category, and every figure in circulation is self-reported under undisclosed conditions. Presenting them side by side would imply a comparability that does not exist.

> **A fifth class was encountered and rejected: vendor-authored SEO content.** Several Indian vendor blog pages carry authoritative-sounding but untraceable claims — a "McKinsey" finding that AI safety monitoring cuts incident rates by up to 50%, a "National Safety Council" figure of ₹19,000+ crore in annual preventable-injury cost to Indian manufacturers, and PPE-compliance improvements from 61% to 89%. None could be traced to a primary source. These pages are used in this document only as evidence that a vendor exists and offers a capability, never for any number.

## 2. Market definition

Guardian Lens sits at a narrow intersection of six filters:

> Video analytics  →  industrial / EHS application  →  camera-observable safety conditions  →  Indian SME sites  →  compatible and correctly positioned existing cameras  →  a buyer with budget and authority

No public report located during this review publishes a revenue figure for that intersection, or for any close approximation of it. Broad video-analytics estimates are therefore contextual ceilings only. They describe the room Guardian Lens is standing in, not the space it can occupy.

**Scope of this research.** This document sizes and assesses the Horizon 1 approval scope defined in document 00 — PPE-rule and restricted-zone detection for Indian SME industrial sites. The wider product vision, a configurable safety-event platform, expands the addressable use cases but not the addressable sites, since it targets the same buyer at the same locations. Section 6.3 assesses the competitive position of the Horizon 2 man-down category separately, because its vendor set is partly distinct. No market figure anywhere in this document is derived from the roadmap; horizons beyond H1 are unfunded by evidence and are treated as such.

## 3. Market size and growth

#### 3.1 Global video analytics — TAM ceiling

| Firm | Base | Forecast | CAGR / period |
|---|---|---|---|
| Fortune Business Insights | USD 12.29 bn (2025) | USD 65.08 bn (2034) | 20.30% (2026-2034) |
| Grand View Research | USD 12.71 bn (2024) | USD 37.84 bn (2030) | 19.5% (2025-2030) |

> **Why these do not reconcile — and why that matters.** The two firms differ by a factor of nearly two at the forecast horizon because scope, base years and methodology differ. More instructively, Fortune Business Insights itself simultaneously publishes a second, older figure on its own site: USD 10.25 bn in 2024 growing to USD 48.94 bn by 2032. One firm, two live numbers. This is the clearest available demonstration that commercial market estimates in this category are directional at best, and it is the reason no Guardian Lens figure in either document is derived from them.

#### 3.2 India video analytics — geographic proxy

IMARC estimates the India video-analytics market at USD 316.08 million in 2025, projected to reach USD 1,005.36 million by 2034, at a CAGR of 13.23% from 2026 to 2034.

This is not a workplace-safety figure, and IMARC's own segmentation makes that unusually clear:

| Segment axis | Leading segment (2025) | Relevance to Guardian Lens |
|---|---|---|
| Application | Intrusion management — 24.0% | Closest analogue to restricted-zone detection, but framed as security, not safety. |
| End user | Traffic management — 23.0% | Manufacturing and industrial safety are not named end-user categories at all. They fall inside "Others". |
| Component | Software — 72.0% | Supports a software-led model over existing hardware. |
| Deployment | On-premises — 68.0% | Consistent with local processing being an expectation, not a differentiator. |
| Architecture | Edge-based — 55.0% | Same conclusion — edge is the market default. |
| Organisation size | Large enterprises — 62.0% | Direct headwind for an SME beachhead. |
| Region | West and Central India — 34.0% | Suggests where a pilot search should concentrate. |

> The absence of manufacturing as a named end-user category in a report that names seven others is the strongest available evidence that workplace-safety video analytics is not yet a separately measured market in India. This supports the conclusion in section 4 far better than any assertion could.

#### 3.3 Customer-base proxy — a corrected figure

> **Correction.** An earlier draft used MSME manufacturing registrations as the customer-base proxy. That figure overstates the addressable population by roughly forty-five times and has been replaced.

| Proxy | Count | Assessment |
|---|---|---|
| MSME manufacturing registrations (as on 31.12.2024) | 1,17,53,385 | Rejected as a market proxy. This is a registration count including informal micro enterprises on the Udyam Assist Platform; total registrations stood at 5,77,03,550. Udyam data shows roughly 97% of registered MSMEs have investment below Rs. 50 lakh — units with no CCTV, no EHS function and no IT administrator. |
| ASI registered factories (live frame, ASI 2023-24) | 2,61,818 | Adopted as the outer boundary. Covers factories registered under sections 2m(i) and 2m(ii) of the Factories Act, 1948 — broadly, ten or more workers using power. This is the population with a statutory safety function and a plausible camera estate. |

Roughly 2.6 lakh registered factories is a ceiling on the site count, not a market. It says nothing about camera presence, rule applicability, budget or intent.

## 4. TAM / SAM / SOM — evidence-based position

| Level | What can be stated | What cannot be stated |
|---|---|---|
| TAM | Global video analytics estimated at USD 12.29 bn in 2025 (Fortune Business Insights) or USD 12.71 bn in 2024 (Grand View Research). | Guardian Lens cannot claim the category. It contains traffic, retail, ANPR, facial recognition, crowd counting and defence applications that are irrelevant to this product. |
| Geographic proxy | India video analytics estimated at USD 316.08 mn in 2025, reaching USD 1,005.36 mn by 2034 (IMARC). | Not a safety-only figure, not an SME-only figure, and manufacturing is not even a named end-user segment within it. |
| SAM | Not reliably calculable from public evidence. Stated as unknown. | No verified count or revenue exists for Indian industrial sites with compatible cameras, relevant written rules and a budget owner. |
| SOM | Not calculable before customer and sales evidence exists. | Any market share, customer count or revenue target would be fabricated. |

#### 4.1 A defensible SAM frame with named unknowns

"Unknown" is the correct answer, but it is a weak deliverable on its own. The structure below converts it into a research plan: each line is either sourced or explicitly flagged as a quantity that must be measured. Nothing is estimated.

| Step | Filter | Status |
|---|---|---|
| 1 | Registered factories in India (ASI 2023-24 live frame) | 2,61,818 — SOURCED |
| 2 | Narrow to PPE-relevant NIC industry codes | CALCULABLE — ASI publishes results by NIC code; not yet done |
| 3 | Narrow to target employment-size bands | CALCULABLE — ASI Summary Results publishes employment-size tables; not yet done |
| 4 | Share with existing IP cameras covering the relevant area | UNKNOWN — no public data located. Highest-priority measurement. |
| 5 | Share with adequate camera positioning and resolution | UNKNOWN — site-level; can only be established by feasibility testing |
| 6 | Share with a written PPE or zone rule and an accountable owner | UNKNOWN — interview-derived |
| 7 | Annual contract value | UNKNOWN — no Indian price benchmark exists |

Steps 2 and 3 can be completed from published ASI tables within Week 2 at no cost. Step 4 is the single most load-bearing unknown in the entire model and cannot be sourced — it must be measured through site visits or a structured buyer survey.

## 5. Customer segments

#### 5.1 Verticals evidenced in current vendor deployments

Official vendor materials show deployments or named offerings across manufacturing, warehousing and logistics, food and beverage, chemicals, paper and packaging, metals and steel, automotive and building materials, and textiles. Visionify additionally lists Indian industrial customers including Godrej, Adani, Hindware and Premier Energies.

#### 5.2 Proposed beachhead

Small and medium Indian manufacturing plants and warehouses, registered under the Factories Act, with existing IP CCTV and explicit written PPE or restricted-zone rules. This is a strategic selection consistent with the product scope. It is not validated as the best-paying or easiest-to-reach segment, and IMARC's finding that large enterprises hold 62% of the India video-analytics market is direct evidence pointing the other way.

#### 5.3 Segment priority criteria

1. A visible, frequent and unambiguously defined rule
1. Adequate existing camera view of the area where the rule applies
1. An accountable safety or operations owner with budget influence
1. Manageable site and network onboarding
1. Willingness to run a transparent, non-biometric pilot with worker communication
1. Repeatability of the configuration across similar sites — without this the business is services, not software

## 6. Competitive landscape — summary

> **The full analysis now lives in document 02.** Companion document 02 — Competitive Research covers more than twelve vendors across five regions, with funding data, feature convergence analysis, pricing disclosure and hardware-displacement findings. This section retains only what is needed to support the market conclusions below; it is not the competitor analysis and should not be read as one.

#### 6.1 The three findings that bear on market position

| Finding | Detail |
|---|---|
| The field is funded and global | Intenseye has raised USD 94.4 million across four rounds including a USD 64 million Series B in February 2024; Protex AI raised USD 36 million in January 2025; CompScience raised USD 27.6 million in February 2025 bundling monitoring with workers' compensation insurance. Voxel, viAct, Buddywise, Surveily and Invigilo also operate internationally. |
| Indian vendors occupy the same capability space | Staqu, Agrex AI, AllGoVision, Uncanny Vision, Videonetics, Vehant, Intozi, DataToBiz, LogicLens, Tentosoft and Mikshi AI market PPE or industrial safety modules on existing CCTV, several with Factories Act-aligned reporting. Visionify already lists Godrej, Adani, Hindware and Premier Energies as customers. |
| Detection is commoditised from below as well as above | Hikvision AcuSense provides region entrance detection with human, vehicle and other classification at camera or recorder level, marketed at small incremental cost; Dahua IVS provides comparable intrusion and line-crossing detection on an on-camera neural chip. PPE detection is separately a solved research problem with published implementations on low-cost edge hardware. |

> **Market consequence.** This is not an underserved category awaiting a first entrant. It is a funded, converged category in which detection capability is available from platforms above, local vendors alongside, published research technically, and camera firmware below. Any market position for Guardian Lens must rest on commercial model and workflow rather than capability, which is why documents 04 and 05 grade differentiation the way they do.

## 7. Buyer behaviour and procurement signals

#### 7.1 What the data shows

Within its broader India video-analytics estimate, IMARC reports for 2025: large enterprises 62%, on-premises deployment 68%, edge-based architecture 55%, and software 72% of the market. These indicate that large organisations and locally processed deployments dominate the broader market. They do not evidence SME workplace-safety purchase intent, and the 62% large-enterprise share is a direct argument against the proposed beachhead.

#### 7.2 Pricing evidence

| Data point | Status |
|---|---|
| Visionify PPE Starter Kit — USD 3,000 one-time, 10 cameras, 3 months included | VERIFIED on the vendor's own page. One vendor, one package, US-listed price. Not an industry range and not an India price. |
| All other specialist vendors reviewed | Demo or contact-sales flows with no published pricing. No price may be inferred from that absence. |
| Indian SME price point, budget range or willingness to pay | NOT FOUND. No credible public source located. |
| Per-camera or per-month industry pricing benchmark | NOT FOUND. |

#### 7.3 Buyer and worker concerns visible in the market

Protex AI's union and worker guide identifies privacy, surveillance overreach, job displacement and data misuse as recurring concerns, and describes edge processing, anonymisation and advance communication as the responses. This is vendor-authored material and is not neutral evidence of buyer sentiment. It is nevertheless consistent with the reasoning behind Guardian Lens's scope exclusions in document 00 — and it confirms that the objections the design anticipates are objections the category already encounters in practice.

IMARC additionally notes that high upfront implementation and integration cost, and regulatory-compliance complexity, disproportionately affect smaller organisations that lack dedicated compliance resources. This is a headwind for an SME beachhead, drawn from a source this document already relies on for market sizing.

#### 7.4 What is missing

1. Indian SME safety-technology budget range
1. The actual procurement owner and approval path at a mid-size Indian plant
1. An acceptable pilot price and required payback period
1. Preferred alert frequency and channel
1. Tolerable false-positive burden before the system is abandoned
1. Willingness to permit use of existing site footage for model tuning
1. Whether human verification is perceived as a valued safeguard or an unwanted extra step

## 8. Market and technology trends

**Trend 1 — Existing-camera retrofit is the standard pattern.** Intenseye, Protex, Voxel, Visionify and the Indian vendors all publish existing-camera compatibility over RTSP or ONVIF. Retrofit is validated as a product pattern and simultaneously eliminated as a differentiator.

**Trend 2 — Edge and on-premises processing dominate.** Edge-based architecture held 55% and on-premises deployment 68% of the India video-analytics market in 2025. Visionify's starter kit ships a physical edge server. Latency, bandwidth and data-control requirements make this the default rather than a premium option.

**Trend 3 — Privacy-preserving design is a category expectation.** Intenseye publishes that it does not use facial recognition or biometrics, deletes camera data within seconds of analysis and blurs faces in alerts. Voxel reports anonymising capability in its NSG deployment. Protex publishes an anonymisation and communication playbook. These are vendor statements, but collectively they establish the baseline a new entrant must meet — not exceed.

**Trend 4 — Human governance is legally and commercially load-bearing.** The DPDP Act requires completeness, accuracy and consistency where personal data is used to make a decision affecting a person, alongside security safeguards and purpose-linked erasure. Whether a given deployment engages these obligations requires legal review, but the requirements support a design in which candidate events are reviewable and corrections are recorded. This is the one trend that argues for Guardian Lens's specific architecture rather than against it.

## 9. Evidence of category demand

The following are vendor-published cases. They evidence that named organisations have bought and deployed the category. Their performance figures are marketing claims, not independent research, and none may be transferred to Guardian Lens.

| Case | Vendor-reported content | Handling |
|---|---|---|
| Voxel — NSG Group | Expansion of deployments across global manufacturing sites, with reported reductions in selected event categories in Malaysia, Canada and the United States. | Cite as adoption evidence only. |
| Intenseye — Coats, Madurai (India) | 20% reduction in speeding detections in the first week, rising to over 50% reduction in speeding incidents. | RECLASSIFIED. The use case is vehicle speeding, not PPE and not restricted-zone entry. Valid as India adoption evidence; invalid as support for either Guardian Lens use case. |
| Protex AI — Marks & Spencer | Page title claims 80% incident reduction in ten weeks; body metrics on the accessible page are not fully consistent with the title. | Cite with the inconsistency stated, or omit. Do not use in any calculation. |

## 10. Barriers and market risks

| Risk | Severity | Basis |
|---|---|---|
| No capability differentiation available | High | Funded global platforms, at least ten Indian vendors, and published research all cover existing-camera PPE and zone detection. |
| Displacement by camera hardware | High | Hikvision AcuSense and Dahua IVS already provide zone and intrusion detection on hardware customers own, at small incremental cost, and continue to expand. Zone detection cannot be a headline capability; document 00 section 3.1 repositions it as an integration feature. |
| Technical commoditisation of the detector | High | PPE and helmet detection is a solved research problem with published implementations, including on low-cost edge hardware. Any defensibility claim resting on model accuracy will not survive technical due diligence. |
| Camera readiness at SME sites is unknown | High | No public data on CCTV penetration, positioning or resolution at Indian SME manufacturing sites was located. If readiness is low, the beachhead does not exist. |
| Large enterprises dominate the segment | High | Large enterprises accounted for 62% of the India video-analytics market in 2025 — the opposite of the target profile. |
| Cost is a known SME barrier | Medium-High | IMARC identifies high upfront implementation cost as disproportionately affecting smaller organisations without compliance resources. |
| Site-specific tuning makes delivery services-heavy | Medium-High | Vendor materials emphasise site-specific configuration; without configuration repeatability the model becomes a consulting business. |
| False-positive burden can increase workload | Medium-High | A human-verification design amplifies this risk: every false positive consumes reviewer time by construction. |
| Worker trust and data governance | Medium | DPDP obligations plus the documented union and privacy concerns in the category. |
| No transparent public dataset for the narrow segment | Medium | Confirmed across all commercial and government sources reviewed. |
| Willingness to pay is entirely unproven | High | No Indian price benchmark, budget figure or paid-pilot evidence found. |

## 11. Market-research conclusion

- Occupational safety is a substantial, officially documented problem, in India and globally — though the Indian data is internally inconsistent and the global data is dominated by disease, which cameras cannot observe.
- AI video analytics is a real and growing commercial category, and named organisations including Indian ones deploy workplace-safety products over existing cameras.
- The proposed Indian SME niche is not quantitatively validated. Public data supports no credible safety-specific SAM or SOM, and the segment's leading indicator — enterprise size mix — points away from SMEs.
- The competitive position is materially harder than the earlier draft implied. Funded global platforms, domestic Indian vendors, published research and embedded camera firmware all occupy the capability space. Detection is not available as a differentiator from any direction; see document 02 for the full analysis.

> **Therefore.** The rational next step is targeted buyer validation plus a controlled camera-feasibility test — specifically to determine whether mandatory human verification is a feature buyers value, and whether SME camera infrastructure can actually support detection. It is not broad development, and it is not any external market claim.

## Source register

*All links accessed 20 July 2026.*

| ID | Source | Class | Supports / limitation |
|---|---|---|---|
| S1 | ILO — Safety and health at work; ILO, A call for safer and healthier working environments (2023) | Authoritative | 2.93 m work-related deaths and 395 m non-fatal injuries, reference year 2019. Global; not product-addressable. |
| S2 | ILO news release, Nearly 3 million people die of work-related accidents and diseases | Authoritative | Splits 2.6 m disease deaths from 330,000 accident deaths; Asia-Pacific share of fatalities. |
| S3 | MoSPI — Annual Survey of Industries 2023-24 press note (PIB) | Authoritative | Live frame of 2,61,818 factories; ASI covers units registered under s.2m(i)/2m(ii) of the Factories Act, 1948. ADOPTED customer-base proxy. |
| S4 | Ministry of MSME — Annual Report 2024-25 | Authoritative | 5,77,03,550 total registrations, 1,17,53,385 manufacturing, as on 31.12.2024. REJECTED as market proxy; retained for context. |
| S5 | Ministry of Labour and Employment — notification S.O. 5321(E), Gazette of India, 21.11.2025; PIB release on the four Labour Codes | Authoritative | OSH Code, 2020 in force from 21 November 2025; four Codes rationalise 29 laws. |
| S6 | NCRB — Accidental Deaths and Suicides in India (factory and machine accidents series) | Authoritative | 1,586 accidents / 1,043 deaths in 2010; 742 accidents / 660 deaths in 2024. Police-reported only. |
| S7 | DGFASLI data obtained by IndiaSpend via RTI (2022) | Authoritative (secondary access) | Average 1,109 deaths and 4,000+ injuries per year in registered factories, 2017-2020. Registered factories only. |
| S8 | MeitY — Digital Personal Data Protection Act, 2023 | Legislation | Definitions, lawful processing, accuracy where data drives decisions, safeguards, erasure. Application requires legal review. |
| S9 | MeitY — Digital Personal Data Protection Rules, 2025 | Rules | Staged commencement and notice requirements. Schedule must be re-checked at deployment. |
| S10 | Fortune Business Insights — Video Analytics Market | Commercial | USD 12.29 bn (2025) to USD 65.08 bn (2034), 20.30%. Methodology proprietary. |
| S11 | Fortune Business Insights — Video Analytics Market press release page | Commercial | USD 10.25 bn (2024) to USD 48.94 bn (2032). Cited specifically to evidence the internal inconsistency in section 3.1. |
| S12 | Grand View Research — Video Analytics Market | Commercial | USD 12.71 bn (2024) to USD 37.84 bn (2030), 19.5%. Cross-check only. |
| S13 | IMARC — India Video Analytics Market | Commercial | USD 316.08 mn (2025) to USD 1,005.36 mn (2034), 13.23%; all segment shares in section 3.2; SME cost barrier. Broader than safety. |
| S14 | Intenseye — product and privacy pages | Vendor | Existing-camera positioning; non-biometric design, short retention, face blurring in alerts. |
| S15 | Intenseye — Coats case study | Vendor case | Madurai, India; speeding reduction figures. RECLASSIFIED — not a PPE or zone case. |
| S16 | Voxel — NSG Group deployment expansion | Vendor case | Named multi-site deployment and anonymising capability. |
| S17 | Protex AI — Safety Computer Vision Market Report; worker and union concerns guide; Marks & Spencer case | Vendor / promotional | Category framing, concern themes and vendor controls. M&S title metric inconsistent with body. |
| S18 | Visionify — PPE Starter Kit page and homepage | Vendor | USD 3,000 kit, 10 cameras, 3 months, Mac Mini M4 edge server, 30-day guarantee; Indian customer logos including Godrej, Adani, Hindware, Premier Energies. |
| S19 | Staqu Technologies — JARVIS platform materials | Vendor | 2,000-worker steel plant PPE deployment on existing cameras. |
| S20 | Agrex AI; AllGoVision; Uncanny Vision; Videonetics; Tentosoft — product pages | Vendor | Indian competitor set for PPE and zone detection on existing CCTV. Existence and offering only; no numeric claim taken from these pages. |
| S21 | Visionify — Person Down and Slip & Fall use-case pages | Vendor | Person-down and fall detection as a published product category on existing IP cameras, VMS and NVR via RTSP. |
| S22 | IntelliSee — Fall Detection solution page | Vendor | Person-down detection without identity, no facial recognition, no PHI, no video storage, local on-premises processing over ONVIF/RTSP. Design precedent only; performance and cost claims on the same site are excluded. |
| S23 | Mikshi AI — Fall and Collapse Detection use case | Vendor | Indian vendor offering slip-and-fall and man-down detection on existing CCTV. |
| S24 | Hanwha Vision — Slip and fall detection white paper and installation guide, January 2026 | Vendor / technical | Documents that detection is not guaranteed when a walking person is undetected beyond three seconds or is occluded by another person. Used as the feasibility basis for gating man-down to Horizon 2. |

## Claims deliberately excluded

Each of the following was encountered during research and rejected. They are listed so that a reviewer can see what was refused, not only what was accepted.

| Claim | Reason for exclusion |
|---|---|
| "Safety-focused computer vision is a USD 1.4 bn market" | No source with a transparent definition could be located. |
| "Competitors charge USD 300-600 per camera per month" | No reliable public source. Most vendors do not publish pricing. |
| "Indian SMEs will pay Rs. 15,000-30,000 per month" | No direct buyer evidence of any kind exists. |
| "AI safety monitoring reduces incident rates by up to 50% (McKinsey)" | Appears in Indian vendor SEO content; could not be traced to any McKinsey publication. |
| "Preventable workplace injuries cost Indian manufacturers Rs. 19,000+ crore annually (National Safety Council)" | Appears in vendor SEO content; could not be traced to any NSC publication. |
| "PPE compliance improves from 61% to 89% within 60 days" | Unsourced vendor marketing figure with no stated baseline or methodology. |
| "Mature platforms deliver 95%+ accuracy with under 5% false positives" | Vendor marketing. No independent evaluation under Indian factory conditions was located. Note: peer-reviewed studies of Indian construction sites do exist and are covered in document 03 section 3.3. |
| "Slip and fall injuries cost businesses USD 70 bn annually" and "reducing workplace injuries by up to 77%" | Vendor marketing on a US-focused page. US-scoped, methodology unstated, and not transferable to an Indian SME context. |
| "Trained on more than 5 billion hours of industrial scenarios, 95%+ detection accuracy" | Vendor marketing. No independent evaluation located, and no accuracy figure of any kind may be attached to Guardian Lens. |
| "Every manufacturing MSME is addressable" | False. Registration count is not a site count, and roughly 97% of registered MSMEs fall below Rs. 50 lakh investment. |
| Any Guardian Lens ROI, incident reduction, accuracy or customer figure | No pilot, no customer and no test exists. Nothing may be stated. |

*Companion documents: 00 — Idea Blocking (problem statement, scope boundaries, roadmap horizons, POC scope, blocking decision) and 02 — Competitive Research (full worldwide vendor landscape, funding, feature convergence, pricing disclosure and hardware analysis).*
