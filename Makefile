.PHONY: lint validate test plan validate-plan approve execute smoke

lint:
	@echo "TODO: lint"

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
