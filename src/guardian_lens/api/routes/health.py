"""Health routes — TRD 10.7. The only unauthenticated routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response

from guardian_lens import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/health/ready")
def readiness(request: Request, response: Response) -> dict[str, Any]:
    # Control DB reachable and evidence store usable. Tenant databases are
    # deliberately not probed here: readiness gates traffic admission, and
    # one drifted tenant must not take the whole plane out.
    database_ok = request.app.state.tenant_registry.health_check()
    evidence_ok = request.app.state.evidence_store.healthy()
    ok = database_ok and evidence_ok
    if not ok:
        response.status_code = 503
    return {
        "status": "ok" if ok else "degraded",
        "checks": {
            "database": "ok" if database_ok else "unavailable",
            "evidence_store": "ok" if evidence_ok else "unavailable",
        },
    }
