CORE_COMPOSE=bootstrap/compose/core/docker-compose.yml
EDGE_COMPOSE=bootstrap/compose/edge/docker-compose.yml
TAIL?=200

# Common commands:
# - make validate
# - make docs-build / docs-serve
# - make skill-update-docs MSG="..."
# - make skill-flywheel MSG="..." [PLAN=...] [EXEC=...] [YES=1]
# - make run MSG="..." [PLAN=...] [EXEC=...] [YES=1]

.PHONY: help lint venv deps validate test plan validate-plan approve execute smoke doctor \
	validate-codex-config docs-build docs-port docs-serve skill-update-docs skill-flywheel skill-plan-inspect skill-ports-check preflight run \
	up-core down-core restart-core up-edge down-edge restart-edge restart up down logs-core logs-edge \
	bootstrap-check env-check env-manifest vw-check vw-run vw-bootstrap-check vw-doctor \
	vw-up vw-up-core vw-up-edge vw-restart vw-restart-core vw-restart-edge backup-core restore-test \
	bw-check release-notes notes tag

help:
	@echo "Usage:"
	@echo "  make help"
	@echo "  make validate"
	@echo "  make preflight [FAIL=1]"
	@echo "  make docs-build"
	@echo "  make docs-serve"
	@echo "  make skill-update-docs MSG=\"...\""
	@echo "  make skill-plan-inspect [PLAN=...] [LIST=1 N=...] [JSON=1]"
	@echo "  make skill-ports-check [PORTS=\"...\"] [FAIL=1] [JSON=1]"
	@echo "  make skill-flywheel MSG=\"...\" [PLAN=...] [EXEC=...] [YES=1]"

lint:
	@echo "TODO: lint"

venv:
	python3 -m venv .venv

deps: venv
	.venv/bin/python -m pip install --upgrade pip
	@if [ -f requirements.txt ]; then .venv/bin/python -m pip install -r requirements.txt; fi
	@if [ -f requirements-dev.txt ]; then .venv/bin/python -m pip install -r requirements-dev.txt; fi

validate: docs-build validate-codex-config

validate-codex-config:
	docker run --rm -v "$$(pwd):/work" -w /work python:3.11-slim python -c "import tomllib; from pathlib import Path; tomllib.loads(Path('.codex/config.toml').read_text(encoding='utf-8')); print('[PASS] .codex/config.toml parses')"

docs-build:
	docker run --rm -v "$(CURDIR):/work" -w /work python:3.11-slim sh -ec "python -m pip install --no-cache-dir -r docs/requirements.txt >/dev/null && mkdocs build --strict"

docs-port:
	@set -e; \
	for port in 8000 8001 8002 8003 8004 8005; do \
		if python3 skills/ports-check/ports-check.py --ports "$$port" --fail-on-used >/dev/null 2>&1; then \
			echo "$$port"; \
			exit 0; \
		fi; \
	done; \
	echo "No free docs port found in 8000-8005" >&2; \
	exit 1

docs-serve:
	@set -e; \
	port="$(DOCS_PORT)"; \
	if [ -z "$$port" ]; then \
		port="$$( $(MAKE) --no-print-directory -s docs-port MAKEFLAGS= )"; \
	fi; \
	echo "[INFO] Serving docs on http://127.0.0.1:$$port/"; \
	docker run --rm -p "$$port:8000" -v "$(CURDIR):/work" -w /work python:3.11-slim sh -ec "python -m pip install --no-cache-dir -r docs/requirements.txt >/dev/null && mkdocs serve -a 0.0.0.0:8000"

skill-update-docs:
	@if [ -z "$(MSG)" ]; then echo "MSG is required. Usage: make skill-update-docs MSG=\"<message>\""; exit 1; fi
	python3 skills/update-docs/update-docs.py --message "$(MSG)"

skill-flywheel:
	@if [ -z "$(MSG)" ]; then echo "MSG is required. Usage: make skill-flywheel MSG=\"<message>\" [PLAN=plans/<file>.json] [EXEC=\"<cmd with {plan}>\"] [YES=1]"; exit 1; fi
	python3 skills/flywheel-runner/run-flywheel.py --message "$(MSG)" \
		$(if $(PLAN),--plan "$(PLAN)",) \
		$(if $(EXEC),--exec "$(EXEC)",) \
		$(if $(filter 1,$(YES)),--yes,) \
		$(if $(filter 1,$(NO_VALIDATE)),--no-validate,)

