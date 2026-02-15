CORE_COMPOSE=bootstrap/compose/core/docker-compose.yml
EDGE_COMPOSE=bootstrap/compose/edge/docker-compose.yml
TAIL?=200

.PHONY: lint venv deps validate test plan validate-plan approve execute smoke doctor \
	up-core down-core restart-core up-edge down-edge restart-edge up down logs-core logs-edge \
	bootstrap-check

lint:
	@echo "TODO: lint"

venv:
	python3 -m venv .venv

deps: venv
	.venv/bin/python -m pip install --upgrade pip
	@if [ -f requirements.txt ]; then .venv/bin/python -m pip install -r requirements.txt; fi
	@if [ -f requirements-dev.txt ]; then .venv/bin/python -m pip install -r requirements-dev.txt; fi

validate:
	python3 ops/validator/validate_repo.py

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
	if [ -n "$$PUBLIC_DOMAIN" ]; then \
		echo "public_domain_set=yes"; \
	else \
		echo "public_domain_set=no"; \
		fail=1; \
	fi; \
	if [ $$fail -eq 0 ]; then \
		echo "DOCTOR: PASS"; \
	else \
		echo "DOCTOR: FAIL"; \
		exit 1; \
	fi

up-core:
	docker compose -f $(CORE_COMPOSE) up -d

down-core:
	docker compose -f $(CORE_COMPOSE) down

restart-core: down-core up-core

up-edge:
	docker compose -f $(EDGE_COMPOSE) up -d

down-edge:
	docker compose -f $(EDGE_COMPOSE) down

restart-edge: down-edge up-edge

up: up-core up-edge

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
