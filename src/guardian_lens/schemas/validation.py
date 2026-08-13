"""Schema validation with TRD 10.8 error translation.

Lives in schemas/ because it is contract-layer logic with no HTTP
dependence — both controllers and the decision ladder use it.

Routes that must inspect the RAW body before validation (the
forbidden-field rules of TRD 10.3/10.4) cannot let FastAPI validate the
model for them — FastAPI would 422 before the rule's 400 could fire. Those
routes read the body as JSON and validate here, so the 400-before-422
ordering is preserved and the 422 still carries field-level detail.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from guardian_lens.core.errors import MalformedRequestError, ValidationFailureError

ModelT = TypeVar("ModelT", bound=BaseModel)


def require_json_object(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise MalformedRequestError("request body must be a JSON object")
    return data


def validate_model(model_type: type[ModelT], data: dict[str, Any]) -> ModelT:
    """Validate, translating the first Pydantic error into the envelope's
    field-level 422."""
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first["loc"]) or None
        raise ValidationFailureError(first["msg"], field=field) from exc
