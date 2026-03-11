.PHONY: install run test seed lint openapi rebuild-frontier rebuild-claims tiny-loop export-effort-briefs smoke-first-user smoke-public-ingress smoke-shared-participation smoke-autoresearch-mlx smoke-production backup-runtime restore-runtime backup-production build-microsite

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

run:
	uvicorn apps.api.main:app --reload

test:
	$(PYTHON) -m pytest

seed:
	$(PYTHON) scripts/seed_demo.py --reset

rebuild-frontier:
	$(PYTHON) scripts/rebuild_frontier_projection.py

rebuild-claims:
	$(PYTHON) scripts/rebuild_claim_projection.py

lint:
	$(PYTHON) -m ruff check .

openapi:
	$(PYTHON) scripts/export_openapi.py

tiny-loop:
	$(PYTHON) -m clients.tiny_loop.run

export-effort-briefs:
	$(PYTHON) scripts/export_effort_briefs.py

smoke-first-user:
	$(PYTHON) scripts/run_first_user_smoke.py

smoke-public-ingress:
	$(PYTHON) scripts/run_public_ingress_smoke.py

smoke-shared-participation:
	$(PYTHON) scripts/run_shared_participation_smoke.py --base-url $(BASE_URL)

smoke-autoresearch-mlx:
	$(PYTHON) scripts/run_autoresearch_mlx_compounding_smoke.py --base-url $(BASE_URL) --repo-path $(REPO_PATH)

smoke-production:
	$(PYTHON) scripts/run_production_smoke.py --site-url $(SITE_URL) --api-base-url $(BASE_URL)

backup-runtime:
	$(PYTHON) scripts/backup_runtime_state.py --output-path $(OUTPUT_PATH)

restore-runtime:
	$(PYTHON) scripts/restore_runtime_state.py --archive-path $(ARCHIVE_PATH) --force

backup-production:
	$(PYTHON) scripts/backup_railway_volume.py --service $(SERVICE) --output-path $(OUTPUT_PATH)

build-microsite:
	$(PYTHON) scripts/build_microsite.py
