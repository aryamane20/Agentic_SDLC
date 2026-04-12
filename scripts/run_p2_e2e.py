#!/usr/bin/env python3
"""
P2 end-to-end: create session → generate report → refine (gate re-checked each time).

Calls the running FastAPI backend (real agent + tokens). Logs JSON under results/p2/e2e/.

Feedback sources (--mode):
  manifest   — use refinement_rounds from scenario manifest.json in order
  file       — read e2e_feedback/round_01.json, round_02.json, … (human edits these)
  interactive — type feedback in the terminal each round (empty line stops)

Examples (API must be up: uvicorn backend.api.main:app --port 8000 from repo root):

  python scripts/run_p2_e2e.py --scenario scenario-a-happy-path --mode manifest
  python scripts/run_p2_e2e.py --scenario scenario-b-low-confidence --mode file
  python scripts/run_p2_e2e.py --scenario scenario-c-critical-risk --mode interactive

Headers: sends X-Planr-User (default p2-e2e-local) so session files isolate under sessions/.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
P2_DIR = ROOT / "inputs" / "test-cases-p2"
E2E_LOG_DIR = ROOT / "results" / "p2" / "e2e"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _find_scenario(arg: str) -> tuple[Path, dict]:
    if not P2_DIR.is_dir():
        raise SystemExit(f"Missing P2 inputs: {P2_DIR}")
    for d in sorted(P2_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        mf = d / "manifest.json"
        if not mf.is_file():
            continue
        data = json.loads(mf.read_text(encoding="utf-8"))
        if data.get("id") == arg or d.name == arg:
            return d, data
    raise SystemExit(f"Scenario not found: {arg!r} (folder name or manifest id)")


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict | None = None,
    timeout: float = 600.0,
) -> tuple[int, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    h = dict(headers)
    if body is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=payload, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {url}\n{detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(
            f"Cannot reach {url!r}: {e.reason!r}\n"
            "Start the API from repo root:\n"
            "  uvicorn backend.api.main:app --reload --port 8000"
        ) from e


def _load_round_feedback(scenario_dir: Path, round_index: int) -> dict[str, Any] | None:
    path = scenario_dir / "e2e_feedback" / f"round_{round_index:02d}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_feedbacks(
    mode: str,
    scenario_dir: Path,
    manifest: dict,
    max_rounds: int | None,
) -> list[tuple[str, str, bool, str | None]]:
    """
    Returns list of (feedback, label_for_log, update_brief, source_note).
    """
    rounds: list[tuple[str, str, bool, str | None]] = []
    if mode == "manifest":
        for i, rnd in enumerate(manifest.get("refinement_rounds") or [], 1):
            fb = (rnd.get("feedback") or "").strip()
            if not fb:
                continue
            rounds.append(
                (
                    fb,
                    rnd.get("label") or f"manifest_round_{i}",
                    bool(rnd.get("update_brief", False)),
                    "manifest",
                )
            )
    elif mode == "file":
        i = 1
        while True:
            data = _load_round_feedback(scenario_dir, i)
            if data is None:
                break
            fb = (data.get("feedback") or "").strip()
            if not fb:
                break
            rounds.append(
                (
                    fb,
                    data.get("label") or f"file_round_{i:02d}",
                    bool(data.get("update_brief", False)),
                    f"e2e_feedback/round_{i:02d}.json",
                )
            )
            i += 1
        if not rounds:
            raise SystemExit(
                f"No e2e_feedback/round_XX.json under {scenario_dir / 'e2e_feedback'} — "
                "add round_01.json, round_02.json, … or use --mode manifest"
            )
    elif mode == "interactive":
        print("\n--- Interactive refinement (empty line = stop) ---\n")
        i = 1
        while max_rounds is None or i <= max_rounds:
            try:
                line = input(f"Round {i} feedback: ").strip()
            except EOFError:
                break
            if not line:
                break
            ub = input("  update_brief? [y/N]: ").strip().lower() in ("y", "yes")
            rounds.append((line, f"interactive_round_{i}", ub, "stdin"))
            i += 1
    else:
        raise SystemExit(f"Unknown mode: {mode}")

    if max_rounds is not None:
        rounds = rounds[:max_rounds]
    return rounds


def main() -> None:
    parser = argparse.ArgumentParser(description="P2 E2E via FastAPI (real agent)")
    parser.add_argument(
        "--scenario",
        required=True,
        help="Folder name (e.g. scenario-a-happy-path) or manifest id",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--mode",
        choices=("manifest", "file", "interactive"),
        default="manifest",
        help="Where refinement feedback comes from",
    )
    parser.add_argument(
        "--user-id",
        default="p2-e2e-local",
        help="X-Planr-User header (isolates sessions/ on disk)",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Pass use_cache=true on generate (default: false for reproducible E2E)",
    )
    parser.add_argument(
        "--prompt-version",
        default=None,
        help="Optional prompt version for PMAgent (default: server default v1.6.2)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="Cap refinement rounds (after slicing manifest/file list)",
    )
    parser.add_argument(
        "--approve-at-end",
        action="store_true",
        help="POST /gates/{report_id}/decision approve after refinements",
    )
    parser.add_argument(
        "--timeout-generate",
        type=float,
        default=900.0,
        help="HTTP timeout seconds for /reports/generate (default 900)",
    )
    parser.add_argument(
        "--timeout-refine",
        type=float,
        default=900.0,
        help="HTTP timeout seconds for each /refine (default 900)",
    )
    args = parser.parse_args()

    scenario_dir, manifest = _find_scenario(args.scenario)
    brief_path = scenario_dir / (manifest.get("brief_file") or "brief.txt")
    if not brief_path.is_file():
        raise SystemExit(f"Missing brief: {brief_path}")

    brief_text = brief_path.read_text(encoding="utf-8")
    base = args.base_url.rstrip("/")
    headers = {"X-Planr-User": args.user_id}

    E2E_LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_id = f"p2_e2e_{scenario_dir.name}_{_utc_iso().replace(':', '-')}"
    log_path = E2E_LOG_DIR / f"{run_id}.json"

    log: dict[str, Any] = {
        "run_id": run_id,
        "started_at": _utc_iso(),
        "scenario_folder": scenario_dir.name,
        "manifest_id": manifest.get("id"),
        "mode": args.mode,
        "base_url": base,
        "user_id": args.user_id,
        "steps": [],
    }

    # 1) Session (no JSON body — matches POST /sessions)
    _, sess_body = _request_json(
        "POST", f"{base}/sessions", headers=headers, body=None
    )
    assert isinstance(sess_body, dict)
    session_id = sess_body["session_id"]
    log["session_id"] = session_id
    log["steps"].append({"step": "create_session", "session_id": session_id})

    # 2) Generate
    gen_body: dict[str, Any] = {
        "session_id": session_id,
        "brief": brief_text,
        "use_cache": args.use_cache,
    }
    if args.prompt_version:
        gen_body["prompt_version"] = args.prompt_version

    _, gen_resp = _request_json(
        "POST",
        f"{base}/reports/generate",
        headers=headers,
        body=gen_body,
        timeout=args.timeout_generate,
    )
    assert isinstance(gen_resp, dict)
    report_id = gen_resp["report_id"]
    log["report_id"] = report_id
    log["steps"].append(
        {
            "step": "generate",
            "report_id": report_id,
            "gate": gen_resp.get("gate"),
            "validation": gen_resp.get("validation"),
            "tokens_used": gen_resp.get("tokens_used"),
            "cache_hit": gen_resp.get("cache_hit"),
        }
    )

    feedback_plan = _iter_feedbacks(
        args.mode, scenario_dir, manifest, args.max_rounds
    )

    # 3) Refinements
    for idx, (feedback, label, update_brief, source_note) in enumerate(feedback_plan, 1):
        _, ref_resp = _request_json(
            "POST",
            f"{base}/reports/{report_id}/refine",
            headers=headers,
            body={
                "session_id": session_id,
                "feedback": feedback,
                "update_brief": update_brief,
            },
            timeout=args.timeout_refine,
        )
        assert isinstance(ref_resp, dict)
        log["steps"].append(
            {
                "step": f"refine_{idx}",
                "label": label,
                "feedback_source": source_note,
                "feedback_preview": feedback[:200] + ("…" if len(feedback) > 200 else ""),
                "update_brief": update_brief,
                "gate": ref_resp.get("gate"),
                "refinement_count": ref_resp.get("refinement_count"),
                "tokens_used": ref_resp.get("tokens_used"),
            }
        )

    # 4) Optional approve
    if args.approve_at_end:
        _, dec_resp = _request_json(
            "POST",
            f"{base}/gates/{report_id}/decision",
            headers=headers,
            body={"session_id": session_id, "decision": "approve"},
        )
        log["steps"].append(
            {"step": "gate_decision", "decision": "approve", "response": dec_resp}
        )

    log["finished_at"] = _utc_iso()
    log["manifest_expected"] = manifest.get("expected")

    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote log: {log_path.relative_to(ROOT)}")
    print(f"session_id={session_id} report_id={report_id}")


if __name__ == "__main__":
    main()
