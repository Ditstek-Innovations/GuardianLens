"""Evidence annotation — mark WHAT fired and WHERE on the proof frame.

The evidence stays exactly what BR-008 requires — one still JPEG — but a
reviewer should not have to hunt for a phone-sized object in a full frame.
The annotated evidence carries:

  * the detection's bounding box, drawn on the frame;
  * a label naming the rule and the confidence;
  * a magnified inset of the detection region ("the zoom"), pasted into a
    corner with a matching border.

Failure posture: annotation is best-effort decoration of evidence, never a
condition of it. Any error — cv2 absent (synthetic deployments), decode
failure, degenerate box — returns the ORIGINAL bytes unchanged. Losing a
candidate's evidence to a drawing bug would invert the priority.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: The inset is scaled so its width is this fraction of the frame width.
_INSET_FRACTION = 0.33
#: Context margin added around the detection box before cropping the inset.
_CROP_MARGIN = 0.15
_BOX_COLOR = (64, 220, 46)  # BGR — high-visibility green
_TEXT_COLOR = (0, 0, 0)


def annotate_evidence(
    jpeg: bytes,
    bbox_norm: tuple[float, float, float, float],
    label: str,
) -> bytes:
    """Return the frame with the detection marked and magnified.

    ``bbox_norm`` is (x1, y1, x2, y2) in 0–1 image space, the evaluator's
    own convention. On any failure the input bytes come back unchanged.
    """
    try:
        return _annotate(jpeg, bbox_norm, label)
    except Exception:  # noqa: BLE001 — decoration must never cost evidence
        logger.warning("evidence annotation failed; using the plain frame")
        return jpeg


def _annotate(
    jpeg: bytes,
    bbox_norm: tuple[float, float, float, float],
    label: str,
) -> bytes:
    import cv2  # lazy — synthetic deployments run without OpenCV
    import numpy as np

    image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return jpeg
    height, width = image.shape[:2]

    x1 = max(0, min(width - 1, int(bbox_norm[0] * width)))
    y1 = max(0, min(height - 1, int(bbox_norm[1] * height)))
    x2 = max(0, min(width, int(bbox_norm[2] * width)))
    y2 = max(0, min(height, int(bbox_norm[3] * height)))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return jpeg

    # The magnified inset FIRST, cropped from the clean frame so the box
    # lines are not magnified along with the pixels.
    margin_x = int((x2 - x1) * _CROP_MARGIN)
    margin_y = int((y2 - y1) * _CROP_MARGIN)
    crop = image[
        max(0, y1 - margin_y) : min(height, y2 + margin_y),
        max(0, x1 - margin_x) : min(width, x2 + margin_x),
    ].copy()

    thickness = max(2, width // 640)
    cv2.rectangle(image, (x1, y1), (x2, y2), _BOX_COLOR, thickness)

    # Label above the box (below it when the box touches the top edge).
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.5, width / 1600)
    (text_w, text_h), baseline = cv2.getTextSize(label, font, scale, thickness)
    label_y = y1 - 6 if y1 - text_h - 10 > 0 else y2 + text_h + 6
    cv2.rectangle(
        image,
        (x1, label_y - text_h - baseline),
        (x1 + text_w + 6, label_y + baseline),
        _BOX_COLOR,
        -1,
    )
    cv2.putText(
        image, label, (x1 + 3, label_y), font, scale, _TEXT_COLOR,
        thickness, cv2.LINE_AA,
    )

    # Paste the zoom inset top-right (top-left if the box is up there).
    if crop.size > 0:
        inset_w = max(1, int(width * _INSET_FRACTION))
        inset_h = max(1, int(crop.shape[0] * (inset_w / crop.shape[1])))
        if inset_h < height - 2 * thickness:
            inset = cv2.resize(
                crop, (inset_w, inset_h), interpolation=cv2.INTER_CUBIC
            )
            cv2.rectangle(
                inset, (0, 0), (inset_w - 1, inset_h - 1), _BOX_COLOR, thickness
            )
            place_left = x1 > width // 2
            x_off = thickness if place_left else width - inset_w - thickness
            image[thickness : thickness + inset_h, x_off : x_off + inset_w] = inset

    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return encoded.tobytes() if ok else jpeg
