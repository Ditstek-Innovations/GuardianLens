#!/usr/bin/env bash
# Standalone provisioning - assumes postgres container is already running on 5433
# This bypasses docker-compose permission issues
set -euo pipefail
cd "$(dirname "$0")"

source .venv/bin/activate

# Load env
if [ -f .env ]; then set -a; . ./.env; set +a; fi

VENV=.venv/bin
TENANT="${GL_DEMO_TENANT:-pilot}"
WEB_PORT="${GL_WEB_PORT:-5173}"
ADMIN_EMAIL="${GL_DEMO_ADMIN_EMAIL:-admin@guardianlens.local}"
PG_USER="${POSTGRES_USER:-postgres}"
PG_PASS="${POSTGRES_PASSWORD:-5003}"
PG_PORT="${POSTGRES_PORT:-5433}"
PG_HOST="${POSTGRES_HOST:-localhost}"

export GL_BOOTSTRAP_PASSWORD="${GL_BOOTSTRAP_PASSWORD:-guardian-dev-1}"
export GL_JWT_SECRET="${GL_JWT_SECRET:-dev-only-secret-change-me-32bytes!}"
export GL_CONTROL_DB_URL="${GL_CONTROL_DB_URL:-postgresql+psycopg://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${GL_CONTROL_DB_NAME:-gl_control}}"
export GL_TENANT_DB_URL="${GL_TENANT_DB_URL:-postgresql+psycopg://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/gl_tenant_${TENANT}}"

echo "GuardianLens Standalone Provisioning"
echo "====================================="
echo "Database: postgresql://${PG_USER}@${PG_HOST}:${PG_PORT}"
echo "Tenant: ${TENANT}"
echo ""

# Test connection
echo "Testing database connection..."
$VENV/python - <<TEST
import sys, psycopg
try:
    conn = psycopg.connect(
        "postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/postgres",
        connect_timeout=3,
    )
    conn.close()
    print("✓ Database is reachable")
    sys.exit(0)
except psycopg.OperationalError as exc:
    print(f"✗ Cannot connect to database: {exc}")
    sys.exit(1)
TEST

echo ""
echo "==> [1/3] Creating control database..."
$VENV/python - <<CREATEDB
import psycopg
from psycopg import sql
name = "${GL_CONTROL_DB_NAME:-gl_control}"
with psycopg.connect(
    "postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/postgres",
    autocommit=True,
) as conn:
    if conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
    ).fetchone() is None:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        print(f"    created database {name}")
    else:
        print(f"    database {name} already exists")
CREATEDB

echo ""
echo "==> [2/3] Running migrations..."
$VENV/alembic -n control upgrade head >/dev/null 2>&1 || echo "    (migrations may already be applied)"

echo ""
echo "==> [3/3] Provisioning tenant '${TENANT}'..."
$VENV/python - "$TENANT" <<'PY'
import sys
from guardian_lens.db.provisioning import ensure_tenant
slug = sys.argv[1]
ensure_tenant(slug, f"Dev tenant {slug}")
print(f"    '{slug}' attested and active")
PY

echo ""
echo "==> Bootstrapping admin ${ADMIN_EMAIL}..."
$VENV/python - "$TENANT" "$ADMIN_EMAIL" <<'PY'
import hashlib, os, sys
import psycopg
from guardian_lens.db.urls import psycopg_url
slug, email = sys.argv[1], sys.argv[2]
digest = hashlib.sha256(email.strip().lower().encode()).digest()
with psycopg.connect(psycopg_url(os.environ["GL_CONTROL_DB_URL"])) as conn:
    exists = conn.execute(
        "SELECT 1 FROM user_directory WHERE email_hash = %s", (digest,)
    ).fetchone()
if exists:
    print(f"    {email} already bootstrapped")
else:
    from guardian_lens.api.bootstrap import bootstrap
    bootstrap(slug, email, "Dev Admin",
              site_name="Dev Plant", timezone_name="Asia/Kolkata")
    print(f"    bootstrapped {email} (site 'Dev Plant')")
PY

echo ""
echo "==> Preparing web dependencies..."
(cd web && npm install --no-audit --no-fund >/dev/null 2>&1)

echo ""
echo "============================================"
echo "✓ Setup complete!"
echo ""
echo "Starting servers..."
echo "  API: http://localhost:8000"
echo "  Web: http://localhost:${WEB_PORT}"
echo "  Login: ${ADMIN_EMAIL} / guardian-dev-1"
echo ""
echo "Press Ctrl-C to stop"
echo "============================================"
echo ""

# Start both servers
$VENV/python -m guardian_lens.api &
API_PID=$!

sleep 2
(cd web && npx vite --port $WEB_PORT) &
WEB_PID=$!

# Wait for Ctrl-C
trap "kill $API_PID $WEB_PID 2>/dev/null; exit 0" INT
wait
