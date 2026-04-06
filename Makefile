.PHONY: install install-frontend test test-hitl api frontend lint help

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

test-hitl:
	python -m pytest tests/test_hitl_flow.py tests/test_api_approval_gate.py -v

test-fast:
	python -m pytest tests/ -v --ignore=tests/test_happy_path.py

# ── Evaluation ─────────────────────────────────────────────────────────────────

eval-generate:
	python scripts/run_eval.py --generate

eval-replay:
	python scripts/run_eval.py --replay

eval-all:
	python scripts/run_eval.py --all

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make install           Install Python dependencies (agent + backend)"
	@echo "  make install-frontend  Install frontend npm dependencies"
	@echo "  make api               Start FastAPI backend on :8000"
	@echo "  make frontend          Start Vite dev server on :5180"
	@echo "  make test              Run full test suite"
	@echo "  make test-hitl         Run HITL-specific tests only"
	@echo "  make test-fast         Run tests excluding slow eval tests"
	@echo "  make eval-generate     Generate fresh eval outputs (uses API credits)"
	@echo "  make eval-replay       Replay cached eval outputs (free)"
	@echo "  make eval-all          Generate + replay + score"
	@echo ""
