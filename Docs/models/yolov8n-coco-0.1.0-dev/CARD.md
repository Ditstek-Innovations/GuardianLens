# Model card — `yolov8n-coco-0.1.0-dev`

**Status: DEV EVALUATION ONLY. This model has NOT passed gate G1 for site
deployment.** It is registered to exercise dynamic, per-rule detection-class
wiring end to end in the development sandbox — any of its 80 classes can now
back a rule created through the API, without a new model per rule. It must
not be deployed to any customer site.

| Field | Value |
|---|---|
| Architecture | YOLOv8n (3.2 M parameters, 8.7 GFLOPs), ONNX opset 17, 640×640 input |
| Source | `ultralytics` package's own stock checkpoint (`yolov8n.pt`, COCO-pretrained), exported to ONNX locally on 2026-08-14 |
| Artefact | `var/models/yolov8n-coco.onnx` — SHA-256 in the manifest beside it; the edge agent refuses any artefact whose hash mismatches |
| Classes (model → manifest) | All 80 COCO classes, unrenamed (`person`, `backpack`, `handbag`, `cell phone`, `bottle`, `chair`, `laptop`, `book`, … — see the manifest for the full list). Unlike `hardhat-yolov8n`, no class is pre-bound to a rule; a rule's `detection_class` selects which one it watches for |
| Reported performance | Ultralytics' published COCO val2017 mAP50-95 ≈ 0.37 for this checkpoint size — **not measured on any Guardian Lens site footage** |
| Runtime | Comparable to the hardhat checkpoint (same architecture/size) — a few tens of ms/frame on CPU, inside the 2 fps sampling budget |

## Known limitations (why G1 is not satisfied)

- **No held-out evaluation on site footage, for any of the 80 classes.**
  COCO is general-purpose internet imagery; our cameras (indoor office Tapo
  at 640×360) are a different distribution for every class, not just one.
- **No condition-stratified evaluation** (night, rain, occlusion, distance) —
  a G1 requirement.
- **License caveat**: same as `hardhat-yolov8n` — the checkpoint derives from
  ultralytics YOLOv8 (AGPL-3.0), acceptable for internal development
  evaluation, **not acceptable for production distribution**.
- **A general-purpose model is a wider net, not a safer one.** Because any of
  its 80 classes can be wired to a rule dynamically, this model makes it
  *easy* to create a rule that isn't a safety condition at all — that
  judgment call is not something the model, the manifest, or this pipeline
  can make. See the change log entry for this integration for the boundary
  RULE_BOOK.md BR-002/BR-006 already draw around what a `detection_class`
  may legitimately be used for.
- Expect false positives and misses, same as any dev-evaluation model;
  rejecting them in the review queue is the point.

## Approval scope

Approval of this version in the development tenant records who takes
responsibility for the **evaluation exercise**, per the BR-C-02 pattern. It
is not, and must not be read as, a G1 site-deployment approval: `deployed_at`
remains NULL and the database refuses deployment marking without it.
