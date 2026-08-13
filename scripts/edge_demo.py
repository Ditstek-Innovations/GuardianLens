"""Drive the running stack from a simulated site — TRD 20.2 step 4, dev form.

Usage (with `make run` already serving on :8000):

    make edge-demo
    # or: .venv/bin/python scripts/edge_demo.py --api http://localhost:8000

Logs in as the dev admin, ensures a camera + zone + ACTIVE rule exist
(activation is explicit and attributed — BR-001/BR-C-02), ensures an agent
principal and a registered model version exist, then composes the real edge
agent (guardian_lens_edge) against the live API: config pull, scenario run,
outbox, publish. The event lands in the review queue at :5173.

Agent principals and model versions DO have an API now (POST /api/v1/agents,
POST /api/v1/model-versions — WORKFLOW.md 7 gap 1, closed). This script keeps
seeding them directly in the tenant database because it must re-run
idempotently against the same 'demo-edge' agent, rotating its secret in
place; an operator registering a real device uses the API and receives the
one-time credential there.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psycopg
from argon2 import PasswordHasher

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from guardian_lens.db.urls import psycopg_url  # noqa: E402

TENANT = os.environ.get("GL_DEMO_TENANT", "pilot")
EMAIL = os.environ.get("GL_DEMO_ADMIN_EMAIL", "admin@guardianlens.local")
PASSWORD = os.environ.get("GL_BOOTSTRAP_PASSWORD", "guardian-dev-1")


def _items(payload: object) -> list:
    """List endpoints may return a bare array or an {items: []} envelope."""
    if isinstance(payload, dict):
        return payload.get("items") or []
    return payload if isinstance(payload, list) else []


def ensure_configuration(client: httpx.Client, token: str) -> tuple[str, str]:
    """Camera + zone + active rule via the API; returns (site_id, camera_id)."""
    auth = {"Authorization": f"Bearer {token}"}

    site = _items(client.get("/api/v1/sites", headers=auth).json())[0]
    site_id = site["id"]

    items = _items(client.get(
        "/api/v1/cameras", headers=auth, params={"site_id": site_id}
    ).json())
    if items:
        camera_id = items[0]["id"]
    else:
        camera_id = client.post(
            "/api/v1/cameras", headers=auth,
            json={"site_id": site_id, "name": "Bay 3 entrance",
                  "stream_url": "rtsp://demo:demo@192.168.1.50/stream2"},
        ).json()["id"]
        print(f"  camera created: {camera_id}")

    zitems = _items(client.get(
        "/api/v1/zones", headers=auth, params={"camera_id": camera_id}
    ).json())
    if zitems:
        zone_id = zitems[0]["id"]
    else:
        zone_id = client.post(
            "/api/v1/zones", headers=auth,
            json={"camera_id": camera_id, "name": "Bay 3",
                  "polygon": [[0.05, 0.05], [0.95, 0.05],
                              [0.95, 0.95], [0.05, 0.95]]},
        ).json()["id"]
        print(f"  zone created: {zone_id}")

    ritems = _items(client.get(
        "/api/v1/rules", headers=auth, params={"zone_id": zone_id}
    ).json())
    active = [r for r in ritems if r.get("is_active")]
    if not active:
        rule = next(iter(ritems), None)
        if rule is None:
            rule = client.post(
                "/api/v1/rules", headers=auth,
                json={"zone_id": zone_id, "rule_type": "ppe_helmet",
                      "confidence_threshold": 0.5, "debounce_seconds": 30,
                      "human_readable": "Helmet required in Bay 3",
                      "written_rule_reference": "Site safety manual 4.2"},
            ).json()
            print(f"  rule created: {rule['id']}")
        activated = client.post(
            f"/api/v1/rules/{rule['id']}/activate", headers=auth
        ).json()
        print(f"  rule activated by {activated['activated_by']['full_name']}"
              if isinstance(activated.get("activated_by"), dict)
              else "  rule activated")
    return site_id, camera_id


def ensure_agent_and_model(site_id: str) -> tuple[str, str]:
    """Seed the agent principal + model version (no API surface yet)."""
    url = os.environ.get(
        "GL_TENANT_DB_URL",
        f"postgresql+psycopg://guardian:guardian@localhost:5432/gl_tenant_{TENANT}",
    )
    with psycopg.connect(psycopg_url(url)) as conn:
        row = conn.execute(
            "SELECT id FROM agents WHERE name = 'demo-edge'"
        ).fetchone()
        secret = uuid.uuid4().hex
        if row:
            agent_id = str(row[0])
            conn.execute(
                "UPDATE agents SET credential_hash = %s WHERE id = %s",
                (PasswordHasher().hash(secret), agent_id),
            )
        else:
            agent_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO agents (id, site_id, name, credential_hash) "
                "VALUES (%s, %s, 'demo-edge', %s)",
                (agent_id, site_id, PasswordHasher().hash(secret)),
            )
            print(f"  agent registered: {agent_id}")
        conn.execute(
            "INSERT INTO model_versions (version, artefact_hash, classes) "
            "VALUES ('synthetic-0.0.0', 'sha256:synthetic', "
            "'[\"person_without_helmet\"]') ON CONFLICT (version) DO NOTHING"
        )
        conn.commit()
    return agent_id, secret


def run_edge(api: str, camera_id: str, site_id: str,
             agent_id: str, secret: str) -> None:
    from guardian_lens_edge.agent import EdgeAgent
    from guardian_lens_edge.auth import AgentAuthenticator
    from guardian_lens_edge.config_sync import ConfigSync
    from guardian_lens_edge.detector import SyntheticDetector
    from guardian_lens_edge.events import EventBuilder
    from guardian_lens_edge.frames import SyntheticSource
    from guardian_lens_edge.publisher import Publisher
    from guardian_lens_edge.rules import RuleEvaluator
    from guardian_lens_edge.scenario import Scenario
    from guardian_lens_edge.state import AgentStateMachine
    from guardian_lens_edge.store import EdgeStore

    tmp = Path(tempfile.mkdtemp(prefix="gl-edge-demo-"))
    now = datetime.now(timezone.utc)
    scenario = Scenario.from_list([
        {"at_seconds": 0.0, "camera_id": camera_id,
         "detections": [{"class": "person_without_helmet",
                         "bbox": [0.4, 0.4, 0.6, 0.85],
                         "confidence": 0.83}]},
        {"at_seconds": 1.0, "camera_id": camera_id, "detections": []},
    ])

    client = httpx.Client(base_url=api, timeout=10.0)
    store = EdgeStore(tmp / "outbox.db",
                      warning_bytes=50 * 1024 * 1024,
                      critical_bytes=100 * 1024 * 1024)
    authenticator = AgentAuthenticator(
        client, api, f"{TENANT}:{agent_id}:{secret}")
    agent = EdgeAgent(
        store=store,
        frame_source=SyntheticSource(scenario, start_at=now),
        detector=SyntheticDetector(scenario),
        evaluator=RuleEvaluator(store),
        builder=EventBuilder(store, tmp / "spool", agent_id),
        publisher=Publisher(store, client, api, authenticator),
        config_sync=ConfigSync(store, client, api, agent_id, authenticator),
        state=AgentStateMachine(store, failure_window=50,
                                degraded_failure_rate=0.2,
                                halt_failure_rate=0.5),
        agent_id=agent_id,
        site_id=site_id,
    )
    event_ids = agent.run_scenario(now=now)
    agent.publisher_tick(now)
    print(f"  edge agent emitted {len(event_ids)} candidate(s); "
          f"outbox pending: {store.pending_count()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api, timeout=10.0) as client:
        login = client.post("/api/v1/auth/login",
                            json={"email": EMAIL, "password": PASSWORD})
        if login.status_code != 200:
            print(f"login failed ({login.status_code}) — is `make run` up, "
                  f"and is GL_BOOTSTRAP_PASSWORD correct?", file=sys.stderr)
            return 1
        token = login.json()["access_token"]

        print(f"*** DEMO DATA: seeding synthetic configuration and events into "
              f"tenant '{TENANT}'. Never point this at a real site's tenant — "
              f"real tenants stay real-only (WORKFLOW.md 3b). ***")
        print("ensuring site configuration…")
        site_id, camera_id = ensure_configuration(client, token)
        print("ensuring agent principal + model version…")
        agent_id, secret = ensure_agent_and_model(site_id)
        print("running the edge agent against the live API…")
        run_edge(args.api, camera_id, site_id, agent_id, secret)

        auth = {"Authorization": f"Bearer {token}"}
        queue = client.get("/api/v1/events", headers=auth,
                           params={"status": "unverified"}).json()
        depth = queue.get("queue_depth", len(queue.get("items", [])))
        print(f"\nreview queue depth is now {depth} — open "
              f"http://localhost:5173 and decide it (A/R/C).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