skill-plan-inspect:
	python3 skills/plan-inspect/plan-inspect.py \
		$(if $(filter 1,$(LIST)),--list $(or $(N),10),) \
		$(if $(PLAN),--plan "$(PLAN)",--plan latest) \
		$(if $(filter 1,$(JSON)),--json,)

skill-ports-check:
	python3 skills/ports-check/ports-check.py \
		$(if $(PORTS),--ports "$(PORTS)",--defaults) \
		$(if $(filter 1,$(FAIL)),--fail-on-used,) \
		$(if $(filter 1,$(JSON)),--json,)

preflight:
	$(MAKE) skill-ports-check $(if $(FAIL),FAIL="$(FAIL)",)
	$(MAKE) validate

run: preflight
	@if [ -z "$(MSG)" ]; then echo "MSG is required. Usage: make run MSG=\"<message>\" [PLAN=plans/<file>.json] [EXEC=\"<cmd with {plan}>\"] [YES=1]"; exit 1; fi
	$(MAKE) skill-flywheel MSG="$(MSG)" \
		$(if $(PLAN),PLAN="$(PLAN)",) \
		$(if $(EXEC),EXEC="$(EXEC)",) \
		$(if $(YES),YES="$(YES)",) \
		$(if $(NO_VALIDATE),NO_VALIDATE="$(NO_VALIDATE)",)

test:
	python3 -m unittest -v

plan:
	python3 ops/plan/mkplan.py $(if $(TEMPLATE),--template $(TEMPLATE),)

validate-plan:
	@if [ -z "$$PLAN" ]; then echo "PLAN is required. Usage: make validate-plan PLAN=plans/<file>.json"; exit 1; fi
	python3 ops/plan/validate_plan.py --plan "$$PLAN"

approve:
	@if [ -z "$$PLAN" ]; then echo "PLAN is required. Usage: make approve PLAN=plans/<file>.json VAULTWARDEN_ITEM_ID=<id>"; exit 1; fi
	@if [ -z "$$VAULTWARDEN_ITEM_ID" ]; then echo "VAULTWARDEN_ITEM_ID is required. Usage: make approve PLAN=plans/<file>.json VAULTWARDEN_ITEM_ID=<id>"; exit 1; fi
	python3 ops/plan/approve_plan.py --plan "$$PLAN" --vaultwarden-item-id "$$VAULTWARDEN_ITEM_ID"

execute:
	@if [ -z "$$PLAN" ]; then echo "PLAN is required. Usage: make execute PLAN=plans/<file>.json"; exit 1; fi
	python3 ops/executor/execute_plan.py --plan "$$PLAN"

smoke:
	@set +e; \
	step="validate"; \
	$(MAKE) validate; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "SMOKE: FAIL ($$step)"; exit 1; fi; \
	step="test"; \
	$(MAKE) test; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "SMOKE: FAIL ($$step)"; exit 1; fi; \
	step="stack-status-plan"; \
	$(MAKE) plan TEMPLATE=stack-status ENV=dev DRY_RUN=true; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "SMOKE: FAIL ($$step)"; exit 1; fi; \
	step="ingress-status-plan"; \
	$(MAKE) plan TEMPLATE=ingress-status ENV=dev DRY_RUN=true; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "SMOKE: FAIL ($$step)"; exit 1; fi; \
	echo "SMOKE: PASS"

env-check:
	python3 ops/bin/env_scan.py env-check $(if $(filter 1,$(EXPLAIN)),--explain,)

env-manifest:
	python3 ops/bin/env_scan.py manifest --output docs/runbooks/env-vars.md

