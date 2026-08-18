# Dataset datasheet — training data of `hardhat-yolov8n-0.1.0-dev`

**We did not train this model.** This datasheet records what is known about
the upstream training data, honestly including what is *not* known — which is
itself a reason the model cannot pass gate G1 for production.

| Field | Value |
|---|---|
| Dataset | "Hard Hat Detection" — a public Roboflow Universe dataset referenced by the upstream repository (`keremberke/yolov8n-hard-hat-detection`) |
| Contents | Construction-site imagery labelled with `Hardhat` / `NO-Hardhat` boxes |
| Collection provenance | **Unknown to us** — consent, geography, demographic coverage and labelling methodology are not documented upstream at the standard GOVERNANCE.md §9 requires |
| Guardian Lens site data included | **None.** No frame from any Guardian Lens camera, demo or real, was used in training |
| Known gaps | Indoor/office scenes (our dev camera's domain) are underrepresented; low-resolution sub-streams (640×360) likely underrepresented; no night/adverse-weather stratification available |

## Consequence

Any accuracy figure carried by this model describes the upstream validation
split of this dataset, nothing else. Claims about performance on a Guardian
Lens site require labelled footage from that site, measured per class and per
condition — the evaluation this dev registration exists to start.
