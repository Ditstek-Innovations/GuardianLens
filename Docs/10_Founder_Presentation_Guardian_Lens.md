# 10 — Founder Presentation

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 10 — Founder Presentation (Week 1 deliverable) |
| Format | Seven minutes presentation, five minutes Q&A |
| Slides | 11, including title and close |
| Supporting documents | 00-09, plus 02 Competitive Research (externally authored) |
| Presenter | Kuldeep, with a 90-second demo segment by Kapil |
| Q&A | All five present. Kuldeep directs each question to its owner: Mayank (market, validation), Kamal (models, technical), Kapil (demo, deployment), Yashpal (limitations, failure modes, verification), Kuldeep (scope, vision, business model). |
| ACTION REQUIRED | The ten founder questions below are INFERRED from the deliverable structure. Replace them with the actual list before rehearsing. |

> **Read this first.** The specific ten founder questions used by your programme were not available. The set in section 1 was inferred from deliverables 00 to 09 and covers the ground those documents cover. The presentation structure, timings and answers will survive a substitution, but the mapping in section 1 must be checked against the real list before rehearsal — if two or three questions differ, the deck needs adjusting, not rebuilding.

## 1. The ten questions and where each is answered

| # | Question (inferred) | Answered on | Owner in Q&A |
|---|---|---|---|
| Q1 | What problem are you solving, precisely? | Slide 2 | Kuldeep |
| Q2 | Who has this problem, and how do you know? | Slides 2, 4 | Mayank |
| Q3 | How large is the opportunity? | Slide 5 | Mayank |
| Q4 | What exactly are you building? | Slides 3, 6 | Kuldeep, Kapil |
| Q5 | Who else is doing this, and why will you win? | Slide 7 | Mayank |
| Q6 | Why is AI necessary, and what is genuinely agentic? | Slide 8 | Kamal |
| Q7 | Who pays, and how does the business work? | Slide 9 | Kuldeep |
| Q8 | What have you actually validated versus assumed? | Slide 4 | Mayank |
| Q9 | What could kill this, and how would you know early? | Slide 10 | Kuldeep |
| Q10 | What are you asking for, and what happens next? | Slide 11 | Kuldeep |

## 2. Slide-by-slide with timings

Seven minutes is roughly 900 spoken words. The temptation is to add slides; the correct move is to cut them. Every timing below is a ceiling, not a target.