doctor:
	@set +e; \
	fail=0; \
	branch=$$(git rev-parse --abbrev-ref HEAD 2>/dev/null); rc=$$?; \
	if [ $$rc -ne 0 ]; then branch="unavailable"; fail=1; fi; \
	status_count=$$(git status --porcelain 2>/dev/null | wc -l | tr -d ' '); rc=$$?; \
	if [ $$rc -ne 0 ]; then status_count="unavailable"; fail=1; fi; \
	echo "git_branch=$$branch"; \
	echo "git_status_entries=$$status_count"; \
	if docker version >/dev/null 2>&1; then \
		echo "docker=$$(docker --version | head -n 1)"; \
	else \
		echo "docker=missing_or_unavailable"; \
		fail=1; \
	fi; \
	if docker compose version >/dev/null 2>&1; then \
		echo "compose=$$(docker compose version | head -n 1)"; \
	else \
		echo "compose=missing_or_unavailable"; \
		fail=1; \
	fi; \
	for file in bootstrap/compose/core/docker-compose.yml bootstrap/compose/edge/docker-compose.yml; do \
		if [ -f "$$file" ]; then \
			echo "file_ok=$$file"; \
		else \
			echo "file_missing=$$file"; \
			fail=1; \
		fi; \
	done; \
	echo "containers(core|edge):"; \
	if docker ps -a --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -E '^(core-|edge-)'; then :; else echo "none_or_unavailable"; fi; \
	$(MAKE) env-check; rc=$$?; \
	if [ $$rc -ne 0 ]; then \
		echo "HINT: Run 'make vw-check' to validate Vaultwarden mapping/session, then 'PUBLIC_DOMAIN=... make vw-bootstrap-check'."; \
		fail=1; \
	fi; \
	if [ $$fail -eq 0 ]; then \
		echo "DOCTOR: PASS"; \
	else \
		echo "DOCTOR: FAIL"; \
		exit 1; \
	fi

bw-check:
	@set +e; \
	if command -v bw >/dev/null 2>&1; then \
		bw --version; \
		echo "BW-CHECK: PASS"; \
	else \
		echo "bw CLI not found on PATH"; \
		echo "BW-CHECK: FAIL"; \
		exit 1; \
	fi

up-core: env-check
	docker compose -f $(CORE_COMPOSE) up -d

down-core:
	docker compose -f $(CORE_COMPOSE) down

restart-core: env-check down-core up-core

up-edge: env-check
	docker compose -f $(EDGE_COMPOSE) up -d

down-edge:
	docker compose -f $(EDGE_COMPOSE) down

restart-edge: env-check down-edge up-edge

restart: restart-core restart-edge

up: env-check up-core up-edge

down: down-edge down-core

logs-core:
	@if [ -z "$(SERVICE)" ]; then echo "SERVICE is required. Usage: make logs-core SERVICE=<name> [TAIL=<n>]"; exit 1; fi
	docker compose -f $(CORE_COMPOSE) logs -n $(TAIL) -f $(SERVICE)

logs-edge:
	@if [ -z "$(SERVICE)" ]; then echo "SERVICE is required. Usage: make logs-edge SERVICE=<name> [TAIL=<n>]"; exit 1; fi
	docker compose -f $(EDGE_COMPOSE) logs -n $(TAIL) -f $(SERVICE)

bootstrap-check:
	@set +e; \
	step="doctor"; \
	$(MAKE) $$step; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "BOOTSTRAP-CHECK: FAIL ($$step)"; exit 1; fi; \
	step="smoke"; \
	$(MAKE) $$step; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "BOOTSTRAP-CHECK: FAIL ($$step)"; exit 1; fi; \
	step="env-check"; \
	$(MAKE) $$step; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "BOOTSTRAP-CHECK: FAIL ($$step)"; exit 1; fi; \
	step="up"; \
	$(MAKE) $$step; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "BOOTSTRAP-CHECK: FAIL ($$step)"; exit 1; fi; \
	step="plan-stack-status"; \
	$(MAKE) plan TEMPLATE=stack-status ENV=dev; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "BOOTSTRAP-CHECK: FAIL ($$step)"; exit 1; fi; \
	step="plan-ingress-status"; \
	$(MAKE) plan TEMPLATE=ingress-status ENV=dev; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "BOOTSTRAP-CHECK: FAIL ($$step)"; exit 1; fi; \
	echo "BOOTSTRAP-CHECK: PASS"

