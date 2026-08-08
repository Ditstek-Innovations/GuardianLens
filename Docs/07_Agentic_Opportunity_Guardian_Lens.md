# 07 — Agentic Opportunity

**Guardian Lens** — AI safety layer for existing workplace cameras

| Field | Value |
|---|---|
| Document | 07 — Agentic Opportunity (Week 1 deliverable) |
| Framework used | Anthropic's published distinction between workflows and agents (Building Effective AI Agents) |
| Research cut-off | 20 July 2026 |
| Headline conclusion | AI is necessary. Agentic AI mostly is not — and the safety-critical path must never be agentic. |
| Genuinely agentic surface | Three candidates, all outside the detection loop, all optional to the product working. |

> **Why this document argues against agency in most places.** Anthropic's own guidance states that when building applications with LLMs one should find the simplest solution possible and only increase complexity when needed — and that this might mean not building agentic systems at all. Agentic systems trade latency and cost for task performance, and carry the potential for compounding errors. In a safety product where an error becomes either a missed hazard or a false accusation, compounding errors are not an acceptable trade. This document identifies the narrow surface where agency genuinely earns its cost, and defends deterministic software everywhere else.

## 1. Why AI is necessary at all

The question a founder should ask is whether conventional software could do this. For the perception task, it cannot, and the reason is specific rather than rhetorical.

1. The input is raw pixels. "Is this person wearing a helmet" cannot be expressed as a rule over pixel values, because appearance varies with lighting, angle, distance, posture, helmet colour, partial occlusion and camera quality.
1. The mapping from image to condition must be learned from examples. This is the definition of the problem class that machine learning exists to solve.
1. The peer-reviewed literature confirms both feasibility and difficulty: a construction-dataset study comparing eight YOLO detectors found YOLOv5x achieved the best mean average precision at 86.55% while YOLOv5s ran fastest at 52 FPS on GPU, and a 2025 study found visually distinctive classes such as non-helmet exceeded 92% accuracy while non-shoes fell to roughly 83.5% due to occlusion and visual ambiguity.

> **Precise statement.** Machine learning is necessary for perception. That is a narrower and more defensible claim than "AI is necessary for workplace safety", and it is the only AI-necessity claim this project can support.

## 2. The framework

Anthropic distinguishes two kinds of agentic system: workflows, where language models and tools are orchestrated through predefined code paths, and agents, where models dynamically direct their own processes and tool usage while maintaining control over how they accomplish tasks. The guidance is that workflows offer predictability and consistency for well-defined tasks, whereas agents suit open-ended problems where the number of required steps cannot be predicted and a fixed path cannot be hardcoded — accepting higher cost and the risk of compounding errors, and requiring trust in the model's decision-making.

Applying that test to Guardian Lens produces a clear split. The safety path is a well-defined task with a fixed number of steps. It is a workflow, and a largely deterministic one. The open-ended problems in this product sit around the edges.

## 3. Component-by-component classification

| Component | Classification | Reasoning |
|---|---|---|
| Video ingest, decoding, frame sampling | Deterministic software | Fixed transformation. Any nondeterminism here is a defect. |
| Object and PPE detection | Machine learning, not agentic | A trained model performing a fixed inference. It makes no decisions about its own process. |
| Zone geometry and boundary logic | Deterministic software, and often not ours | Whether a point is inside a polygon is arithmetic. More importantly, embedded NVR analytics such as Hikvision AcuSense already perform this with human classification on hardware the customer owns. Guardian Lens consumes these events rather than recomputing them. |
| Threshold, debounce and dwell-time rules | Deterministic software | Explicit, auditable, tunable. A customer must be able to read the rule that fired. |
| Event record construction | Deterministic software | Structured writing. Must be exactly reproducible for the audit trail to mean anything. |
| Routing to a reviewer | Deterministic software | A queue. Adding model-driven prioritisation is a later optimisation, not a foundation. |
| The accept / reject / correct decision | Human. Never automated. | The product's central commitment. There is no version of this that a model performs. |
| Audit trail and retention | Deterministic software | Legal and governance value depends entirely on it being deterministic. |
| Candidate false-positive triage | Genuinely agentic candidate | See section 4.1. |
| Report drafting and trend narrative | Genuinely agentic candidate | See section 4.2. |
| Site configuration assistance | Genuinely agentic candidate | See section 4.3. |

> **Read the table honestly.** Eight of eleven components should be deterministic software or plain machine learning. Only three are agentic candidates, and the product works without all three. A team claiming its safety product is "agentic AI" end-to-end is either misunderstanding the term or overselling. Saying this plainly is a stronger position in a founder review than claiming agency everywhere.

## 4. The three genuinely agentic opportunities

#### 4.1 Vision-language triage of candidate events

An object detector reports what is present, not what it means. The academic literature identifies exactly this limitation: existing entity-detection methods cannot capture the semantic relationships within a scene, focusing on individual objects and locations without considering how they interact — a tool-detection model may identify a tool in a cabinet or on the ground but fail to distinguish which situation poses a hazard.

A vision-language model reasoning over a flagged frame could plausibly filter obvious non-events before a human sees them — for example, a person carrying a helmet rather than wearing it, or a person in a zone during a scheduled maintenance window.

