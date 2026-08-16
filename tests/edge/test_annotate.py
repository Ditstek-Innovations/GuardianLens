"""Evidence annotation — the mark and the zoom, and the never-lose-evidence
posture (annotation failure returns the original bytes unchanged)."""

from __future__ import annotations

import pytest

from guardian_lens_edge.annotate import annotate_evidence

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


def _plain_jpeg(width: int = 640, height: int = 360) -> bytes:
    image = np.full((height, width, 3), 128, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


def test_annotation_marks_the_frame_and_stays_a_decodable_jpeg():
    original = _plain_jpeg()
    annotated = annotate_evidence(original, (0.4, 0.4, 0.6, 0.6), "Mobile phone in use 32%")
    assert annotated != original
    decoded = cv2.imdecode(np.frombuffer(annotated, np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[:2] == (360, 640)  # same frame, decorated — never resized
    # The box colour appears where the detection was drawn.
    region = decoded[130:230, 240:400]
    greenish = (region[:, :, 1].astype(int) - region[:, :, 2].astype(int)) > 60
    assert bool(greenish.any())


def test_degenerate_or_out_of_range_boxes_return_the_original_bytes():
    original = _plain_jpeg()
    assert annotate_evidence(original, (0.5, 0.5, 0.5, 0.5), "x") == original
    assert annotate_evidence(original, (1.2, 1.2, 1.4, 1.4), "x") == original


def test_garbage_bytes_are_returned_unchanged_not_raised():
    garbage = b"not a jpeg at all"
    assert annotate_evidence(garbage, (0.1, 0.1, 0.9, 0.9), "x") == garbage