| # | Slide | Time | Content and delivery note |
|---|---|---|---|
| 1 | Title | 0:15 | Guardian Lens. One line: turning cameras a workplace already owns into a human-verified safety record. Names of all five members on screen. |
| 2 | The problem | 0:50 | A plant has cameras. Nobody can watch them continuously. Rule exceptions are caught inconsistently or found only after something goes wrong. Ground it in India: NCRB recorded 742 factory and machine accidents with 660 deaths in 2024, while DGFASLI data indicates an average of 1,109 deaths a year in registered factories over 2017-2020 — two official sources, roughly 40% apart. Say the divergence out loud; it is the honest version of the problem. |
| 3 | What we are building | 0:50 | The verification layer above existing cameras. We detect PPE ourselves; zone events we take from the customer's own NVR rather than duplicating it. A human accepts, rejects or corrects every candidate before anything is recorded. Audit trail with the reviewer's decision attached. State the exclusion explicitly: no facial recognition, no productivity monitoring, no automatic action. |
| 4 | What we validated — and what we did not | 1:00 | The strongest slide in the deck. Validated: the problem, the technical feasibility, that organisations buy this. Not validated: that Indian SMEs will pay, that their cameras are adequate, that buyers want the human gate. Say plainly that zero customer interviews have been conducted and that this is the top priority for next week. |
| 5 | Market position | 0:45 | Do not present a fake SAM. India video analytics is estimated at USD 316.08 mn in 2025 (IMARC) — but manufacturing is not even a named end-user category in that report. Roughly 2.6 lakh ASI-registered factories is the site ceiling. State that no safety-specific SAM exists in public data and that the team refused to invent one. |
| 6 | Demo | 1:30 | Kapil. One feed, one rule. Show a detection, pause at review, accept one, then deliberately reject one. Show the reject staying visible in the log. Close with the limitation statement before anyone asks. |
| 7 | Competition and differentiation | 0:50 | Be first to say it. This field has raised over USD 150 million across three vendors alone — Intenseye 94.4, Protex 36, CompScience 27.6. Ten-plus Indian vendors sell PPE detection on existing cameras, and Visionify already has Godrej and Adani. Detection is commoditised from above, alongside and below. What is left is the human gate, the audit trail and transparent pricing. |
| 8 | Why AI, and what is agentic | 0:45 | Kamal may take this. Machine learning is necessary for perception because the task cannot be expressed as rules. But the safety path is deliberately deterministic, and the product is not agentic end-to-end. Three agentic candidates exist, all outside the detection loop, none in the POC. |
| 9 | Business model | 0:40 | Almost nobody in this category publishes a price; buyers must enter a sales process to learn what anything costs. We intend to publish ours. The act of publishing is the differentiator, whatever the number turns out to be. No revenue projection, and say why: it would be four invented numbers multiplied together. |
| 10 | What could kill this | 0:35 | Camera readiness. Buyers rejecting the human gate as friction. Configuration not generalising across sites. Each has a named test in the plan. If the edge-case testing has produced a reviewer-load figure by presentation day, state it here — it is a number no competitor publishes. |
| 11 | Ask and next steps | 0:20 | Approval for limited analysis and a workflow-only POC. Next: 5-8 buyer interviews, camera audits at three sites, integrator conversations. |

*Total: 7:00. Rehearse against a clock. If it runs over, cut slide 10 to a single sentence on slide 11 — do not cut slide 4.*

## 3. The strategic choice in this deck

> **Lead with what is not validated.** The instinct in a founder presentation is to project confidence and hide gaps. That instinct is wrong here, for a specific reason: every gap in this project is discoverable in five minutes by anyone who knows the category. An evaluator who finds the Indian competitors, or notices there are no customer interviews, will conclude the team either missed it or hid it. Both are worse than saying it first. Slide 4 converts the project's biggest weakness into evidence of research quality — and it is the slide most likely to be remembered.

## 4. Q&A preparation

Five minutes is roughly six to eight questions. The most likely hard ones, with the honest answer and the owner.

