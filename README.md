# Guardian Lens — Week 1 Research Set

**AI safety layer for existing workplace cameras**

Research cut-off 20 July 2026 · POC target 14 August 2026 · Team of five

---

## Repository

| Path | Contents | Normative source |
|---|---|---|
| [Docs/](Docs/) | The controlled document set — GOVERNANCE §19.1 | — |
| [migrations/tenant/](migrations/tenant/) | Tenant schema, one database per tenant (ADR-016) | [Docs/DATABASE.md](Docs/DATABASE.md) §5, §6 |
| [migrations/control/](migrations/control/) | Tenant registry and routing (ADR-017) | [Docs/DATABASE.md](Docs/DATABASE.md) §1.4 |
| [src/guardian_lens/rules/](src/guardian_lens/rules/) | Rule-to-constraint registry | [Docs/RULE_BOOK.md](Docs/RULE_BOOK.md) §6 |
| [src/guardian_lens/db/](src/guardian_lens/db/) | FF-11 attestation, tenant provisioning | [Docs/DATABASE.md](Docs/DATABASE.md) §13.5 |
| [tests/bypass/](tests/bypass/) | Business-rule bypass suite | [Docs/TRD.md](Docs/TRD.md) §19.4 |

**Where code and documents disagree, the documents prevail and the code is corrected.**

This is TRD §20.2 steps 1–4 in development form: data layer, control plane
API (`src/guardian_lens/`), review UI (`web/`) and the edge agent with a
synthetic detector (`src/guardian_lens_edge/`). The real ONNX detector is
gated on G1 and does not exist yet.

```bash
make run          # ONE command: db + API (:8000) + review UI (:5173, or GL_WEB_PORT)
make edge-demo    # second terminal: simulated site feeds the queue
```

Login `admin@guardianlens.local` / `guardian-dev-1`. Full command list,
workflow narrative and gap register: **[Docs/WORKFLOW.md](Docs/WORKFLOW.md)**.

Individual pieces: `make api` · `make web` · `make bypass` · `make e2e` ·
`make test` — see `make help`.

> Every SQL statement in `Docs/DATABASE.md` remains a **specification**. The
> migrations are the executable form, and they are reviewed against it — a
> document gets reviewed, a migration gets applied.

### Tests

| Suite | Asserts | Needs a database |
|---|---|---|
| `tests/bypass/` | Every ABSOLUTE rule is unviolable **via direct SQL** — TRD §19.4 | yes |
| `tests/integration/` | Audit atomicity, concurrent decisions, clean instance, query plans, CLI | yes |
| `tests/migrations/` | Every revision reverses and reapplies; provisioning lifecycle | yes |
| `tests/unit/` | URL handling, registry invariants | no |

Markers separate the two rule states: `-m active_rule` is release-blocking,
`-m proposed_rule` is informational until [RULE_BOOK.md](Docs/RULE_BOOK.md)
§10 ratification.

CI additionally enforces GOVERNANCE §8.2 — a pull request that changes rule
enforcement **and** the bypass suite that tests it fails the build and must
be split.

---

## Documents

| # | Document | Pages | Owner | Status |
|---|---|---|---|---|
| 00 | [Idea Blocking](00_Idea_Blocking_Guardian_Lens.md) | 13 | Kuldeep | Complete |
| 01 | [Market Research](01_Market_Research_Guardian_Lens.md) | 12 | Mayank | Complete |
| 02 | [Competitive Research](02_Competitive_Research_Guardian_Lens.md) | 11 | Mayank | v1.1 — externally authored, 4 corrections applied |
| 03 | [Problem Validation](03_Problem_Validation_Guardian_Lens.md) | 10 | Mayank | Complete |
| 04 | [Product Vision](04_Product_Vision_Guardian_Lens.md) | 7 | Kuldeep | Complete |
| 05 | [Business Model](05_Business_Model_Guardian_Lens.md) | 8 | Kuldeep | Complete |
| 06 | [Initial Features](06_Initial_Features_Guardian_Lens.md) | 5 | Kapil | Complete |
| 07 | [Agentic Opportunity](07_Agentic_Opportunity_Guardian_Lens.md) | 6 | Kamal | Complete |
| 08 | [AI Output vs Human Corrections](08_AI_Output_vs_Human_Corrections_Guardian_Lens.md) | 10 | Yashpal | **Sections 7–8 incomplete by design** |
| 09 | [Team Contribution](09_Team_Contribution_Guardian_Lens.md) | 10 | Kuldeep | GitHub handles pending |
| 10 | [Founder Presentation](10_Founder_Presentation_Guardian_Lens.md) | 6 | Kuldeep | **Founder questions are inferred — replace** |

