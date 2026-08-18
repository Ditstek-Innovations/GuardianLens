.PHONY: help run edge-demo api web e2e up down migrate-control provision onboard attest bypass unit test coverage lint clean

# .env is the single source of truth for local runs. `-include` tolerates
# its absence; `export` passes everything to child processes so make targets
# and scripts/run_dev.sh resolve the same database.
-include .env
export

help:
	@echo "Guardian Lens"
	@echo ""
	@echo "  make run              ONE COMMAND: db + API (:8000) + review UI (:5173)"
	@echo "  make edge-demo        feed the running stack events from a simulated site"
	@echo "  make camera-sim       synthetic RTSP camera at rtsp://localhost:8554/cam1"
	@echo "  make e2e              the full-workflow test (TRD 20.2 steps 1-4)"
	@echo ""
	@echo "  make up               start PostgreSQL 16 (docker-compose.dev.yml)"
	@echo "  make migrate-control  create the control schema"
	@echo "  make provision        provision a tenant database (TENANT=slug)"
	@echo "  make onboard          REAL site, clean tenant: provision + attest +"
	@echo "                        first admin (TENANT= ADMIN_EMAIL= ADMIN_NAME="
	@echo "                        SITE_NAME= TZ=) — no demo data, WORKFLOW.md 3b"
	@echo "  make attest           FF-11 constraint attestation for a tenant"
	@echo "  make bypass           run the business-rule bypass suite (TRD 19.4)"
	@echo "  make unit             unit tests, no database"
	@echo "  make test             full test suite"
	@echo "  make coverage         full suite with coverage (TRD 19.2)"
	@echo "  make lint             bandit static analysis (TRD 12.8)"
	@echo "  make down             stop and remove the stack"

run:
	bash scripts/run_dev.sh

edge-demo:
	.venv/bin/python scripts/edge_demo.py

api:
	.venv/bin/python -m guardian_lens.api

web:
	cd web && npx vite --port 5173

# Only the two sim services — a bare "up" would also start the compose db,
# which collides with a system PostgreSQL on the same POSTGRES_PORT.
camera-sim:
	docker compose -f docker-compose.dev.yml --profile camera up -d rtsp-sim rtsp-feed
	@echo "RTSP test stream: rtsp://localhost:8554/cam1 (allow ~10s to publish)"

camera-sim-down:
	docker compose -f docker-compose.dev.yml --profile camera rm -sf rtsp-feed rtsp-sim

e2e:
	.venv/bin/pytest tests/e2e -v

up:
	docker compose -f docker-compose.dev.yml up -d
	@echo "waiting for postgres..."
	@until docker compose -f docker-compose.dev.yml exec -T db pg_isready -q; do sleep 1; done
	@echo "ready"

down:
	docker compose -f docker-compose.dev.yml down -v

migrate-control:
	.venv/bin/alembic -n control upgrade head

# Provisioning is a code path, never a runbook — DATABASE.md 13.5.1.
# create -> migrate to head -> seed -> attest -> activate.
provision:
	.venv/bin/python -m guardian_lens.db.provisioning provision $(TENANT)

# Going real (WORKFLOW.md 3b): a physically isolated tenant carrying no demo
# data, FF-11 attested, with its first admin bootstrapped. GL_BOOTSTRAP_PASSWORD
# must be exported for the admin's first sign-in; edge-demo must never be
# pointed at this tenant.
onboard:
	@test -n "$(TENANT)" -a -n "$(ADMIN_EMAIL)" -a -n "$(ADMIN_NAME)" \
	  -a -n "$(SITE_NAME)" -a -n "$(TZ)" || \
	  (echo "usage: make onboard TENANT=slug ADMIN_EMAIL=a@b ADMIN_NAME='Full Name' SITE_NAME='Plant name' TZ=Area/City"; exit 1)
	.venv/bin/python -m guardian_lens.db.provisioning provision $(TENANT)
	.venv/bin/python -m guardian_lens.api.bootstrap $(TENANT) $(ADMIN_EMAIL) "$(ADMIN_NAME)" --site-name "$(SITE_NAME)" --timezone $(TZ)

attest:
	.venv/bin/python -m guardian_lens.db.attestation $(TENANT)

bypass:
	.venv/bin/pytest tests/bypass -v

unit:
	.venv/bin/pytest tests/unit -v

test:
	.venv/bin/pytest -v

coverage:
	.venv/bin/pytest --cov=guardian_lens --cov-report=term-missing

lint:
	.venv/bin/bandit -q -r src/

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache
