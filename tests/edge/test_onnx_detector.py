"""OnnxDetector artefact loading and manifest verification (TRD 5.6).

onnxruntime is NOT installed in this environment — deliberately, because
model deployment is gated on GOVERNANCE.md 9 gate G1. These tests cover
everything BEFORE the runtime import: manifest validation and SHA-256
artefact verification, and the gate-naming error when the dependency is
absent. Inference itself is exercised once a gated model exists.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from guardian_lens_edge.detector import ModelVerificationError, OnnxDetector

MODEL_BYTES = b"not-a-real-onnx-graph-but-hashable"


@pytest.fixture
def artefact(tmp_path: Path) -> Path:
    path = tmp_path / "model.onnx"
    path.write_bytes(MODEL_BYTES)
    return path


def write_manifest(tmp_path: Path, **overrides: object) -> Path:
    manifest = {
        "version": "1.2.0",
        "artefact_sha256": hashlib.sha256(MODEL_BYTES).hexdigest(),
        "classes": ["person_without_helmet"],
    }
    manifest.update(overrides)
    path = tmp_path / "model.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_hash_mismatch_refuses_to_start(
    tmp_path: Path, artefact: Path
) -> None:
    manifest = write_manifest(
        tmp_path, artefact_sha256=hashlib.sha256(b"other").hexdigest()
    )
    with pytest.raises(ModelVerificationError) as excinfo:
        OnnxDetector(artefact, manifest)
    message = str(excinfo.value)
    assert "SHA-256 mismatch" in message
    assert "refuses" in message


def test_verification_happens_before_the_runtime_import(
    tmp_path: Path, artefact: Path
) -> None:
    # A tampered artefact must fail on the hash, never reach the runtime:
    # ModelVerificationError, not the missing-dependency RuntimeError.
    artefact.write_bytes(MODEL_BYTES + b"tampered")
    manifest = write_manifest(tmp_path)
    with pytest.raises(ModelVerificationError):
        OnnxDetector(artefact, manifest)


def test_missing_onnxruntime_names_gate_g1_and_the_dependency(
    tmp_path: Path, artefact: Path
) -> None:
    manifest = write_manifest(tmp_path)
    # Hash verifies; the next step is the lazy runtime import, which is
    # absent in this environment.
    with pytest.raises(RuntimeError) as excinfo:
        OnnxDetector(artefact, manifest)
    message = str(excinfo.value)
    assert "onnxruntime" in message
    assert "G1" in message


@pytest.mark.parametrize(
    "overrides",
    [
        {"version": None},
        {"artefact_sha256": None},
        {"classes": None},
    ],
)
def test_missing_required_manifest_fields_refuse(
    tmp_path: Path, artefact: Path, overrides: dict
) -> None:
    manifest_dict = {
        "version": "1.2.0",
        "artefact_sha256": hashlib.sha256(MODEL_BYTES).hexdigest(),
        "classes": ["person_without_helmet"],
    }
    for key, value in overrides.items():
        if value is None:
            manifest_dict.pop(key)
    path = tmp_path / "model.manifest.json"
    path.write_text(json.dumps(manifest_dict), encoding="utf-8")
    with pytest.raises(ModelVerificationError, match="required fields"):
        OnnxDetector(artefact, path)


def test_empty_class_list_refuses(tmp_path: Path, artefact: Path) -> None:
    manifest = write_manifest(tmp_path, classes=[])
    with pytest.raises(ModelVerificationError, match="non-empty"):
        OnnxDetector(artefact, manifest)


def test_malformed_hash_refuses(tmp_path: Path, artefact: Path) -> None:
    manifest = write_manifest(tmp_path, artefact_sha256="abc123")
    with pytest.raises(ModelVerificationError, match="64-char"):
        OnnxDetector(artefact, manifest)


def test_missing_manifest_refuses(tmp_path: Path, artefact: Path) -> None:
    with pytest.raises(ModelVerificationError, match="not found"):
        OnnxDetector(artefact, tmp_path / "absent.json")


def test_missing_artefact_refuses(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path)
    with pytest.raises(ModelVerificationError, match="artefact not found"):
        OnnxDetector(tmp_path / "absent.onnx", manifest)


def test_manifest_must_be_an_object(tmp_path: Path, artefact: Path) -> None:
    path = tmp_path / "model.manifest.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(ModelVerificationError, match="object"):
        OnnxDetector(artefact, path)