| Aspect | Assessment |
|---|---|
| Why it is agentic | The model decides what to examine and what reasoning to apply, rather than executing a fixed path. The number of steps is not predictable in advance. |
| Why it earns its cost | It attacks the metric that determines whether the product survives: reviewer workload. Every false positive consumes reviewer time by construction in this design. |
| Feasibility on edge | Research indicates small vision-language models under four billion parameters are efficient alternatives deployable on edge devices with lower inference latency and hardware requirements. |
| Honest state of the evidence | Research on vision-language models for hazard identification has so far been limited to proof-of-concept studies, with little systematic evaluation of feasibility for on-site, near real-time deployment, and the computational demands of large models make them impractical in field conditions. |
| Mandatory constraint | Triage may only suppress or rank candidates before human review. It must never confirm an event, and every suppression must be logged and auditable so the customer can see what was filtered out. |

> This is the strongest agentic claim the project can make, and it must be framed as a research direction rather than a feature. It is not in the POC, and it should not appear on any roadmap slide as though it were built.

#### 4.2 Report drafting and trend narrative

Turning a month of verified events into a written summary for a plant head or an auditor is an open-ended language task with no fixed step count. An agent could query the verified event store, identify recurring patterns by zone and shift, and draft a narrative for a human to edit.

1. Operates only on verified events — data a human already confirmed. It cannot introduce a safety error into the record.
1. Failure mode is a poor first draft, which a human edits. This is the correct risk profile for agency.
1. The draft must be marked as machine-generated and require human sign-off before leaving the organisation.
1. This is where agency is safest in the entire product, and it is unglamorous. That combination is usually the sign of a correct answer.

#### 4.3 Site configuration assistance

Setting up a new site means identifying which cameras exist, what each one views, which zones matter and which rules apply. Document 05 identifies per-site configuration effort as one of the two measurements that decide business viability — if it does not fall steeply between the first and fifth site, Guardian Lens is a services business rather than a software business.

1. An agent could examine sample frames, propose zone boundaries and suggest applicable rules for an engineer to approve.
1. It attacks a validated commercial risk rather than a hypothetical one, which is what makes it worth the complexity.
1. Every proposal requires explicit human approval before it becomes configuration. Nothing is applied automatically.
1. Sequencing note: this only becomes worth building once enough sites exist to learn from. It is a Horizon 3 item.

## 5. Where deterministic software is strictly better

| Function | Why determinism wins |
|---|---|
| Zone boundary evaluation | Point-in-polygon is exact, instant and free. A model would be slower, costlier and occasionally wrong at something arithmetic solves perfectly. |
| Thresholds, debounce, dwell time | A customer must be able to read the rule that fired and change it. "The model felt it had been long enough" is not an auditable rule. |
| The audit trail | Its entire value is that it is reproducible. Non-determinism in the record destroys the product's only differentiator. |
| Retention and deletion | Purpose-linked erasure obligations require certainty. Deletion must be a guarantee, not a probability. |
| Access control and reviewer identity | Security-critical and exactly specifiable. Never a place for inference. |
| Alert routing | A queue with rules. Predictable behaviour matters more than clever behaviour to a supervisor mid-shift. |
| NVR event ingestion | An integration against a documented interface. Deterministic by necessity: a safety event that arrives unreliably is worse than one that does not arrive at all. |

## 6. Where human approval is mandatory

These are architectural constraints, not configurable settings. Each is a point at which no model output may proceed without a human.

| # | Gate | Rule |
|---|---|---|
| G1 | Candidate event becomes a verified event | An authorised reviewer must accept, reject or correct. No automatic promotion exists in any code path. |
| G2 | Any consequence for any worker | Guardian Lens has no disciplinary function and no interface to one. Action is taken by the site's existing processes, entirely outside the product. |
| G3 | A report leaving the organisation | Machine-drafted narrative must be reviewed and signed off by a named person. |
| G4 | A new rule or zone becoming active | Agent-proposed configuration requires explicit engineer or customer approval. |
| G5 | Any triage suppression policy change | A change to what gets filtered before human review is a safety-relevant change and requires approval plus an audit entry. |
| G6 | Adding a new detection class to a site | Customer decision. Nothing is enabled by default, ever. |

> **G5 deserves particular attention.** An agentic triage layer that quietly learns to suppress a category of event is the most dangerous failure mode available to this product, because it degrades safety silently and invisibly. If section 4.1 is ever built, suppression logging and periodic human audit of what was filtered are not features — they are conditions of the layer existing at all.

## 7. Summary position

| Question | Answer |
|---|---|
| Why is AI necessary? | Because the perception task — recognising a safety condition in raw video — cannot be expressed as rules and must be learned from examples. This applies to machine learning specifically, not to AI in general. |
| What is genuinely agentic? | Three candidates: false-positive triage using vision-language reasoning, report drafting, and site configuration assistance. None is in the POC. The product functions without all three. |
| What tools would agents use? | Read access to flagged frames and to the verified event store; the ability to propose configuration. No agent may write to the event record, alter a verified decision, or notify a worker. |
| Where is deterministic software better? | Zone logic, thresholds, the audit trail, retention, access control and routing — the entire safety-critical path. |
| Where is human approval mandatory? | Six gates, listed in section 6. G1 is the product. |
| Is Guardian Lens an agentic product? | No, and it should not claim to be. It is a machine-learning perception product with a deterministic safety path, a mandatory human gate, and a narrow set of agentic opportunities at the periphery. |
