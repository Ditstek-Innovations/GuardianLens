# 08 — AI Output vs Human Corrections

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 08 — AI Output vs Human Corrections (Week 1 deliverable) |
| Purpose | Demonstrate that AI-assisted research was independently verified, not copy-pasted |
| AI tool used | Claude (Anthropic), via the Claude chat interface |
| Status of sections 1-5 | COMPLETE. Factual record of how each document was produced, and of corrections made in three directions: AI on the team, the team on AI, and an external reviewer on both. |
| Status of sections 6-8 | INCOMPLETE BY DESIGN. Human verification columns must be filled in by named team members before submission. |

> **Read this before completing the document.** Sections 6 to 8 contain empty fields for source checks, reviewer names and sign-off dates. They are empty because that verification has not yet happened. Filling them in without doing the work would fabricate the exact audit trail this document exists to demonstrate — and would be a more serious failure than unverified copy-paste, because it would be unverified copy-paste with a false assurance attached. Every empty box below represents roughly five to fifteen minutes of a named person opening a link and confirming a number.

## 1. How AI was used

| Dimension | Detail |
|---|---|
| Tool | Claude (Anthropic), chat interface with web search enabled. |
| Role of the AI | Source discovery, source retrieval, cross-checking of figures against original sources, drafting, structuring, and critical review of the team's initial research. |
| What the AI was explicitly instructed not to do | Invent, assume or estimate any fact, statistic, source or figure; fill gaps where reliable information was unavailable; or present vendor marketing as independent evidence. |
| Method used to enforce that | A four-class evidence taxonomy (authoritative, commercial, vendor, derived) applied to every source, with an explicit "claims deliberately excluded" register recording what was rejected and why. |
| What the AI could not do | Conduct customer interviews, visit sites, obtain paywalled analyst research, or verify anything not publicly accessible. |

## 2. How each document was produced

Every document in this set followed the same four-stage process: the team supplied the input and direction, AI was used for research and drafting, the team then corrected and finalised the content, and a named owner is accountable for it. The table records what happened at each stage rather than attributing whole documents to one party.

> **Stated plainly, so it can be answered directly if asked.** AI was used substantially for source discovery and drafting across this set. The team's contribution was the original research that preceded it, the direction that shaped it, the corrections that changed its conclusions, and the verification that confirms its figures. Section 3 records what the team's original research got wrong, section 4 records what the AI got wrong and who caught it, section 5 records what an independent reviewer corrected in both, and section 7 is the evidence that the figures were checked by hand. Those sections together are the answer to "how much of this did AI write" — not a claim, but a record.

| Document | Team input | AI role | Team correction and finalisation | Owner |
|---|---|---|---|---|
| 00 Idea Blocking | Original product concept, use-case list, target segments, POC intent. | Structured and researched; challenged internal contradictions in the concept. | Man-down renamed and defined; roadmap horizons added; productivity monitoring removed; all scope decisions approved. | Kuldeep |
| 01 Market Research | Original Week 1 research with initial sources, market figures and structure. | Verified figures against original sources; corrected errors; added missing evidence. | Source-by-source verification; figures confirmed or removed. | Mayank |
| 02 Competitive Research | Commissioned and authored externally by a senior reviewer, independently of the AI-assisted work. | None. AI was not used to produce it. | Reviewed against documents 00, 01 and 04; four corrections applied; adopted as the competitor analysis. | Mayank |
| 03 Problem Validation | Direction to validate rather than assert; the standard of evidence required. | Located peer-reviewed literature, analyst coverage and user-review evidence. | Academic citations checked; validation plan executed through interviews and audits. | Mayank |
| 04 Product Vision | Product vision, positioning, differentiation intent, the human-control principle. | Structured into outcomes, beneficiary map and control charter; graded differentiation against evidence. | Control charter confirmed as a real engineering commitment; vision scope directed by the team. | Kuldeep |
| 05 Business Model | Pricing intent and the SME affordability goal. | Pricing structures, cost drivers and assumption register; refused to produce a revenue projection. | Distributor quotes and buyer interviews to populate the unknowns. | Kuldeep |
| 06 Initial Features | POC feature list and the 14 August target. | Split into must-have, optional and excluded; sequenced the build order. | Feasibility confirmed against actual team capacity and skills. | Kapil |
| 07 Agentic Opportunity | Direction on AI and agentic scope. | Applied the published workflow-versus-agent framework; classified each component. | Technical classification confirmed by the engineers building it. | Kamal |
| 08 This document | Requirement for a defensible audit trail. | Recorded its own output, its own errors, and the claims it rejected. | Verification log completed with named checkers and dates. | Yashpal |
| 09 Team Contribution | All roles, names, ownership and allocation decisions. AI had no knowledge of the team. | Structure, phasing proposal and distribution check only. | Roles supplied and corrected twice; availability set; handles collected. | Kuldeep |
| 10 Founder Presentation | Delivery approach and the actual founder questions. | Structure, timings and answer content. | Inferred questions replaced with the real list; rehearsal and delivery. | Kuldeep |