| Likely question | Answer | Owner |
|---|---|---|
| "Indian companies already do this. Why you?" | Agree immediately. Capability is not our differentiator and our documents say so. Our candidate position is that no detection becomes a record without a named human confirming it. We have not validated that buyers pay more for that, and testing it is the top item in our plan. | Kuldeep |
| "What is your accuracy?" | We do not have one and will not quote one. A single feed over three weeks cannot support an accuracy figure. Published work reports non-helmet detection above 92% and harder classes near 83.5%, which is why we chose helmet for the POC. Our own number comes from labelled Indian factory footage, which we have not yet collected. | Kamal |
| "How big is the market?" | India video analytics is estimated at USD 316.08 mn in 2025, but that includes traffic, retail and security, and manufacturing is not a named category within it. We could not find a credible safety-specific figure and chose not to construct one. Our site ceiling is roughly 2.6 lakh ASI-registered factories. | Mayank |
| "What will you charge?" | Unknown, and we have not invented a number. The only verified public price in the category is a competitor's USD 3,000 kit, which is a US price. We are testing a banded per-site subscription. A competitor already offers a free proof of concept, so we cannot compete on entry price. | Kuldeep |
| "Isn't this surveillance?" | It is designed specifically not to be. No facial recognition, no biometrics, no audio, no productivity or activity measurement at any horizon, no automatic consequence for any worker. We removed inactivity detection from our own concept for exactly this reason and replaced it with a narrowly defined man-down capability. | Kuldeep |
| "Why is this AI rather than normal software?" | Only the perception step needs machine learning — recognising a helmet in raw video cannot be written as a rule. Everything on the safety path is deliberately deterministic, because an audit trail whose behaviour is not reproducible is worthless. | Kamal |
| "Doesn't the customer's NVR already do this?" | For zone and intrusion detection, largely yes — Hikvision AcuSense and Dahua IVS classify humans and detect region entry on hardware they already own, at small incremental cost. That is exactly why we do not sell zone detection. We take that event from their NVR, put it through human verification, and write it into the same audit record as our PPE detection. We are the layer above the hardware, not a competitor to it. PPE compliance is the detection we own. | Kamal |
| "What if the cameras are not good enough?" | That is our largest single risk and we say so in three documents. Two peer-reviewed systematic reviews name camera positioning, resolution and distance as unresolved questions. It cannot be researched further — it has to be measured, so we are auditing cameras at three sites. | Kapil |
| "What did your testing actually show? Where does it fail?" | We tested nine conditions drawn from published failure modes rather than ones we invented — occlusion, congested scenes, poor lighting, PPE colour variation, camera angle, face blurring, and helmet carried rather than worn. We can give you the results including where it broke. The number we care about most is how many events a reviewer has to adjudicate per shift, because our design makes every false positive cost human time. | Yashpal |
| "How much of this did AI write?" | AI drafted and researched; we verified. Document 08 records what AI produced, where it was wrong, who caught it, and which sources each of us checked by hand. It also lists seven claims we rejected because we could not trace them to a primary source. | Yashpal |

## 5. Presentation and Q&A ownership

Matches the allocation in document 09. Seven minutes does not accommodate five speakers, so distributed ownership is demonstrated through Q&A routing rather than by splitting the presentation.

| Member | Role on the day | Basis |
|---|---|---|
| Kuldeep | Primary presenter — problem, scope, vision, business model, ask. Directs all Q&A. | Owns 00, 04, 05 and 10; final reviewer on every deliverable. |
| Kapil | Live demonstration, approximately 90 seconds. | Owns 06 and the camera, edge and network integration. Answers deployment questions. |
| Mayank | Q&A — market, sizing, competitors, sources, validation status. | Owns 01 and 03, the source register and the interview programme. |
| Kamal | Q&A — models, accuracy, agentic architecture, technical feasibility. | Owns 07 and the detection pipeline. |
| Yashpal | Q&A — limitations, failure modes, test results, verification process. | Owns 08 and the T1-T9 edge-case testing. The most credible person present to answer what does not work. |

> **Prepare Yashpal deliberately.** The hardest questions in a founder review are about what does not work, and the instinct is for the lead to field them. Do the opposite. A named person answering failure-mode questions with specific test results is far stronger than a lead deflecting, and it is direct evidence that participation was meaningfully distributed rather than asserted in a document.

## 5. Rules for the room

1. Never quote a number that is not in the source register. If asked for one that is not, say it is not established and name the test that would produce it.
1. When conceding a point, concede fully and move to what the team is doing about it. Partial concessions read as evasion.
1. Kuldeep directs questions to owners rather than answering everything. This demonstrates distributed ownership more effectively than splitting the seven minutes five ways.
1. If a question cannot be answered, say so and record it. "We do not know, and here is how we would find out" is a stronger answer than a confident guess, and it is consistent with every other document in this set.
1. Do not use the word "revolutionary". The strongest thing about this project is that it refuses to overclaim; the presentation should sound like the documents.
1. If asked what changed as a result of external review, answer directly: an independent competitive study found that camera firmware already covers zone detection, and we changed the product scope in response. Document 08 section 5 records it. Showing that the research changed the product is stronger than showing the research agreed with it.

> **One-sentence close.** Guardian Lens turns cameras a workplace already owns into a continuously watching, human-verified safety record — and we can tell you exactly which parts of that we have proved and which parts we have not.
