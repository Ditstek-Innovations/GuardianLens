"""Detectors — MOD-2 Inference Runner boundary (TRD 4).

``Detector.detect`` is IF-E2: the last point at which a model output
participates. Everything downstream is deterministic code
(ARCHITECTURE.md 5.2, BR-D-03).

The development form ships ``SyntheticDetector``, which replays detections
from a scenario file (see ``guardian_lens_edge.scenario`` for the schema) so
the full workflow runs with zero ML dependencies — the MVP tests the
workflow, not the detector (TRD 13.2).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from guardian_lens_edge.frames import Frame
from guardian_lens_edge.scenario import Scenario

__all__ = [
    "CompositeDetector",
    "Detection",
    "Detector",
    "ModelVerificationError",
    "NullDetector",
    "OnnxDetector",
    "SyntheticDetector",
]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detection:
    """IF-E2 payload: class, normalised bbox, confidence."""

    class_name: str
    bbox_norm: tuple[float, float, float, float]  # x1, y1, x2, y2 in 0-1
    confidence: float
    # Filled when multiple models analyse one frame so the candidate retains
    # the exact model that produced its triggering detection.
    model_version: str | None = None


class Detector(Protocol):
    @property
    def model_version(self) -> str | None:
        """Model version recorded on every event (FR-013); None for nvr."""
        ...

    def detect(self, frame: Frame) -> list[Detection]:
        ...


class SyntheticDetector:
    """Replays scripted detections for the frame's scenario entry.

    ``frame.sequence`` is the scenario entry index assigned by
    ``SyntheticSource``; both must be built from the same ``Scenario``.
    """

    def __init__(
        self, scenario: Scenario, *, model_version: str = "synthetic-0.0.0"
    ) -> None:
        self._scenario = scenario
        self._model_version = model_version

    @property
    def model_version(self) -> str:
        return self._model_version

    def detect(self, frame: Frame) -> list[Detection]:
        if not 0 <= frame.sequence < len(self._scenario.entries):
            return []
        entry = self._scenario.entries[frame.sequence]
        if entry.camera_id != frame.camera_id:
            return []
        return [
            Detection(
                class_name=detection.class_name,
                bbox_norm=detection.bbox,
                confidence=detection.confidence,
            )
            for detection in entry.detections
        ]


class NullDetector:
    """The rtsp-mode default until gate G1 admits a real model.

    Returns no detections and counts frames. This is DELIBERATE absence of
    a model, announced in the CLI help and in this docstring — not the
    silent-zero-detections failure RS-6 excludes, which is an agent that
    *claims* to detect and does not. With the NullDetector no detection
    rule can ever fire, so the site's monitored scope is exactly what the
    operator was told: stream ingestion only, no detection until a model
    passes GOVERNANCE.md 9 gate G1.
    """

    def __init__(self) -> None:
        self._frames_seen = 0

    @property
    def model_version(self) -> None:
        """No model is loaded, and no event can be built to carry one."""
        return None

    @property
    def frames_seen(self) -> int:
        return self._frames_seen

    def detect(self, frame: Frame) -> list[Detection]:
        self._frames_seen += 1
        if self._frames_seen == 1 or self._frames_seen % 30 == 0:
            logger.warning(
                "YOLO not loaded (NullDetector): camera=%s seq=%s frames=%d "
                "— no detections until --model and --model-manifest point at "
                "a verified ONNX artefact",
                frame.camera_id,
                frame.sequence,
                self._frames_seen,
            )
        return []


class CompositeDetector:
    """Run multiple verified detectors and retain per-detection provenance."""

    def __init__(self, detectors: list[Detector]) -> None:
        if len(detectors) < 2:
            raise ValueError("CompositeDetector requires at least two detectors")
        self._detectors = tuple(detectors)

    @property
    def model_version(self) -> str:
        return "+".join(
            version
            for detector in self._detectors
            if (version := detector.model_version) is not None
        )

    def detect(self, frame: Frame) -> list[Detection]:
        detections: list[Detection] = []
        for detector in self._detectors:
            version = detector.model_version
            detections.extend(
                Detection(
                    class_name=item.class_name,
                    bbox_norm=item.bbox_norm,
                    confidence=item.confidence,
                    model_version=version,
                )
                for item in detector.detect(frame)
            )
        return detections


class ModelVerificationError(Exception):
    """The model artefact failed manifest verification (TRD 5.6).

    Raised at construction so the agent refuses to start: it must never
    run without a verified model and never silently produce zero
    detections (RS-6).
    """


# Decode mechanics, not product thresholds: the [OPEN] per-rule confidence
# threshold (TRD 5.5) is applied downstream by D1 row 2. These only strip
# numerically-meaningless boxes before NMS, standard for YOLO decoding.
_DECODE_SCORE_FLOOR = 0.05
_NMS_IOU_THRESHOLD = 0.45
_DEFAULT_INPUT_SIZE = 640

_MANIFEST_REQUIRED_FIELDS = ("version", "artefact_sha256", "classes")


class OnnxDetector:
    """ONNX-Runtime detector — MOD-2 Inference Runner (TRD 4).

    Deployment of any real model remains gated on GOVERNANCE.md 9 gate G1
    (model card, datasheets, held-out + condition-stratified evaluation,
    challenge sign-off); this class is the loading/inference machinery
    that gate-approved artefacts will run on. ``onnxruntime`` is NOT a
    project dependency — it is imported lazily and its absence is reported
    naming the gate, so nothing can run an ungated model by accident.

    Artefact layout (mirrors ``model_versions``, TRD 9.10):

    * ``model_path`` — the ONNX file (opset 17+, TRD 5.7).
    * ``manifest_path`` — JSON with required fields ``version`` (semver),
      ``artefact_sha256`` (64 hex chars, SHA-256 of the ONNX file) and
      ``classes`` (ordered class-id → name list); optional ``input_size``
      (square model input edge, default 640).

    Verification: the artefact's SHA-256 is recomputed and compared to the
    manifest before anything is loaded. On mismatch the constructor raises
    :class:`ModelVerificationError` — the agent refuses to start rather
    than run an unverified model (TRD 5.6 "never run without a model";
    ARCHITECTURE.md 6.7 step "verify SHA-256 against manifest"). The class
    list is the BR-006 surface reviewed at gate G1: only detection classes,
    never identity, biometric or re-identification outputs.

    Pipeline per TRD 5.2: letterbox resize preserving aspect ratio,
    normalise to [0,1] RGB CHW float32, single-image batch, YOLO-family
    output decode (v8 ``(1, 4+nc, N)`` and v5 ``(1, N, 5+nc)`` layouts),
    class-wise NMS, boxes mapped back to normalised original-image space.
    """

    def __init__(
        self, model_path: str | Path, manifest_path: str | Path
    ) -> None:
        self._model_path = Path(model_path)
        manifest = self._load_manifest(Path(manifest_path))
        self._verify_artefact_hash(manifest["artefact_sha256"])
        self._model_version = str(manifest["version"])
        self._classes: list[str] = [str(c) for c in manifest["classes"]]
        self._input_size = int(
            manifest.get("input_size", _DEFAULT_INPUT_SIZE)
        )
        if self._input_size <= 0:
            raise ModelVerificationError(
                "manifest input_size must be positive"
            )
        self._session = self._create_session()
        self._input_name = self._session.get_inputs()[0].name
        self._warm_up()
        self._frames_seen = 0
        logger.info(
            "YOLO model ready: version=%s classes=%d input=%d artefact=%s "
            "classes_sample=%s",
            self._model_version,
            len(self._classes),
            self._input_size,
            self._model_path.name,
            self._classes[:12],
        )

    @property
    def model_version(self) -> str:
        """Recorded on every detection/event (FR-013)."""
        return self._model_version

    # ------------------------------------------------------------------
    # Artefact loading and verification
    # ------------------------------------------------------------------

    def _load_manifest(self, manifest_path: Path) -> dict:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ModelVerificationError(
                f"model manifest not found: {manifest_path}"
            ) from exc
        except (OSError, ValueError) as exc:
            raise ModelVerificationError(
                f"model manifest unreadable or not JSON: {exc}"
            ) from exc
        if not isinstance(manifest, dict):
            raise ModelVerificationError("model manifest must be an object")
        missing = [
            key for key in _MANIFEST_REQUIRED_FIELDS if key not in manifest
        ]
        if missing:
            raise ModelVerificationError(
                f"model manifest missing required fields: {missing}"
            )
        classes = manifest["classes"]
        if not isinstance(classes, list) or not classes:
            raise ModelVerificationError(
                "model manifest classes must be a non-empty list"
            )
        return manifest

    def _verify_artefact_hash(self, expected_hex: object) -> None:
        expected = str(expected_hex).lower()
        if len(expected) != 64:
            raise ModelVerificationError(
                "manifest artefact_sha256 is not a 64-char SHA-256 hex digest"
            )
        digest = hashlib.sha256()
        try:
            with self._model_path.open("rb") as artefact:
                for chunk in iter(lambda: artefact.read(1 << 20), b""):
                    digest.update(chunk)
        except FileNotFoundError as exc:
            raise ModelVerificationError(
                f"model artefact not found: {self._model_path}"
            ) from exc
        actual = digest.hexdigest()
        if actual != expected:
            # Refuse to start (TRD 5.6): a hash mismatch means this is not
            # the artefact the manifest (and gate G1 review) describes.
            raise ModelVerificationError(
                "model artefact SHA-256 mismatch: manifest declares "
                f"{expected} but {self._model_path.name} hashes to "
                f"{actual}; the agent refuses to run an unverified model"
            )

    def _create_session(self):  # -> onnxruntime.InferenceSession
        try:
            import onnxruntime  # noqa: PLC0415 — lazy on purpose: not a
            # dependency; see the class docstring.
        except ImportError as exc:
            raise RuntimeError(
                "onnxruntime is not installed. Real detection is gated on "
                "GOVERNANCE.md 9 gate G1 (model release); once a model "
                "passes the gate, install the missing dependency "
                "'onnxruntime' explicitly to enable OnnxDetector. The "
                "agent otherwise runs with NullDetector (ingestion only) "
                "or SyntheticDetector (TRD 13.2)."
            ) from exc
        return onnxruntime.InferenceSession(
            str(self._model_path),
            providers=["CPUExecutionProvider"],  # CPU [MVP], TRD 5.3
        )

    def _warm_up(self) -> None:
        """One inference on zeros at start (TRD 5.3): the first real frame
        must not pay the graph-optimisation latency spike."""
        import numpy  # noqa: PLC0415 — lazy: ships with the edge-camera extra

        zeros = numpy.zeros(
            (1, 3, self._input_size, self._input_size), dtype=numpy.float32
        )
        self._session.run(None, {self._input_name: zeros})

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def detect(self, frame: Frame) -> list[Detection]:
        """Frame → detections. Exceptions propagate: the agent's MOD-2
        failure row (drop, count, continue; sustained → degraded) handles
        them, so nothing is swallowed here."""
        import numpy  # noqa: PLC0415 — lazy, see class docstring

        image = self._decode_image(frame)
        tensor, scale, pad_x, pad_y = self._letterbox(image, numpy)
        outputs = self._session.run(None, {self._input_name: tensor})
        boxes, scores, class_ids = self._decode_output(outputs[0], numpy)
        keep = _non_maximum_suppression(
            boxes, scores, class_ids, _NMS_IOU_THRESHOLD, numpy
        )
        height, width = image.shape[:2]
        detections: list[Detection] = []
        for index in keep:
            class_id = int(class_ids[index])
            if not 0 <= class_id < len(self._classes):
                logger.warning(
                    "model emitted unknown class id %d; detection dropped",
                    class_id,
                )
                continue
            x1, y1, x2, y2 = boxes[index]
            # Undo the letterbox, then normalise to the original image.
            x1 = (x1 - pad_x) / scale / width
            y1 = (y1 - pad_y) / scale / height
            x2 = (x2 - pad_x) / scale / width
            y2 = (y2 - pad_y) / scale / height
            detections.append(
                Detection(
                    class_name=self._classes[class_id],
                    bbox_norm=(
                        float(min(max(x1, 0.0), 1.0)),
                        float(min(max(y1, 0.0), 1.0)),
                        float(min(max(x2, 0.0), 1.0)),
                        float(min(max(y2, 0.0), 1.0)),
                    ),
                    confidence=float(scores[index]),
                )
            )
        self._frames_seen += 1
        if self._frames_seen == 1 or self._frames_seen % 30 == 0:
            top = ", ".join(
                f"{item.class_name}={item.confidence:.2f}"
                for item in detections[:8]
            ) or "(none)"
            logger.info(
                "YOLO inference ok: version=%s camera=%s seq=%s "
                "detections=%d [%s]",
                self._model_version,
                frame.camera_id,
                frame.sequence,
                len(detections),
                top,
            )
        return detections

    def _decode_image(self, frame: Frame):  # -> numpy.ndarray (BGR)
        import cv2  # noqa: PLC0415 — lazy on purpose (TRD 13.2)
        import numpy  # noqa: PLC0415

        if frame.image_bytes is not None:
            raw = frame.image_bytes
        else:
            path = Path(frame.image_ref)
            if not path.exists():
                raise ValueError(
                    f"frame carries no image bytes and no readable file: "
                    f"{frame.image_ref}"
                )
            raw = path.read_bytes()
        image = cv2.imdecode(
            numpy.frombuffer(raw, dtype=numpy.uint8), cv2.IMREAD_COLOR
        )
        if image is None:
            raise ValueError("frame image failed to decode")
        return image

    def _letterbox(self, image, numpy):
        """TRD 5.2: letterbox resize preserving aspect ratio, normalise,
        convert to the model input tensor. Returns (tensor, scale, pad_x,
        pad_y) so boxes can be mapped back."""
        import cv2  # noqa: PLC0415 — lazy on purpose (TRD 13.2)

        size = self._input_size
        height, width = image.shape[:2]
        scale = min(size / width, size / height)
        new_width = max(1, round(width * scale))
        new_height = max(1, round(height * scale))
        pad_x = (size - new_width) // 2
        pad_y = (size - new_height) // 2
        resized = cv2.resize(
            image, (new_width, new_height), interpolation=cv2.INTER_LINEAR
        )
        canvas = numpy.full((size, size, 3), 114, dtype=numpy.uint8)
        canvas[
            pad_y : pad_y + new_height, pad_x : pad_x + new_width
        ] = resized
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = rgb.astype(numpy.float32) / 255.0
        tensor = tensor.transpose(2, 0, 1)[numpy.newaxis, ...]
        return numpy.ascontiguousarray(tensor), scale, pad_x, pad_y

    def _decode_output(self, output, numpy):
        """YOLO-family raw output → (boxes_xyxy, scores, class_ids).

        Handles the v8 layout ``(1, 4+nc, N)`` (xywh + per-class scores)
        and the v5 layout ``(1, N, 5+nc)`` (xywh + objectness + scores).
        """
        raw = numpy.asarray(output)
        if raw.ndim != 3 or raw.shape[0] != 1:
            raise ValueError(
                f"unsupported model output shape {raw.shape}; expected a "
                "single-batch YOLO-family head"
            )
        class_count = len(self._classes)
        if raw.shape[1] == 4 + class_count and raw.shape[2] != 5 + class_count:
            predictions = raw[0].T  # (N, 4+nc)
            class_scores = predictions[:, 4:]
            confidences = class_scores.max(axis=1)
            class_ids = class_scores.argmax(axis=1)
        elif raw.shape[2] == 5 + class_count:
            predictions = raw[0]  # (N, 5+nc)
            objectness = predictions[:, 4]
            class_scores = predictions[:, 5:]
            confidences = objectness * class_scores.max(axis=1)
            class_ids = class_scores.argmax(axis=1)
        else:
            raise ValueError(
                f"model output shape {raw.shape} does not match the "
                f"manifest's {class_count} classes"
            )
        keep = confidences >= _DECODE_SCORE_FLOOR
        predictions = predictions[keep]
        confidences = confidences[keep]
        class_ids = class_ids[keep]
        # xywh (centre) -> xyxy in model-input pixel space.
        centre_x, centre_y = predictions[:, 0], predictions[:, 1]
        half_w, half_h = predictions[:, 2] / 2.0, predictions[:, 3] / 2.0
        boxes = numpy.stack(
            [
                centre_x - half_w,
                centre_y - half_h,
                centre_x + half_w,
                centre_y + half_h,
            ],
            axis=1,
        )
        return boxes, confidences, class_ids


def _non_maximum_suppression(boxes, scores, class_ids, iou_threshold, numpy):
    """Greedy class-wise NMS; returns the kept indices, best-first."""
    kept: list[int] = []
    order = numpy.argsort(scores)[::-1]
    while order.size > 0:
        best = int(order[0])
        kept.append(best)
        if order.size == 1:
            break
        rest = order[1:]
        same_class = class_ids[rest] == class_ids[best]
        overlap = _iou(boxes[best], boxes[rest], numpy)
        suppressed = same_class & (overlap > iou_threshold)
        order = rest[~suppressed]
    return kept


def _iou(box, others, numpy):
    x1 = numpy.maximum(box[0], others[:, 0])
    y1 = numpy.maximum(box[1], others[:, 1])
    x2 = numpy.minimum(box[2], others[:, 2])
    y2 = numpy.minimum(box[3], others[:, 3])
    intersection = numpy.clip(x2 - x1, 0, None) * numpy.clip(y2 - y1, 0, None)
    area_box = (box[2] - box[0]) * (box[3] - box[1])
    area_others = (others[:, 2] - others[:, 0]) * (others[:, 3] - others[:, 1])
    union = area_box + area_others - intersection
    return numpy.where(union > 0, intersection / union, 0.0)