> **Documents 00 and 01 are the clearest illustration of the process.** The team produced original research before AI review. AI then found eight errors in it, listed in section 3. The team subsequently found five errors in the AI's work, listed in section 4. Neither party got it right alone, and the record of both directions of correction is what makes this document worth reading.

## 3. What AI review corrected in the team's original research

The team produced its own research before any AI review. The following eight errors were identified in it and corrected. This section demonstrates that AI was used as a critic of existing human work, not only as a generator of new text — and that the team's starting position was a real draft rather than a prompt.

| # | Original claim | Correction |
|---|---|---|
| C1 | MSME manufacturing registrations (1,17,53,385) used as the addressable customer base. | Wrong denominator, overstating the site population by roughly 45 times. Replaced with the ASI 2023-24 live frame of 2,61,818 registered factories. Udyam data shows roughly 97% of registered MSMEs have investment below Rs. 50 lakh. |
| C2 | Intenseye Coats case cited as India evidence for PPE and zone detection. | The published outcome concerns vehicle speeding at the Madurai facility, not PPE or restricted-zone entry. Reclassified as India adoption evidence only. |
| C3 | UK HSE guidance used as the anchor for Indian safety process. | Replaced with the OSH Code, 2020, in force from 21 November 2025 by notification S.O. 5321(E). |
| C4 | Grand View figures given as USD 12.7 bn and USD 37.8 bn. | Corrected to USD 12.71 bn (2024) and USD 37.84 bn (2030). |
| C5 | ILO figures presented without vintage or definition. | Reference year 2019 added; the 395 million figure counts non-fatal injuries causing at least four days of absence; 2.6 million of 2.93 million deaths are disease-related. |
| C6 | Competitor set contained only Western vendors. | Indian vendors added: Staqu, Agrex AI, AllGoVision, Uncanny Vision, Videonetics, Tentosoft, Mikshi AI. This materially changed the blocking decision — the capability is not differentiated. |
| C7 | No India-specific injury data. | NCRB and DGFASLI series added, including the roughly 40% divergence between them. |
| C8 | "Prolonged inactivity" listed as a detection feature alongside a positioning statement rejecting productivity monitoring. | Internal contradiction identified. Renamed Man-Down / Possible-Collapse Detection with a precise trigger definition and moved to Horizon 2; productivity monitoring excluded explicitly at every horizon. |

## 4. What the AI got wrong, and who caught it

> **This section matters more than section 3.** Any team can show AI correcting humans. Showing where the AI was wrong and who caught it is what demonstrates that a review process actually operated.

| # | AI error | Correction and source |
|---|---|---|
| E1 | AI stated that prolonged inactivity detection had "no safety justification" and removed it entirely. | Over-broad. Corrected after the team clarified intent: man-down and person-down detection is an established safety category. Verified against Visionify's Person Down and Slip & Fall pages, IntelliSee, Mikshi AI and a Hanwha Vision white paper. Caught by: team (Kuldeep). |
| E2 | AI stated that no independent study of detection accuracy under Indian conditions existed. | Too strong. Peer-reviewed work on Indian construction sites exists (Frontiers in Built Environment, 2020), documenting congestion, occlusion and colour mismatching. Corrected to specify that no Indian factory-floor study was located. Caught by: AI on subsequent search; requires human confirmation. |
| E3 | AI initially narrowed the product scope without recording the broader product vision, making the concept appear smaller than intended. | Corrected by adding roadmap horizons H0-H3 to document 00 so that narrow Week 1 scope reads as deliberate sequencing rather than limited ambition. Caught by: team (Kuldeep). |
| E4 | AI cited a claim that Protex AI ranked highest in a 2026 Verdantix video analytics report. | Source was a competitor's blog, not Verdantix. Could not be independently verified; recorded as an unverified third-party claim rather than a fact. |
| E5 | Vendor SEO content initially surfaced as apparently authoritative. | Claims attributed to McKinsey (50% incident reduction) and the National Safety Council (Rs. 19,000+ crore) could not be traced to any primary source. Moved to the excluded-claims register. This is the clearest example in the project of why AI output requires source-level verification. |