vw-check:
	python3 ops/bin/vw_env.py check

vw-run:
	@if [ -z "$(CMD)" ]; then echo "CMD is required. Usage: make vw-run CMD=\"<command>\""; exit 1; fi
	python3 ops/bin/vw_env.py run -- $(CMD)

vw-bootstrap-check:
	python3 ops/bin/vw_env.py run -- $(MAKE) bootstrap-check

vw-doctor:
	@set +e; \
	step="vw-check"; \
	$(MAKE) $$step; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "VW-DOCTOR: FAIL ($$step)"; exit 1; fi; \
	step="vw-run-env-check"; \
	$(MAKE) vw-run CMD="$(MAKE) env-check"; rc=$$?; \
	if [ $$rc -ne 0 ]; then echo "VW-DOCTOR: FAIL ($$step)"; exit 1; fi; \
	echo "VW-DOCTOR: PASS"

vw-up:
	@if [ -z "$$PUBLIC_DOMAIN" ]; then echo "PUBLIC_DOMAIN is required. Usage: PUBLIC_DOMAIN=<domain> make vw-up"; exit 1; fi
	$(MAKE) vw-run CMD="$(MAKE) up"

vw-up-core:
	@if [ -z "$$PUBLIC_DOMAIN" ]; then echo "PUBLIC_DOMAIN is required. Usage: PUBLIC_DOMAIN=<domain> make vw-up-core"; exit 1; fi
	$(MAKE) vw-run CMD="$(MAKE) up-core"

vw-up-edge:
	@if [ -z "$$PUBLIC_DOMAIN" ]; then echo "PUBLIC_DOMAIN is required. Usage: PUBLIC_DOMAIN=<domain> make vw-up-edge"; exit 1; fi
	$(MAKE) vw-run CMD="$(MAKE) up-edge"

vw-restart:
	@if [ -z "$$PUBLIC_DOMAIN" ]; then echo "PUBLIC_DOMAIN is required. Usage: PUBLIC_DOMAIN=<domain> make vw-restart"; exit 1; fi
	$(MAKE) vw-run CMD="$(MAKE) restart"

vw-restart-core:
	@if [ -z "$$PUBLIC_DOMAIN" ]; then echo "PUBLIC_DOMAIN is required. Usage: PUBLIC_DOMAIN=<domain> make vw-restart-core"; exit 1; fi
	$(MAKE) vw-run CMD="$(MAKE) restart-core"

vw-restart-edge:
	@if [ -z "$$PUBLIC_DOMAIN" ]; then echo "PUBLIC_DOMAIN is required. Usage: PUBLIC_DOMAIN=<domain> make vw-restart-edge"; exit 1; fi
	$(MAKE) vw-run CMD="$(MAKE) restart-edge"

backup-core:
	$(MAKE) plan TEMPLATE=backup-core ENV=dev

restore-test:
	$(MAKE) plan TEMPLATE=restore-test ENV=dev

release-notes:
	@set -eu; \
	if git describe --tags --abbrev=0 >/dev/null 2>&1; then \
		base=$$(git describe --tags --abbrev=0); \
		range="$$base..HEAD"; \
	else \
		base=$$(git rev-list --max-parents=0 HEAD); \
		range="$$base..HEAD"; \
	fi; \
	ts=$$(date -u +%Y%m%dT%H%M%SZ); \
	out="artifacts/release-notes/release-notes-$$ts.md"; \
	mkdir -p artifacts/release-notes; \
	{ \
		echo "# Release Notes"; \
		echo; \
		echo "Base: $$base"; \
		echo; \
		git log $$range --pretty=format:'- %h %s'; \
		echo; \
	} > "$$out"; \
	echo "$$out"; \
	echo "RELEASE-NOTES: OK"

notes: release-notes

tag:
	@if [ -z "$(VERSION)" ]; then echo "VERSION is required. Usage: make tag VERSION=0.2.0"; exit 1; fi
	git tag -a "v$(VERSION)" -m "v$(VERSION)"
	@echo "v$(VERSION)"
	@echo "TAG: OK"
