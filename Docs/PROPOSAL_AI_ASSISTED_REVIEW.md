# Proposal — AI-Assisted Review Tier (AMD-RB-05 / AMD-RB-06)

**A formal T4 rule-change proposal for the RULE_BOOK owner, drafted per
[GOVERNANCE.md](GOVERNANCE.md) §8.4. Nothing in this document changes any
rule. Nothing may be implemented from it until the RAPID process completes.**

| Field | Value |
|---|---|
| Document | Rule-change proposal (T4 RFC input). **Non-normative** |
| Version | 1.0 |
| Date | 14 August 2026 |
| Raised by | Kapil (Engineering) |
| Decided by | Kuldeep (rule book owner) via RAPID — Yashpal holds the standing proxy veto on worker-protection rules ([GOVERNANCE.md](GOVERNANCE.md) §6.4) |
| Gates engaged | **G5** (suppression/triage layer — "if ever built") · **G1** (any model doing this must be a released model) |

---

## 1. The operational need, honestly stated

A reviewer is present for part of the day. While present, they decide the
queue normally. When they leave, candidates accumulate undecided. The ask:
a **site-level mode switch** — "reviewer available" vs "AI review" — where,
in AI-review mode, the registered model's own confidence disposes queue
candidates without a human.

This directly contradicts BR-004/BR-005/BR-V-03 as written, which is why it
arrives as a T4 proposal and not a feature.

## 2. AMD-RB-05 — an explicit machine-disposition tier

Per §8.4 step 1, the rule verbatim and what would replace it:

**BR-004 today (ABSOLUTE, ACTIVE):**
> No record without human verification. A Candidate Event must not become a
> Verified Record, appear in any report, or contribute to any trend or count
> until an authorised Reviewer has accepted or corrected it. Rejected
> candidates never enter the verified record.

**Proposed replacement (for the owner to accept, amend, or veto):**
> No record without human verification. A Candidate Event must not become a
> **Verified Record** until an authorised Reviewer has accepted or corrected
> it. A site MAY additionally operate a **machine-disposition tier**, in
> which a Candidate Event may be closed as a **Machine-Screened Outcome** —
> a distinct terminal status that (a) is never a Verified Record, (b) never
> appears in any count, trend, report or export presented as verified, (c)
> permanently records the model version, threshold and mode that produced
> it, and (d) remains re-openable for human decision. Machine-Screened
> Outcomes are reported to the customer as their own separately-labelled
> category, including their volume, so the proportion of unreviewed
> dispositions is never hidden.

Consequential amendments: BR-005 unchanged (it governs Verified Records,
which remain human-only). BR-V-03 gains: *"except within the
machine-disposition tier of BR-004, which may never produce a Verified
Record."* BR-S-02 unchanged — the disposition is written by the control
plane as a recorded system outcome (the BR-W-02 family), not by an agent
principal holding a review role.

**Step 2 — principle affected:** PR-1 ("the human gate is the product").
The principle itself is being narrowed, not just the rule; the owner must
decide this knowingly.

**Step 3 — impact on P-5, the worker:** exceptions affecting a worker could
be closed with no human ever seeing them. Mitigation offered: the tier is
per-site, off by default (BR-001 discipline), G5-gated, its use is audited
per mode-switch with the acting user's name, and accepted-by-machine events
never carry consequence weight (they are not Verified Records).

**Step 4 — regulatory exclusion table:** no new high-risk category is
entered *by this amendment alone* (no biometrics, no individual analytics).
The EU AI Act Article 14 human-oversight posture weakens and customer-facing
material must be reviewed (§8.4 final step).

**Engineering preconditions Kapil commits to regardless of approval shape:**

1. Only a **G1-released** model may ever hold machine-disposition authority.
   The current dev models fail their own cards' limitations sections; under
   this proposal they could never be granted the mode.
2. A new terminal status (e.g. `machine_screened`), never a write to
   `status='verified'`; `chk_decided_requires_reviewer` stays untouched; the
   bypass suite gains rows proving machine disposition cannot produce a
   Verified Record.
3. The mode switch is a per-site, audited, named-user act — exactly the
   BR-C-02 pattern rule activation already uses.

## 3. AMD-RB-06 — deliberately NOT proposed: person re-identification

The request included: *"identify that the thing or person is same."*

For a **person**, this is not proposed, and engineering recommends against
raising it. BR-006 (ABSOLUTE, ACTIVE) excludes identity matching outright,
and the rule book's own §4.4 note documents the consequence that matters
here: EU AI Act **Article 14(5)** attaches two-natural-person verification
duties to remote biometric identification. Guardian Lens escapes it *only
because* BR-006 holds. Person re-ID would therefore **legally mandate more
human verification while this proposal exists to reduce it** — the two asks
cancel each other. It is also RD-05 (scope creep reintroduces surveillance)
in its purest form.

For a **thing/incident**, the underlying need is real and needs no rule
change: one ongoing condition currently lands as dozens of near-identical
candidates. **Incident grouping** — same rule, same zone, same class,
within a bounded time window, folded into one reviewable incident with a
count — involves no identity, no biometric template, no cross-camera
matching, and is already half-expressed by `debounce_seconds` /
`dwell_seconds`. Engineering will build this as ordinary queue behaviour
unless the owner objects.

## 4. What happens while this is pending

Nothing machine-disposes anything. Compliant reviewer-workload relief —
confidence-ordered queue, flagged-first triage, incident grouping, and the
already-legal `expired` outcome for aged-out candidates (BR-W-02) — proceeds
as normal engineering work.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-08-14 | Initial proposal: AMD-RB-05 machine-disposition tier drafted per §8.4 steps 1–4; person re-ID declined with the Article 14(5) reversal argument; incident grouping identified as the no-amendment-needed alternative. | Kapil |