---

## The four claims this set makes

1. **The problem is real.** Supported by ILO, NCRB and DGFASLI data, peer-reviewed literature, and independent academic commentary on the limits of human video monitoring.
2. **The category is real, funded and converged.** Over USD 150 million raised across three vendors alone; ten-plus Indian vendors; detection commoditised from published research and from camera firmware.
3. **Detection is not available as a differentiator.** What remains is the mandatory human-verification gate, the audit trail, and transparent pricing.
4. **Almost nothing about the customer is validated.** Zero customer interviews conducted. Camera readiness unknown. Willingness to pay unknown.

---

## Outstanding actions

| Priority | Action | Owner | Document |
|---|---|---|---|
| 1 | Complete the source verification log — 15 rows, names and dates | Yashpal | 08 §7 |
| 2 | Replace the inferred ten founder questions with the real list | Kuldeep | 10 §1 |
| 3 | Collect GitHub handles and create the repository | Kuldeep | 09 §8 |
| 4 | Buyer interviews at 5–8 Factories Act-registered sites | Mayank, Kuldeep | 03 §9 |
| 5 | Camera audit + NVR capability check at 3+ sites | Kapil, Kamal | 09 W4 |
| 6 | ASI filtering steps 2 and 3 from published tables | Mayank | 01 §4.1 |
| 7 | Confirm each member's availability figures | All | 09 §6 |

---

## Reading order

**For a reviewer with ten minutes:** 00 (sections 1, 3, 12) → 03 (section 1 scorecard) → 08 (section 5).

**For a technical reviewer:** 06 → 07 → 09 section 4.

**For a commercial reviewer:** 01 → 02 → 05.

---

## Evidence rules applied throughout

- Every source is graded: authoritative, commercial, vendor, or derived.
- Vendor marketing is labelled as vendor marketing and never treated as independent proof of an outcome.
- No accuracy percentages appear in comparison tables — no independent benchmark exists for this category.
- No vendor-published competitor rankings are used.
- Where evidence could not be found, the documents say so rather than estimating.
- Rejected claims are recorded in 01 and 08 §6, not silently dropped.

---

## Key numbers, with their sources

| Figure | Value | Source |
|---|---|---|
| Registered factories in India | 2,61,818 (ASI 2023-24 live frame) | MoSPI / PIB |
| Factory accident deaths, India 2024 | 660 (NCRB) vs ~1,109/yr avg (DGFASLI) | NCRB ADSI; IndiaSpend RTI |
| India video analytics market 2025 | USD 316.08 mn → USD 1,005.36 mn by 2034 | IMARC |
| Helmet detection accuracy | >92% non-helmet; ~83.5% non-shoes | Scientific Reports, 2025 |
| Face-blurring accuracy cost | −7% on helmet class | CHV dataset paper |
| Capital raised by three vendors | USD 94.4M + 36M + 27.6M | Tracxn; technology press |
| Only verified competitor package price | USD 3,000 (10 cameras, 3 months) | Visionify |

**No Guardian Lens ROI, accuracy, incident-reduction, customer or revenue figure appears anywhere in this set.** No pilot, customer or test exists yet.
