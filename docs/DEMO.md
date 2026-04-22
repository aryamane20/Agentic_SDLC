# DEMO.md — Pre-demo checklist

Use this before any live demo of the P2 PLANR HITL system.

---

## 1. Start the stack

```bash
make api       # FastAPI on :8000  (start first — frontend proxies to it)
make frontend  # Vite on :5180
```

Verify both are healthy:

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

Open [http://localhost:5180/plan](http://localhost:5180/plan) in the browser.

---

## 2. Reset between runs

```bash
rm -rf sessions/   # wipes all session JSON — each browser tab starts fresh
```

Or just open an incognito window (new `X-Planr-User` UUID is generated per browser tab).

---

## 3. Scenarios

### Scenario A — Happy path (gate should NOT fire)

Brief to paste:
```
Build an internal analytics dashboard for the data engineering team.
The dashboard will surface pipeline health metrics from Snowflake.
Timeline: 12 weeks. Budget: $120k.
Team: 2 backend engineers, 1 frontend engineer, 1 data analyst, 1 PM.
```

**What to expect:**
- Confidence score ≥ 60
- No CRITICAL risks
- Gate banner shows "No blocking gate — use Refine below to iterate"
- Approve button works cleanly → green "Plan approved" + Copy/Download JSON

---

### Scenario B — Low confidence (gate fires on confidence < 60)

Brief to paste:
```
Build something for our customers. It should help them do things faster.
Timeline: ASAP. Budget: TBD.
```

**What to expect:**
- Confidence score < 60 (vague brief)
- Gate fires: amber "confidence_score < 60" reason shown
- You can still Refine — type "Clarify scope: the product is a mobile app for expense tracking. Budget is $80k."
- After refine, confidence may rise and gate may clear

---

### Scenario C — Critical risk (gate fires on CRITICAL risk + viability)

Brief file: `inputs/test-cases-p2/scenario-c-critical-risk/brief.txt`
(paste its contents, or use the Upload PRD button)

**What to expect:**
- CRITICAL risk: EPIC integration unfinished design
- Possibly NOT_VIABLE: fixed public deadline with understaffed team
- Gate fires with 2+ reason strings (all CRITICAL risks listed, not just the first)
- Refine to add: "Add a security/compliance contractor. Push launch to 2026-08-01."
- Gate may clear after mitigation round

---

## 4. Features to show

| Feature | How |
|---------|-----|
| Session sidebar | Multiple browser tabs → different sessions appear in sidebar; active one is highlighted in bold |
| Session restore | Reload page → sidebar still shows past sessions; click one to restore |
| Gate reasons | Scenario C shows all CRITICAL reasons (not truncated at first) |
| Refinement loop | Refine through a fired gate without approving first |
| Approve + export | Approve → "Copy JSON" and "Download JSON" appear |
| PRD upload | Click `+` in composer → upload a `.pdf` or `.docx` |
| PRD error messages | Upload a `.exe` → "Unsupported file type" message (not raw JSON) |
| Empty state | Open a fresh incognito tab → "Start a plan" heading with disabled Generate button |

---

## 5. Quick sanity check (no browser)

```bash
# All P2 tests pass before going live
make test-p2-baseline

# Expected: 45 passed, 0 failed
```
