# Guardian Lens — Running a Detection Model (Dev Evaluation)

**How to put a real detection model behind a camera in the development
sandbox: obtain, verify, register, run — and what to expect**

| Field | Value |
|---|---|
| Document | Technical runbook (Diátaxis: **how-to**). Companion to [CAMERA_INTEGRATION.md](CAMERA_INTEGRATION.md) — do that first; this adds the detection layer |
| Version | 1.0 |
| Date | 14 August 2026 |
| Owner | Kuldeep (Product) |
| Status | **Dev evaluation only.** Nothing here is a G1 site-deployment approval — [GOVERNANCE.md](GOVERNANCE.md) §9 still gates any model reaching a customer site |

---

## 0. What already exists (nothing to build)

- `OnnxDetector` (edge): SHA-256 artefact verification against a manifest,
  YOLOv5/v8 output decode, NMS. It refuses to start on any hash mismatch.
- Edge CLI flags: `--model <file.onnx> --model-manifest <manifest.json>`
  (both together, rtsp mode). Without them the agent runs `NullDetector` —
  ingestion only.
- `POST /api/v1/model-versions` + `/approve` — the registration/evidence
  trail. Approval requires model-card and datasheet references.
- A worked example: `hardhat-yolov8n-0.1.0-dev`, with its honest card and
  datasheet in [models/hardhat-yolov8n-0.1.0-dev/](models/hardhat-yolov8n-0.1.0-dev/) —
  read the card's **limitations** section before expecting miracles.

The one contract to know: the rule evaluator fires `ppe_helmet` rules on the
detection class named **`person_without_helmet`** (see
`guardian_lens_edge/config.py`). Your manifest maps the model's class ids to
names — the "no hard hat" class must be named exactly that.

## 1. Get the model artefact (once per machine, ~10 min)

Model binaries are **not committed** (gitignored under `var/models/`); each
dev machine produces its own and pins it by hash. From the repo root:

```bash
# 1a. Download the pretrained checkpoint (YOLOv8n hard-hat, ~6 MB)
mkdir -p var/models
curl -sL -o var/models/hardhat-yolov8n.pt \
  "https://huggingface.co/keremberke/yolov8n-hard-hat-detection/resolve/main/best.pt"

# 1b. Export to ONNX in a THROWAWAY venv (keeps torch/ultralytics out of .venv)
python3 -m venv /tmp/gl-export-venv
/tmp/gl-export-venv/bin/pip install -q -U pip ultralytics onnx
/tmp/gl-export-venv/bin/python -c "
from ultralytics import YOLO
m = YOLO('var/models/hardhat-yolov8n.pt')
print('classes:', m.names)   # expect {0: 'Hardhat', 1: 'NO-Hardhat'}
m.export(format='onnx', opset=17, imgsz=640)"
rm -rf /tmp/gl-export-venv   # done with it

# 1c. Generate the manifest with YOUR artefact's hash
.venv/bin/python - <<'EOF'
import hashlib, json
from pathlib import Path
sha = hashlib.sha256(Path("var/models/hardhat-yolov8n.onnx").read_bytes()).hexdigest()
Path("var/models/hardhat-yolov8n.manifest.json").write_text(json.dumps({
    "version": "hardhat-yolov8n-0.1.0-dev",
    "artefact_sha256": sha,
    "classes": ["hardhat", "person_without_helmet"],  # id 0, id 1 — see Docs/models/.../CARD.md
    "input_size": 640,
}, indent=2) + "\n")
print("manifest written; sha256:", sha)
EOF

# 1d. Enable the runtime — a deliberate, explicit step (see OnnxDetector docstring)
.venv/bin/pip install onnxruntime
```

## 2. Register it through the front door (once per tenant)

The registration is the evidence trail — do not skip it. As a site_admin
token (dev sandbox: `admin@guardianlens.local`):

```bash
.venv/bin/python - <<'EOF'
import hashlib, httpx
from pathlib import Path
sha = hashlib.sha256(Path("var/models/hardhat-yolov8n.onnx").read_bytes()).hexdigest()
c = httpx.Client(base_url="http://localhost:8000", timeout=15)
t = c.post("/api/v1/auth/login", json={"email": "admin@guardianlens.local",
                                       "password": "guardian-dev-1"}).json()["access_token"]
auth = {"Authorization": f"Bearer {t}"}
mv = c.post("/api/v1/model-versions", headers=auth, json={
    "version": "hardhat-yolov8n-0.1.0-dev",
    "artefact_hash": f"sha256:{sha}",
    "classes": ["hardhat", "person_without_helmet"],
    "model_card_ref": "Docs/models/hardhat-yolov8n-0.1.0-dev/CARD.md",
    "datasheet_ref": "Docs/models/hardhat-yolov8n-0.1.0-dev/DATASHEET.md",
    "notes": "DEV EVALUATION ONLY - not G1-approved for site deployment.",
}).json()
approved = c.post(f"/api/v1/model-versions/{mv['id']}/approve", headers=auth).json()
print("registered + approved:", approved["version"], "by", approved["approved_by"])
EOF
```

(409 on the first call = already registered on this tenant; that's fine.)

## 3. Run the edge agent with the model

Exactly the [CAMERA_INTEGRATION.md](CAMERA_INTEGRATION.md) §3 command, plus
the two model flags:

```bash
set -a; . ./.env; . ./var/edge.env; set +a
.venv/bin/python -m guardian_lens_edge --source rtsp \
  --api http://localhost:8000 \
  --agent-id "$GL_AGENT_ID" --site "$GL_SITE_ID" \
  --data-dir var/edge-data \
  --outbox-warning-bytes 52428800 --outbox-critical-bytes 104857600 \
  --failure-window 50 --degraded-failure-rate 0.2 --halt-failure-rate 0.5 \
  --decode-failure-threshold 10 \
  --model var/models/hardhat-yolov8n.onnx \
  --model-manifest var/models/hardhat-yolov8n.manifest.json
```

Look for this line in the log — it means the hash verified and the model is
live: `OnnxDetector loaded: model_version=hardhat-yolov8n-0.1.0-dev`.
If the file was tampered with or the manifest is stale, the agent **refuses
to start** — regenerate the manifest (step 1c).

## 4. The wave test — seeing the whole product work

Walk into the camera's view **without a hard hat**. Within ~a minute:

1. The model flags `person_without_helmet` on a sampled frame; the rule
   fires (threshold ≥ 0.5, then 30 s debounce before it can fire again).
2. A candidate lands in the **Review queue** — photo, rule text, confidence.
   This queue is the one and only place raw model output appears, always
   labelled Unverified.
3. Press **A** to accept or **R** to reject. Your decision, under your name,
   is what becomes (or doesn't become) a record.
4. **Reports** now shows real verified counts, the decision mix, and the
   analysis charts — fed only by what humans confirmed.

Expect noise: an office is not a construction site, and this checkpoint has
never seen your footage (card §limitations). **Rejecting its mistakes is not
a failure of the demo — it is the demo**: the human gate doing its job.

## 5. What this is building toward

Every rejected false positive and missed detection observed here is exactly
the evidence G1 asks for. The production path stays what
[CAMERA_INTEGRATION.md](CAMERA_INTEGRATION.md) §6 says: cleanly-licensed
training (e.g. YOLOX), labelled site footage, held-out + condition-stratified
evaluation, then G1 approval — and the same flags on the same agent.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-08-14 | Initial runbook: obtain/export/verify a dev hard-hat model, register + approve through /model-versions, run with --model flags, the wave test, honest expectations. | Kuldeep |