## 5. What independent external review corrected

Document 02 — Competitive Research was commissioned and authored externally, without AI assistance and independently of the documents above. Reviewing the two bodies of work against each other produced corrections in both directions. This is the strongest evidence in this document that a review process operated, because neither party could mark its own work.

#### 5.1 Where the external review corrected the AI-assisted work

| # | Correction | Consequence |
|---|---|---|
| X1 | Restricted-zone entry was treated as a co-equal headline capability alongside PPE. Embedded camera analytics already provide it: Hikvision AcuSense offers region entrance detection with human, vehicle and other classification at camera or recorder level, marketed at small incremental cost, and Dahua IVS provides comparable intrusion detection on an on-camera neural chip. | The most significant single correction in the project. Restricted-zone entry was repositioned from a headline detection to an integration feature. Documents 00, 04, 06 and 07 were revised. |
| X2 | No funding or capitalisation data on the competitive field. | Added: Intenseye USD 94.4 million over four rounds, Protex AI USD 36 million, CompScience USD 27.6 million. Materially changes how the field is described to an evaluator. |
| X3 | The privacy posture was graded as merely undifferentiated. | Corrected to behind the frontier. Buddywise analyses feeds in real time without storing data and does not identify subjects. Document 04 downgraded accordingly. |
| X4 | Pricing was framed only as an unknown to be solved. | Reframed: the act of publishing a price is itself a differentiator, independent of the number. Document 05 revised. |

#### 5.2 Where the AI-assisted work corrected the external review

| # | Correction | Basis |
|---|---|---|
| Y1 | The claim that no vendor in the category publishes fixed pricing. | Visionify publishes a USD 3,000 starter kit covering up to ten cameras with three months of subscription and a Mac Mini M4 edge server, and NAVA markets a zero-cost proof of concept on AWS Marketplace. Verified directly from the vendor pages. The pricing-opacity thesis survives but was restated precisely, because the absolute claim is falsifiable in one search. |
| Y2 | Analysis worked from a superseded product brief, citing prolonged inactivity as a current detection event. | That capability had already been removed and replaced with Man-Down / Possible-Collapse Detection at Horizon 2. |
| Y3 | The market-sizing gap stated that only a physical PPE equipment figure could be located. | Document 01 holds IMARC India video analytics at USD 316.08 million in 2025 rising to USD 1,005.36 million by 2034, plus global figures from Fortune Business Insights and Grand View Research. Not safety-specific, but materially closer than PPE equipment. |
| Y4 | Four competitors absent from the vendor set. | Staqu, Mikshi AI, IntelliSee and Hanwha Vision added. Hanwha in particular strengthens the external review's own hardware-displacement argument, being a camera manufacturer publishing safety analytics research. |

> **Why this section matters more than sections 3 and 4.** Sections 3 and 4 record a team and an AI checking each other. Section 5 records two independently produced bodies of research checking each other, with corrections running in both directions and one of them changing the product scope. That is a stronger demonstration of verification than any process description could be.

## 6. What was rejected outright

Reproduced from the excluded-claims register in document 01. Each was encountered during research and refused.

| Rejected claim | Reason |
|---|---|
| "AI safety monitoring reduces incident rates by up to 50% (McKinsey)" | Untraceable to any McKinsey publication. Vendor SEO content. |
| "Preventable injuries cost Indian manufacturers Rs. 19,000+ crore annually (National Safety Council)" | Untraceable to any NSC publication. |
| "PPE compliance improves from 61% to 89% within 60 days" | Unsourced vendor marketing; no baseline or methodology. |
| "Mature platforms deliver 95%+ accuracy with under 5% false positives" | Vendor marketing. No independent evaluation under Indian factory conditions located. |
| "Slip and fall injuries cost businesses USD 70 bn annually"; "77% injury reduction" | US-scoped vendor marketing; methodology unstated; not transferable to India. |
| "Safety-focused computer vision is a USD 1.4 bn market" | No source with a transparent definition could be located. |
| Any Guardian Lens ROI, accuracy, incident-reduction or customer figure | No pilot, no customer, no test exists. |

