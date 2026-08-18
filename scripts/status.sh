#!/usr/bin/env bash
# One-command health check for the whole dev stack — run from the repo root:
#
#   bash scripts/status.sh
#
# Checks every layer a real camera depends on and prints PASS/FAIL per line.
# Exit code 0 = everything answered; 1 = something needs attention.
set -u
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi

PG_USER="${POSTGRES_USER:-guardian}"
PG_PASS="${POSTGRES_PASSWORD:-guardian}"
PG_HOST="${POSTGRES_HOST:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
WEB_PORT="${GL_WEB_PORT:-5173}"
ADMIN_EMAIL="${GL_DEMO_ADMIN_EMAIL:-admin@guardianlens.local}"
ADMIN_PASSWORD="${GL_BOOTSTRAP_PASSWORD:-guardian-dev-1}"

FAILURES=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

echo "Guardian Lens status — $(date '+%Y-%m-%d %H:%M:%S')"

# 1. Database
if .venv/bin/python -c "
import psycopg
psycopg.connect('postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/postgres', connect_timeout=3).close()
" 2>/dev/null; then
  pass "PostgreSQL answering on ${PG_HOST}:${PG_PORT}"
else
  fail "PostgreSQL not reachable on ${PG_HOST}:${PG_PORT} — start it (this machine: var/start-db.sh)"
fi

# 2. API
if curl -sf -m 3 http://localhost:8000/api/v1/health >/dev/null 2>&1; then
  pass "API healthy on :8000"
else
  fail "API not answering on :8000 — is 'make run' up?"
fi

# 3. Review UI
if curl -sf -m 3 -o /dev/null "http://localhost:${WEB_PORT}" 2>/dev/null; then
  pass "Review UI serving on :${WEB_PORT}"
else
  fail "Review UI not serving on :${WEB_PORT}"
fi

# 4. Edge agent process
if pgrep -f "guardian_lens_edge" >/dev/null 2>&1; then
  pass "Edge agent process running (pid $(pgrep -f guardian_lens_edge | head -1))"
else
  fail "Edge agent not running — restart recipe: set -a; . .env; . var/edge.env; set +a; then the CLI in CAMERA_INTEGRATION.md §3"
fi

# 5 + 6. Server-side truth: agent health beat freshness, camera states
.venv/bin/python - "$ADMIN_EMAIL" "$ADMIN_PASSWORD" <<'PY'
import sys
from datetime import datetime, timezone
import httpx

email, password = sys.argv[1], sys.argv[2]
try:
    client = httpx.Client(base_url="http://localhost:8000", timeout=5)
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    agents = client.get("/api/v1/agents", headers=auth).json()
    cameras = client.get("/api/v1/cameras", headers=auth).json()
except Exception as exc:
    print(f"  FAIL  could not query the API as {email}: {exc}")
    sys.exit(1)

failures = 0
now = datetime.now(timezone.utc)
live_agents = [a for a in agents if a["status"] == "active"]
if not live_agents:
    print("  FAIL  no agent is active (no recent health beat)")
    failures += 1
for agent in live_agents:
    beat = agent.get("last_health_at")
    if beat is None:
        print(f"  FAIL  agent {agent['name']}: active but no health beat recorded")
        failures += 1
        continue
    age = (now - datetime.fromisoformat(beat)).total_seconds()
    if age <= 90:
        print(f"  PASS  agent {agent['name']}: health beat {int(age)}s ago")
    else:
        print(f"  FAIL  agent {agent['name']}: last health beat {int(age)}s ago (stale — beats should arrive every ~30s)")
        failures += 1

watched = [c for c in cameras if c["status"] != "disabled"]
if not watched:
    print("  FAIL  no enabled cameras")
    failures += 1
for cam in watched:
    if cam["status"] == "active":
        print(f"  PASS  camera {cam['name']}: active")
    else:
        print(f"  FAIL  camera {cam['name']}: {cam['status']}")
        failures += 1
sys.exit(1 if failures else 0)
PY
[ $? -ne 0 ] && FAILURES=$((FAILURES + 1))

echo
if [ "$FAILURES" -eq 0 ]; then
  echo "ALL CHECKS PASSED — the stack is healthy."
  echo "(Reminder: an empty review queue is CORRECT until a G1 model exists — NullDetector produces no candidates.)"
else
  echo "$FAILURES check(s) FAILED — see lines above."
  exit 1
fi
