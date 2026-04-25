"""
Golden dataset runner — two modes:

  --generate  Call /reports/generate for each case in inputs/golden_dataset.json,
              save responses to outputs/golden/{case_id}.json.
              Skips cases where output already exists and golden_verified=true.

  --replay    Read saved outputs, check against assertions in golden_dataset.json,
              print a pass/fail table, and write outputs/golden/golden_replay.xlsx.
              No API calls.

  --case ID   Run a single case only (works with both modes).

Usage:
  python scripts/run_golden.py --generate
  python scripts/run_golden.py --replay
  python scripts/run_golden.py --case hp-01 --generate
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

REQUEST_TIMEOUT_S = 480  # generate is slow; Haiku w/ 16k max_tokens + 8-step reasoning
                          # can exceed 240s on vague briefs (hp-02, hp-06). 480s = 8min ceiling.

# Keep golden `--generate` aligned with the active system prompt in agent/main + API default.
GOLDEN_GENERATE_PROMPT_VERSION = "v1.6.4"

try:
    import httpx as _http

    def _request(method: str, url: str, **kwargs):
        return _http.request(method, url, timeout=REQUEST_TIMEOUT_S, **kwargs)
except ImportError:
    import urllib.request
    import urllib.error

    class _FakeResp:
        def __init__(self, status_code: int, body: bytes):
            self.status_code = status_code
            self._body = body

        def json(self):
            return json.loads(self._body)

    def _request(method: str, url: str, json=None, headers=None, **kw):  # type: ignore[misc]
        data = json and __import__("json").dumps(json).encode()
        h = {**(headers or {}), "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=h, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as r:
                return _FakeResp(r.status, r.read())
        except urllib.error.HTTPError as e:
            return _FakeResp(e.code, e.read())


ROOT = Path(__file__).parent.parent
DATASET = ROOT / "inputs" / "golden_dataset.json"
OUT_DIR = ROOT / "outputs" / "golden"
API_BASE = "http://127.0.0.1:8000"
HEADERS = {"X-Planr-User": "golden-runner"}

SYSTEM_PROMPT_FINGERPRINTS = [
    "8-step", "eight-step", "ANTI-PATTERN CHECK",
    "OUTPUT CONTRACT", "PMI-grounded", "EXTRACT\n", "CLASSIFY\n",
]


# ── Dataset loading ────────────────────────────────────────────────────────────

def load_dataset() -> list[dict]:
    if not DATASET.exists():
        sys.exit(f"Dataset not found: {DATASET}")
    raw = DATASET.read_text()
    cleaned = re.sub(r"//[^\n]*", "", raw)   # strip JS-style comments
    return json.loads(cleaned)["cases"]


def read_input(case: dict) -> str:
    p = ROOT / case["input_file"]
    if not p.exists():
        sys.exit(f"Input file not found: {p}")
    return p.read_text()


# ── Session helper ─────────────────────────────────────────────────────────────

def create_session() -> str:
    r = _request("POST", f"{API_BASE}/sessions", headers=HEADERS)
    if r.status_code not in (200, 201):
        sys.exit(f"Could not create session: HTTP {r.status_code}")
    return r.json()["session_id"]


# ── Generate ───────────────────────────────────────────────────────────────────

def generate(cases: list[dict], only_id: str | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok_count = fail_count = skip_count = 0

    for case in cases:
        cid = case["id"]
        if only_id and cid != only_id:
            continue

        out_file = OUT_DIR / f"{cid}.json"
        if out_file.exists() and case.get("golden_verified"):
            print(f"  SKIP  {cid}  (verified output exists)")
            skip_count += 1
            continue

        text = read_input(case)
        expected_status = case["assertions"].get("http_status", 200)

        print(f"  ...   {cid}  [{case['category']}]", end="", flush=True)
        try:
            sid = create_session()
            r = _request(
                "POST",
                f"{API_BASE}/reports/generate",
                json={
                    "session_id": sid,
                    "brief": text,
                    "use_cache": False,
                    "prompt_version": GOLDEN_GENERATE_PROMPT_VERSION,
                },
                headers=HEADERS,
            )
            result = {
                "case_id": cid,
                "http_status": r.status_code,
                "body": r.json(),
            }
            out_file.write_text(json.dumps(result, indent=2))
            match = "✓" if r.status_code == expected_status else "!"
            print(f"\r  {match}     {cid}  HTTP {r.status_code} (expected {expected_status})")
            ok_count += 1
            time.sleep(0.4)
        except Exception as exc:
            print(f"\r  ✗     {cid}  ERROR: {exc}")
            fail_count += 1

    print(f"\n  {ok_count} generated, {skip_count} skipped, {fail_count} failed")
    print(f"  Outputs: {OUT_DIR}\n")


# ── Replay ─────────────────────────────────────────────────────────────────────

def check_case(case: dict, saved: dict) -> list[tuple[str, bool, str]]:
    """Return list of (check_name, passed, detail) tuples."""
    checks: list[tuple[str, bool, str]] = []
    a = case["assertions"]
    body = saved.get("body", {})
    actual_status = saved.get("http_status")

    def ok(name: str, detail: str = "") -> None:
        checks.append((name, True, detail))

    def fail(name: str, detail: str = "") -> None:
        checks.append((name, False, detail))

    # HTTP status — checked first; if wrong, skip further checks
    expected_status = a.get("http_status", 200)
    if actual_status == expected_status:
        ok("http_status", str(actual_status))
    else:
        fail("http_status", f"got {actual_status}, expected {expected_status}")
        return checks

    # ── 422 path (bad_input cases) ────────────────────────────────────────────
    if expected_status == 422:
        detail = body.get("detail", {})
        actual_code = detail.get("code", "") if isinstance(detail, dict) else ""
        actual_reason = detail.get("reason", "") if isinstance(detail, dict) else ""

        exp_code = a.get("error_code", "")
        if actual_code == exp_code:
            ok("error_code", actual_code)
        else:
            fail("error_code", f"got {actual_code!r}, expected {exp_code!r}")

        exp_reason = a.get("reason_code")
        if exp_reason:
            if actual_reason == exp_reason:
                ok("reason_code", actual_reason)
            else:
                fail("reason_code", f"got {actual_reason!r}, expected {exp_reason!r}")
        return checks

    # ── 200 path (happy path / risk cases) ────────────────────────────────────
    report = body.get("report", {})
    gate = body.get("gate", {})
    raw_json = json.dumps(report).lower()

    if a.get("no_parse_error"):
        if not report.get("parse_error"):
            ok("no_parse_error")
        else:
            fail("no_parse_error", "parse_error=true in report")

    if a.get("gate_fires") is not None:
        fired = bool(gate.get("fired"))
        if fired == a["gate_fires"]:
            ok("gate_fires", str(fired))
        else:
            fail("gate_fires", f"got {fired}, expected {a['gate_fires']}")

    # Confidence
    confidence: float | None = None
    cs = report.get("pm_confidence_score")
    if isinstance(cs, (int, float)):
        confidence = float(cs)
    elif isinstance(cs, dict):
        s = cs.get("score")
        try:
            confidence = float(s) if s is not None else None
        except (TypeError, ValueError):
            pass

    if confidence is not None and a.get("confidence_min") is not None:
        lo, hi = a["confidence_min"], a["confidence_max"]
        if lo <= confidence <= hi:
            ok("confidence_range", f"{confidence:.0f} ∈ [{lo},{hi}]")
        else:
            fail("confidence_range", f"{confidence:.0f} ∉ [{lo},{hi}]")

    for field in a.get("required_fields", []):
        if report.get(field) is not None:
            ok(f"field:{field}")
        else:
            fail(f"field:{field}", "missing or null")

    for pat in a.get("injection_strings_absent", []):
        if pat.lower() not in raw_json:
            ok(f"no_injection:{pat[:20]}")
        else:
            fail(f"no_injection:{pat[:20]}", "found in output")

    if a.get("system_prompt_not_revealed"):
        leaked = [fp for fp in SYSTEM_PROMPT_FINGERPRINTS if fp.lower() in raw_json]
        if not leaked:
            ok("system_prompt_not_revealed")
        else:
            fail("system_prompt_not_revealed", f"fingerprints: {leaked}")

    if a.get("has_critical_risk") is not None:
        risks = report.get("risk_register", report.get("risks", []))
        has_crit = any(
            str(r.get("score", r.get("severity", ""))).upper() == "CRITICAL"
            for r in (risks if isinstance(risks, list) else [])
        )
        if has_crit == a["has_critical_risk"]:
            ok("has_critical_risk", str(has_crit))
        else:
            fail("has_critical_risk", f"got {has_crit}, expected {a['has_critical_risk']}")

    if a.get("viability_status") is not None:
        vb = report.get("project_viability", {})
        actual_vs = vb.get("viability_status", "") if isinstance(vb, dict) else ""
        if actual_vs == a["viability_status"]:
            ok("viability_status", actual_vs)
        else:
            fail("viability_status", f"got {actual_vs!r}, expected {a['viability_status']!r}")

    if a.get("assumption_log_min_items") is not None:
        log = report.get("assumption_log", [])
        n = len(log) if isinstance(log, list) else 0
        if n >= a["assumption_log_min_items"]:
            ok("assumption_log_min_items", f"{n} entries")
        else:
            fail("assumption_log_min_items", f"got {n}, need ≥ {a['assumption_log_min_items']}")

    if a.get("staffing_includes_qa"):
        staffing = report.get("staffing_plan", [])
        has_qa = any(
            any(kw in str(r).lower() for kw in ("qa", "quality", "test"))
            for r in (staffing if isinstance(staffing, list) else [])
        )
        ok("staffing_includes_qa") if has_qa else fail("staffing_includes_qa", "no QA role found")

    if a.get("staffing_includes_security"):
        staffing = report.get("staffing_plan", [])
        has_sec = any(
            any(kw in str(r).lower() for kw in ("security", "infosec"))
            for r in (staffing if isinstance(staffing, list) else [])
        )
        ok("staffing_includes_security") if has_sec else fail("staffing_includes_security", "no security role found")

    if a.get("max_allocation_pct") is not None:
        staffing = report.get("staffing_plan", [])
        allocs = [
            r.get("allocation_percent", 0)
            for r in (staffing if isinstance(staffing, list) else [])
            if isinstance(r, dict)
        ]
        top = max(allocs, default=0)
        if top <= a["max_allocation_pct"]:
            ok("max_allocation_pct", f"max={top}%")
        else:
            fail("max_allocation_pct", f"got {top}%, limit {a['max_allocation_pct']}%")

    return checks


def _summarize_expected(a: dict) -> str:
    """Human-readable one-line summary of what a case's assertions require."""
    parts = []
    status = a.get("http_status", 200)
    parts.append(f"HTTP {status}")
    if status == 422:
        if a.get("error_code"):
            parts.append(f"error={a['error_code']}")
        if a.get("reason_code"):
            parts.append(f"reason={a['reason_code']}")
    else:
        if a.get("gate_fires") is not None:
            parts.append(f"gate={'fires' if a['gate_fires'] else 'silent'}")
        if a.get("confidence_min") is not None:
            parts.append(f"confidence=[{a['confidence_min']},{a['confidence_max']}]")
        if a.get("viability_status"):
            parts.append(f"viability={a['viability_status']}")
        if a.get("has_critical_risk") is not None:
            parts.append(f"critical_risk={a['has_critical_risk']}")
        if a.get("staffing_includes_qa"):
            parts.append("qa_in_staffing")
        if a.get("staffing_includes_security"):
            parts.append("security_in_staffing")
        if a.get("max_allocation_pct") is not None:
            parts.append(f"max_alloc≤{a['max_allocation_pct']}%")
        if a.get("assumption_log_min_items") is not None:
            parts.append(f"assumptions≥{a['assumption_log_min_items']}")
        if a.get("system_prompt_not_revealed"):
            parts.append("no_prompt_leak")
        if a.get("injection_strings_absent"):
            parts.append(f"no_injection({len(a['injection_strings_absent'])})")
        if a.get("required_fields"):
            parts.append(f"fields:{','.join(a['required_fields'])}")
    return " | ".join(parts)


