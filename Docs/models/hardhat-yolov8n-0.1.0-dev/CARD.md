# Model card — `hardhat-yolov8n-0.1.0-dev`

**Status: DEV EVALUATION ONLY. This model has NOT passed gate G1 for site
deployment.** It is registered to exercise the detection pipeline end to end
in the development sandbox and to begin building the G1 evidence trail
(GOVERNANCE.md §9). It must not be deployed to any customer site.

| Field | Value |
|---|---|
| Architecture | YOLOv8n (3.0 M parameters, 8.1 GFLOPs), ONNX opset 17, 640×640 input |
| Source | `keremberke/yolov8n-hard-hat-detection` (Hugging Face), checkpoint `best.pt`, exported to ONNX locally on 2026-08-14 |
| Artefact | `var/models/hardhat-yolov8n.onnx` — SHA-256 in the manifest beside it; the edge agent refuses any artefact whose hash mismatches |
| Classes (model → manifest) | 0 `Hardhat` → `hardhat` (worn hard hat; triggers no rule) · 1 `NO-Hardhat` → `person_without_helmet` (head/person without hard hat; the `ppe_helmet` trigger vocabulary). The rename is semantic, not a behaviour change |
| Reported performance | mAP50 0.836 **on the upstream repository's own validation split** — not on any Guardian Lens site footage |
| Runtime | ~36 ms/frame on this dev machine's CPU (12th-gen i7), comfortably inside the 2 fps sampling budget |

## Known limitations (why G1 is not satisfied)

- **No held-out evaluation on site footage.** The upstream metric is on a
  public construction-imagery dataset; our cameras (indoor office Tapo at
  640×360) are far outside that distribution.
- **No condition-stratified evaluation** (night, rain, occlusion, distance) —
  a G1 requirement.
- **License caveat**: the checkpoint derives from ultralytics YOLOv8 training
  code (AGPL-3.0) and carries no explicit weight license upstream. Acceptable
  for internal development evaluation; **not acceptable for production
  distribution**. A production model should be trained with cleanly licensed
  tooling (e.g., YOLOX, Apache-2.0) on labelled site data.
- Expect false positives and misses; rejecting them in the review queue is the
  point — the human gate is the product.

## Approval scope

Approval of this version in the development tenant records who takes
responsibility for the **evaluation exercise**, per the BR-C-02 pattern. It is
not, and must not be read as, a G1 site-deployment approval: `deployed_at`
remains NULL and the database refuses deployment marking without it.
