.PHONY: install install-frontend test test-p1 test-p2 test-hitl test-p2-baseline test-input-guard api frontend lint eval-generate-golden eval-replay-golden help

# ── Setup ──────────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt -r backend/requirements.txt

install-frontend:
	cd frontend && npm install

# ── Development ────────────────────────────────────────────────────────────────

api:
	uvicorn backend.api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# ── Testing ────────────────────────────────────────────────────────────────────

test:
	python -m pytest tests/ -v

test-p1:
	python -m pytest tests/p1/ -v

test-p2:
	python -m pytest tests/p2/ -v

test-hitl:
	python -m pytest tests/p2/test_hitl_flow.py tests/p2/test_api_approval_gate.py -v

test-p2-baseline:
	python -m pytest tests/p2/ -v

test-input-guard:
	python -m pytest tests/p2/test_input_guard.py -v

test-fast:
	python -m pytest tests/ -v --ignore=tests/p1/test_happy_path.py

# ── Evaluation ─────────────────────────────────────────────────────────────────

eval-generate:
	python scripts/run_eval.py --generate

eval-replay:
	python scripts/run_eval.py --replay

eval-all:
	python scripts/run_eval.py --all

eval-generate-golden:
	python scripts/run_golden.py --generate

eval-replay-golden:
	python scripts/run_golden.py --replay

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make install              Install Python dependencies (agent + backend)"
	@echo "  make install-frontend     Install frontend npm dependencies"
	@echo "  make api                  Start FastAPI backend on :8000"
	@echo "  make frontend             Start Vite dev server on :5180"
	@echo "  make test                 Run full test suite (P1 + P2)"
	@echo "  make test-p1              Run P1 tests only (agent, validator, viability)"
	@echo "  make test-p2              Run P2 tests only (gates, HITL, refinement, API)"
	@echo "  make test-hitl            Run HITL-specific tests (gate + flow)"
	@echo "  make test-input-guard     Run input guard unit tests (zero API cost)"
	@echo "  make test-p2-baseline     P2 regression suite (alias for test-p2)"
	@echo "  make test-fast            Run tests excluding slow happy-path tests"
	@echo "  make eval-generate        Generate fresh eval outputs (uses API credits)"
	@echo "  make eval-replay          Replay cached eval outputs (free)"
	@echo "  make eval-all             Generate + replay + score"
	@echo "  make eval-generate-golden Generate golden dataset outputs (uses API credits)"
	@echo "  make eval-replay-golden   Replay golden outputs against assertions (free)"
	@echo ""