def export_xlsx(
    cases: list[dict],
    rows: list[tuple[str, bool, list[tuple[str, bool, str]]]],
    skipped: list[str],
    out_path: Path,
) -> None:
    """Write replay results to an xlsx file."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("  ⚠  openpyxl not installed — skipping xlsx export (pip install openpyxl --break-system-packages)")
        return

    cases_by_id = {c["id"]: c for c in cases}
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    wb = Workbook()

    # ── Results sheet ──────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Results"

    # Colors
    NAV   = "0F1F3D"   # header bg — PLANR navy
    WHITE = "FFFFFF"
    PASS_BG  = "D4EDDA"   # soft green
    FAIL_BG  = "F8D7DA"   # soft red
    SKIP_BG  = "E8E8E8"   # gray
    CAT_BG   = "EEF2FF"   # light lavender for category dividers
    FONT     = "Arial"

    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def hfont(bold=False, color=WHITE, sz=10):
        return Font(name=FONT, bold=bold, color=color, size=sz)

    def fill(hex_color):
        return PatternFill("solid", start_color=hex_color, fgColor=hex_color)

    def center():
        return Alignment(horizontal="center", vertical="center", wrap_text=False)

    def left():
        return Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Header row
    headers = ["Test Case", "Category", "Description", "Time Run",
               "Expected Output", "Result", "Checks", "Failed Checks"]
    ws.append(headers)
    for col, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = hfont(bold=True, color=WHITE)
        cell.fill = fill(NAV)
        cell.alignment = center()
        cell.border = border

    # Build rows — group by category
    CATEGORY_ORDER = ["happy_path", "bad_input", "premortem_risk"]
    CATEGORY_LABELS = {
        "happy_path":      "Happy Path",
        "bad_input":       "Bad Input",
        "premortem_risk":  "Pre-mortem Risk",
    }

    rows_by_id = {r[0]: r for r in rows}
    current_row = 2

    for cat in CATEGORY_ORDER:
        cat_cases = [c for c in cases if c.get("category") == cat]
        if not cat_cases:
            continue

        # Category divider row
        ws.append([CATEGORY_LABELS[cat]])
        cat_cell = ws.cell(row=current_row, column=1)
        cat_cell.font = hfont(bold=True, color="1A1A2E", sz=10)
        cat_cell.fill = fill(CAT_BG)
        cat_cell.alignment = left()
        ws.merge_cells(start_row=current_row, start_column=1,
                       end_row=current_row, end_column=len(headers))
        for col in range(1, len(headers) + 1):
            ws.cell(row=current_row, column=col).border = border
        current_row += 1

        for case in cat_cases:
            cid = case["id"]
            expected_str = _summarize_expected(case["assertions"])
            out_file = OUT_DIR / f"{cid}.json"

            if cid in skipped or cid not in rows_by_id:
                time_str = "—"
                result_str = "SKIP"
                checks_str = "—"
                failed_str = "No saved output — run --generate first"
                row_bg = SKIP_BG
            else:
                _, all_pass, checks = rows_by_id[cid]
                # Time from file mtime
                if out_file.exists():
                    mtime = datetime.fromtimestamp(out_file.stat().st_mtime)
                    time_str = mtime.strftime("%Y-%m-%d %H:%M")
                else:
                    time_str = run_ts
                n_ok = sum(1 for c in checks if c[1])
                result_str = "PASS" if all_pass else "FAIL"
                checks_str = f"{n_ok}/{len(checks)}"
                failed_checks = [f"{name}: {detail}" for name, passed, detail in checks if not passed]
                failed_str = "; ".join(failed_checks) if failed_checks else ""
                row_bg = PASS_BG if all_pass else FAIL_BG

            ws.append([cid, cat, case.get("description", ""), time_str,
                       expected_str, result_str, checks_str, failed_str])

            row_fill = fill(row_bg)
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=current_row, column=col)
                cell.fill = row_fill
                cell.border = border
                cell.font = Font(name=FONT, size=10,
                                 bold=(col == 6),   # bold the PASS/FAIL cell
                                 color=("276534" if result_str == "PASS"
                                        else "8B0000" if result_str == "FAIL"
                                        else "555555") if col == 6 else "1A1A2E")
                cell.alignment = center() if col in (1, 2, 4, 6, 7) else left()
            current_row += 1

    # Summary row
    total = len(rows)
    passed = sum(1 for _, ok, _ in rows if ok)
    failed = total - passed
    ws.append([])
    current_row += 1
    ws.append([f"Run: {run_ts}", "", "",
               f"Total: {total}",
               f"Passed: {passed}",
               f"Failed: {failed}",
               f"Skipped: {len(skipped)}", ""])
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=current_row, column=col)
        cell.font = Font(name=FONT, bold=True, size=10, color="1A1A2E")
        cell.fill = fill("F0F0F0")
        cell.border = border
        cell.alignment = center()

    # Column widths
    col_widths = [14, 16, 42, 18, 60, 9, 9, 55]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Freeze header + category rows
    ws.freeze_panes = "A2"

    # ── Summary sheet ──────────────────────────────────────────────────────────
    ws2 = wb.create_sheet("Summary")
    ws2.append(["PLANR Golden Dataset — Run Summary"])
    ws2["A1"].font = Font(name=FONT, bold=True, size=13, color=NAV)
    ws2.append(["Run timestamp", run_ts])
    ws2.append([])
    ws2.append(["Category", "Total", "Passed", "Failed", "Pass Rate"])

    # Header style for summary
    for col in range(1, 6):
        cell = ws2.cell(row=4, column=col)
        cell.font = hfont(bold=True, color=WHITE)
        cell.fill = fill(NAV)
        cell.alignment = center()
        cell.border = border

    cat_row = 5
    for cat in CATEGORY_ORDER:
        cat_cases_ids = {c["id"] for c in cases if c.get("category") == cat}
        cat_rows = [(cid, ok, chks) for cid, ok, chks in rows if cid in cat_cases_ids]
        cat_total = len(cat_rows)
        cat_pass = sum(1 for _, ok, _ in cat_rows if ok)
        cat_fail = cat_total - cat_pass
        rate = f"{(cat_pass/cat_total*100):.0f}%" if cat_total else "—"
        ws2.append([CATEGORY_LABELS[cat], cat_total, cat_pass, cat_fail, rate])
        for col in range(1, 6):
            cell = ws2.cell(row=cat_row, column=col)
            cell.font = Font(name=FONT, size=10)
            cell.border = border
            cell.alignment = center()
        cat_row += 1

    # Totals row
    ws2.append(["Total", total, passed, failed,
                f"{(passed/total*100):.0f}%" if total else "—"])
    for col in range(1, 6):
        cell = ws2.cell(row=cat_row, column=col)
        cell.font = Font(name=FONT, bold=True, size=10)
        cell.fill = fill("F0F0F0")
        cell.border = border
        cell.alignment = center()

    for col, w in enumerate([28, 10, 10, 10, 12], 1):
        ws2.column_dimensions[get_column_letter(col)].width = w

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
    print(f"  📊  Results saved → {out_path}")


def replay(cases: list[dict], only_id: str | None = None) -> None:
    rows: list[tuple[str, bool, list[tuple[str, bool, str]]]] = []
    skipped: list[str] = []

    for case in cases:
        cid = case["id"]
        if only_id and cid != only_id:
            continue

        out_file = OUT_DIR / f"{cid}.json"
        if not out_file.exists():
            print(f"  SKIP  {cid}  (no saved output — run --generate first)")
            skipped.append(cid)
            continue

        saved = json.loads(out_file.read_text())
        checks = check_case(case, saved)
        all_pass = all(c[1] for c in checks)
        rows.append((cid, all_pass, checks))

        icon = "PASS" if all_pass else "FAIL"
        n_ok = sum(1 for c in checks if c[1])
        print(f"  {icon}  {cid}  ({n_ok}/{len(checks)} checks)")
        if not all_pass:
            for name, passed, detail in checks:
                if not passed:
                    print(f"         ✗  {name}: {detail}")

    total = len(rows)
    passed = sum(1 for _, ok, _ in rows if ok)
    print(f"\n  {'─'*50}")
    print(f"  {passed}/{total} cases passed   |   {len(skipped)} skipped")
    if passed < total:
        failed_ids = [cid for cid, ok, _ in rows if not ok]
        print(f"  FAILED: {failed_ids}")
    print()

    # Always export xlsx after replay (unless single --case run)
    if not only_id:
        xlsx_path = OUT_DIR / "golden_replay.xlsx"
        export_xlsx(cases, rows, skipped, xlsx_path)

    sys.exit(0 if passed == total else 1)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="PLANR golden dataset runner")
    parser.add_argument("--generate", action="store_true", help="Call API, save outputs")
    parser.add_argument("--replay", action="store_true", help="Score saved outputs + export xlsx (free)")
    parser.add_argument("--case", metavar="ID", help="Single case only")
    args = parser.parse_args()

    if not args.generate and not args.replay:
        parser.print_help()
        sys.exit(1)

    cases = load_dataset()

    if args.generate:
        generate(cases, only_id=args.case)
    if args.replay:
        replay(cases, only_id=args.case)


if __name__ == "__main__":
    main()