## 7. Source verification log — TO BE COMPLETED

> **Instructions.** Each row must be independently checked by a named team member who opens the source and confirms the figure with their own eyes. Record the name and date. Do not sign off a row you did not personally check. Rows S1-S7 are the highest priority because they are load-bearing government facts.

| ID | Fact to confirm | Source to open | Checked by | Date |
|---|---|---|---|---|
| S1 | 2.93 m deaths / 395 m non-fatal injuries; reference year 2019 | ILO | [ ] | [ ] |
| S2 | 2.6 m disease vs 330,000 accident deaths | ILO news release | [ ] | [ ] |
| S3 | ASI 2023-24 live frame 2,61,818 factories | MoSPI / PIB | [ ] | [ ] |
| S4 | 5,77,03,550 total and 1,17,53,385 manufacturing registrations | MSME Annual Report 2024-25 | [ ] | [ ] |
| S5 | OSH Code in force 21.11.2025; S.O. 5321(E) | Gazette / PIB | [ ] | [ ] |
| S6 | NCRB 742 accidents / 660 deaths (2024) | NCRB ADSI | [ ] | [ ] |
| S7 | DGFASLI 1,109 deaths average 2017-2020 | IndiaSpend RTI report | [ ] | [ ] |
| S10 | USD 12.29 bn (2025) to 65.08 bn (2034), 20.30% | Fortune Business Insights | [ ] | [ ] |
| S12 | USD 12.71 bn (2024) to 37.84 bn (2030), 19.5% | Grand View Research | [ ] | [ ] |
| S13 | USD 316.08 mn to 1,005.36 mn, 13.23%; segment shares | IMARC | [ ] | [ ] |
| S18 | USD 3,000 kit, 10 cameras, 3 months, Mac Mini M4 | Visionify starter kit page | [ ] | [ ] |
| S26 | Non-helmet >92%; non-shoes ~83.5% | Scientific Reports 2025 | [ ] | [ ] |
| S27 | YOLOv5x mAP 86.55%; blurred-face helmet accuracy -7% | CHV dataset paper | [ ] | [ ] |
| S28 | India construction: occlusion, congestion, ~2 fps | Frontiers in Built Environment 2020 | [ ] | [ ] |
| S31 | Intenseye 4.6/5, 72 reviews, mid-market 47.2% | G2 | [ ] | [ ] |

*The full register runs to S35 across documents 01 and 03. The rows above are the load-bearing subset; the remainder should be checked on the same basis and recorded in the same format.*

## 8. Conclusion sign-off — TO BE COMPLETED

Each major conclusion requires a named reviewer who agrees it follows from the evidence.

| Conclusion | Document | Reviewed by | Date |
|---|---|---|---|
| The problem is real; the segment and willingness to pay are not validated | 03 | [ ] | [ ] |
| ASI factories, not MSME registrations, is the correct customer-base proxy | 01, 00 | [ ] | [ ] |
| No safety-specific SAM can be calculated from public data | 01 | [ ] | [ ] |
| Guardian Lens has no capability-based differentiation in India | 00, 01, 04 | [ ] | [ ] |
| Human verification is the only candidate differentiator, and it is unvalidated | 04 | [ ] | [ ] |
| Camera readiness is the single most load-bearing unknown | 01, 03, 05 | [ ] | [ ] |
| Man-down belongs in Horizon 2, not the POC | 00, 06 | [ ] | [ ] |
| No revenue projection can be responsibly produced | 05 | [ ] | [ ] |
| Restricted-zone entry is an integration feature, not a headline capability | 00, 04, 06 | [ ] | [ ] |
| Publishing a price is itself the differentiator | 05 | [ ] | [ ] |
| The product is not agentic end-to-end and should not claim to be | 07 | [ ] | [ ] |

## 9. Process commitments

1. No AI-generated figure enters a submitted document without a named human having opened the source.
1. Vendor marketing is labelled as vendor marketing wherever it appears.
1. Where evidence could not be found, the documents say so rather than estimating.
1. AI errors are recorded in section 4 rather than quietly corrected, so the review process is visible.
1. The team can defend every number in every document, or the number is removed before submission.
