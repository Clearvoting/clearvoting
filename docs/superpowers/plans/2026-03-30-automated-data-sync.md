# Automated Data Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate ClearVote's weekly data sync — government data via GitHub Actions on Saturdays, AI generation via local /loop on Sundays.

**Architecture:** Add `--skip-ai` and `--ai-only` CLI flags to sync.py to partition the 12-step pipeline. Create a GitHub Actions workflow that runs the government-only sync on a Saturday cron schedule, commits changes to `main`, and triggers Render auto-deploy. AI generation runs locally via Claude Code /loop using the existing Claude Max plan.

**Tech Stack:** Python 3.12, GitHub Actions, existing sync.py pipeline, Render auto-deploy from `main`.

**Spec:** `docs/superpowers/specs/2026-03-22-automated-data-sync-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `sync.py` | Modify | Add `SYNC_STATES` constant, `--skip-ai` flag, `--ai-only` flag |
| `.github/workflows/weekly-sync.yml` | Create | GitHub Actions cron workflow for Saturday government sync |
| `tests/test_sync_flags.py` | Create | Tests for the new CLI flags and `SYNC_STATES` default |

---

## Task 1: Add `SYNC_STATES` constant and update default states

**Files:**
- Modify: `sync.py:36-51` (constants section) and `sync.py:1845` (states parsing in main)
- Create: `tests/test_sync_flags.py`

- [ ] **Step 1: Write the failing test for SYNC_STATES default**

```python
# tests/test_sync_flags.py
"""Tests for sync.py CLI flags and configuration."""
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def test_sync_states_constant_exists():
    """SYNC_STATES should be defined in sync.py with our 4 target states."""
    content = (PROJECT_ROOT / "sync.py").read_text()
    assert "SYNC_STATES" in content, "SYNC_STATES constant should exist in sync.py"
    assert '"NY"' in content, "SYNC_STATES should include NY"
    assert '"FL"' in content, "SYNC_STATES should include FL"
    assert '"CA"' in content, "SYNC_STATES should include CA"
    assert '"TX"' in content, "SYNC_STATES should include TX"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/Documents/Claude/Entrepreneurship/Non-Profit/ClearVote
source .venv/bin/activate
pytest tests/test_sync_flags.py::test_sync_states_constant_exists -v
```

Expected: FAIL — `SYNC_STATES` does not exist yet.

- [ ] **Step 3: Add SYNC_STATES constant to sync.py**

In `sync.py`, after the `CONGRESSES` constant (line 51), add:

```python
# Default states to sync — update this list when expanding coverage
# The --states CLI flag overrides this. Previously defaulted to all 50+ states/territories.
SYNC_STATES = ["NY", "FL", "CA", "TX"]
```

- [ ] **Step 4: Update states parsing in main() to use SYNC_STATES**

In `sync.py`, change line 1845 from:

```python
states = [s.strip().upper() for s in args.states.split(",")] if args.states else None
```

to:

```python
states = [s.strip().upper() for s in args.states.split(",")] if args.states else SYNC_STATES
```

And update the `sync_members` call — since `states` is now always a list (never `None`), the `states or US_STATES` fallback in `sync_members` won't trigger, which is the desired behavior.

Also update the metadata write (line 1946) from:

```python
"states_synced": states or US_STATES,
```

to:

```python
"states_synced": states,
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_sync_flags.py::test_sync_states_constant_exists -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sync.py tests/test_sync_flags.py
git commit -m "feat: add SYNC_STATES constant, default to 4 target states"
```

---

**Note:** After Task 1 adds ~3 lines for `SYNC_STATES`, all line numbers in Tasks 2–5 shift by ~3. Line numbers below are approximate — match by code content, not exact line number.

## Task 2: Add `--skip-ai` flag

**Files:**
- Modify: `sync.py` argparse section and steps 5-6, 8-9, 11 in main
- Modify: `tests/test_sync_flags.py`

- [ ] **Step 1: Write the failing test for --skip-ai**

Add to `tests/test_sync_flags.py`:

```python
import subprocess
import sys


def test_skip_ai_flag_accepted():
    """sync.py should accept --skip-ai without error."""
    result = subprocess.run(
        [sys.executable, "sync.py", "--help"],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)
    )
    assert "--skip-ai" in result.stdout, "--skip-ai should appear in help text"


def test_skip_ai_and_ai_only_mutually_exclusive():
    """--skip-ai and --ai-only should not be usable together."""
    result = subprocess.run(
        [sys.executable, "sync.py", "--skip-ai", "--ai-only"],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)
    )
    assert result.returncode != 0, "Should fail when both flags are provided"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sync_flags.py -v -k "skip_ai"
```

Expected: FAIL — `--skip-ai` flag doesn't exist yet.

- [ ] **Step 3: Add --skip-ai flag to argparse**

In `sync.py`, in the `main()` function's argparse section, before `args = parser.parse_args()`, add a mutually exclusive group:

```python
mode_group = parser.add_mutually_exclusive_group()
mode_group.add_argument("--skip-ai", action="store_true",
                        help="Skip AI-dependent steps (5,6,8,9,11). Run government data only.")
mode_group.add_argument("--ai-only", action="store_true",
                        help="Run only AI-dependent steps (5,6,8,9,11). Assumes gov data is fresh.")
```

This replaces the need for a manual check — argparse will reject `--skip-ai --ai-only` automatically with a clear error message.

- [ ] **Step 4: Verify mutual exclusivity works**

The `add_mutually_exclusive_group` handles this — no manual check needed.

- [ ] **Step 5: Wrap AI steps with skip_ai guard**

In the normal sync section of `main()`, wrap steps 5, 6, 8, 9, and 11 with conditionals. Replace the existing step blocks:

For steps 5 and 6 (lines 1890-1899), wrap:

```python
# Step 5: AI bill summaries (writer-grader loop)
summary_stats = {}
if not args.skip_ai:
    print()
    print(f"[5/12] Generating graded AI bill summaries ({'API' if anthropic_key else 'Claude CLI'})...")
    summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key or None, batch_size=5, rate_limit=1.0)
else:
    print()
    print("[5/12] Skipping AI bill summaries (--skip-ai)")

# Step 6: Bill arguments — both sides (writer-grader loop)
arguments_stats = {}
if not args.skip_ai:
    print()
    print(f"[6/12] Generating bill arguments ({'API' if anthropic_key else 'Claude CLI'})...")
    args_batch = 10 if not anthropic_key else 5
    arguments_stats = await sync_bill_arguments(SYNC_DIR, api_key=anthropic_key or None, batch_size=args_batch, rate_limit=1.0)
else:
    print()
    print("[6/12] Skipping bill arguments (--skip-ai)")
```

For step 8 (lines 1906-1909), wrap:

```python
# Step 8: Issue scorecard verdicts
if not args.skip_ai:
    print()
    print(f"[8/12] Generating issue scorecard verdicts ({'API' if anthropic_key else 'Claude CLI'})...")
    await generate_scorecard_verdicts(SYNC_DIR, api_key=anthropic_key or None)
else:
    print()
    print("[8/12] Skipping scorecard verdicts (--skip-ai)")
```

For step 9 (lines 1911-1914), wrap:

```python
# Step 9: Member summaries
member_summary_stats = {}
if not args.skip_ai:
    print()
    print(f"[9/12] Generating AI member summaries ({'API' if anthropic_key else 'Claude CLI'})...")
    member_summary_stats = await sync_member_summaries(SYNC_DIR, api_key=anthropic_key or None)
else:
    print()
    print("[9/12] Skipping AI member summaries (--skip-ai)")
```

For step 11 (lines 1934-1937), wrap:

```python
# Step 11: Page coherence check
coherence_stats = {}
if not args.skip_ai:
    print()
    print(f"[11/12] Checking page coherence ({'API' if anthropic_key else 'Claude CLI'})...")
    coherence_stats = await check_page_coherence(SYNC_DIR, api_key=anthropic_key or None)
else:
    print()
    print("[11/12] Skipping coherence check (--skip-ai)")
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_sync_flags.py -v -k "skip_ai"
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add sync.py tests/test_sync_flags.py
git commit -m "feat: add --skip-ai and --ai-only flags to sync.py"
```

---

## Task 3: Add `--ai-only` flag logic

**Files:**
- Modify: `sync.py:1844-1864` (normal sync mode entry point)
- Modify: `tests/test_sync_flags.py`

- [ ] **Step 1: Write the failing test for --ai-only**

Add to `tests/test_sync_flags.py`:

```python
def test_ai_only_flag_accepted():
    """sync.py should accept --ai-only without error."""
    result = subprocess.run(
        [sys.executable, "sync.py", "--help"],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)
    )
    assert "--ai-only" in result.stdout, "--ai-only should appear in help text"


def test_ai_only_skips_congress_key_check():
    """--ai-only should not require CONGRESS_API_KEY.

    We verify this by checking the code structure: the --ai-only block
    must return before the CONGRESS_API_KEY check. We don't run the
    actual sync (it would try to call Claude CLI and timeout).
    """
    content = (PROJECT_ROOT / "sync.py").read_text()
    # Find positions of key code patterns
    ai_only_return = content.find("if args.ai_only:")
    congress_key_check = content.find('CONGRESS_API_KEY not set')
    assert ai_only_return != -1, "--ai-only block should exist"
    assert congress_key_check != -1, "CONGRESS_API_KEY check should exist"
    assert ai_only_return < congress_key_check, \
        "--ai-only block should come before CONGRESS_API_KEY check"
    # Also verify the ai-only block has a return statement before the check
    between = content[ai_only_return:congress_key_check]
    assert "return" in between, "--ai-only block should return before CONGRESS_API_KEY check"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sync_flags.py -v -k "ai_only"
```

Expected: FAIL — `--ai-only` flag exists but doesn't bypass the API key check yet.

- [ ] **Step 3: Add --ai-only logic to main()**

In `sync.py`, restructure the normal sync mode. Replace the section starting at line 1844 (after all the special mode handlers) through the beginning of step 1:

```python
# --- Normal sync mode ---
states = [s.strip().upper() for s in args.states.split(",")] if args.states else SYNC_STATES

# --ai-only mode: skip government data steps, go straight to AI
if args.ai_only:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    print("=== ClearVote AI-Only Sync ===")
    print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
    print()

    # Step 5: AI bill summaries
    print("[5/12] Generating graded AI bill summaries...")
    summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key or None, batch_size=5, rate_limit=1.0)

    # Step 6: Bill arguments
    print()
    print("[6/12] Generating bill arguments...")
    args_batch = 10 if not anthropic_key else 5
    arguments_stats = await sync_bill_arguments(SYNC_DIR, api_key=anthropic_key or None, batch_size=args_batch, rate_limit=1.0)

    # Step 8: Issue scorecard verdicts
    print()
    print("[8/12] Generating issue scorecard verdicts...")
    await generate_scorecard_verdicts(SYNC_DIR, api_key=anthropic_key or None)

    # Step 9: Member summaries
    print()
    print("[9/12] Generating AI member summaries...")
    member_summary_stats = await sync_member_summaries(SYNC_DIR, api_key=anthropic_key or None)

    # Step 11: Page coherence check
    print()
    print("[11/12] Checking page coherence...")
    coherence_stats = await check_page_coherence(SYNC_DIR, api_key=anthropic_key or None)

    # Step 12: Write metadata
    # Include zero-value keys for gov fields so downstream code that reads
    # sync_metadata.json doesn't break on missing keys.
    print()
    print("[12/12] Writing sync metadata...")
    metadata = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "states_synced": states,
        "ai_only": True,
        "members_count": 0,
        "bills_count": 0,
        "senate_votes_count": 0,
        "house_votes_count": 0,
        "member_votes_count": 0,
        "donations_stats": {},
        "summary_stats": summary_stats,
        "arguments_stats": arguments_stats,
        "member_summary_stats": member_summary_stats,
        "coherence_stats": coherence_stats,
    }
    _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)

    print()
    print("=== AI-only sync complete ===")
    if summary_stats.get("total"):
        print(f"  Bill summaries: {summary_stats['total']} ({summary_stats.get('passed', 0)} passed)")
    if arguments_stats.get("total"):
        print(f"  Arguments: {arguments_stats['total']} ({arguments_stats.get('passed', 0)} passed)")
    if member_summary_stats.get("total"):
        print(f"  Member narratives: {member_summary_stats['total']} ({member_summary_stats.get('passed', 0)} passed)")
    return

api_key = os.getenv("CONGRESS_API_KEY", "")
if not api_key:
    print("ERROR: CONGRESS_API_KEY not set in .env")
    sys.exit(1)
```

The rest of the normal sync flow continues unchanged after this block.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_sync_flags.py -v -k "ai_only"
```

Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
pytest tests/ -v --timeout=30
```

Expected: All existing tests pass. No regressions.

- [ ] **Step 6: Commit**

```bash
git add sync.py tests/test_sync_flags.py
git commit -m "feat: add --ai-only mode that runs only AI-dependent sync steps"
```

---

## Task 4: Create GitHub Actions workflow

**Files:**
- Create: `.github/workflows/weekly-sync.yml`

- [ ] **Step 1: Create the .github/workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create the workflow file**

```yaml
# .github/workflows/weekly-sync.yml
# Automated weekly government data sync for ClearVote.
# Runs every Saturday at 10:00 UTC (~6 AM ET summer / 5 AM ET winter).
# Pulls members, votes, bills, and campaign finance data from public APIs.
# AI generation is handled separately via local Claude Code /loop on Sundays.

name: Weekly Government Data Sync

on:
  schedule:
    - cron: '0 10 * * 6'  # Saturday 10:00 UTC
  workflow_dispatch:  # Manual trigger for testing

jobs:
  sync:
    runs-on: ubuntu-latest
    timeout-minutes: 45

    steps:
      - name: Check out repo
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Configure git identity
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Run government data sync
        env:
          CONGRESS_API_KEY: ${{ secrets.CONGRESS_API_KEY }}
          FEC_API_KEY: ${{ secrets.FEC_API_KEY }}
        run: python sync.py --skip-ai

      - name: Commit and push if data changed
        run: |
          git add data/synced/
          if git diff --cached --quiet; then
            echo "No data changes — nothing to commit."
          else
            git commit -m "data: weekly government sync [automated]"
            git push
          fi
```

- [ ] **Step 3: Validate the YAML syntax**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/weekly-sync.yml')); print('Valid YAML')"
```

If `pyyaml` is not installed, use:

```bash
python -c "
import json, re
with open('.github/workflows/weekly-sync.yml') as f:
    content = f.read()
# Basic structural check: file starts with valid YAML
assert 'name:' in content, 'Missing name key'
assert 'on:' in content, 'Missing on trigger'
assert 'jobs:' in content, 'Missing jobs key'
assert 'actions/checkout' in content, 'Missing checkout step'
print('Basic structure valid')
"
```

Expected: Valid

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/weekly-sync.yml
git commit -m "ci: add weekly government data sync GitHub Actions workflow"
```

---

## Task 5: Update docstring and verify full pipeline

**Files:**
- Modify: `sync.py:1-12` (module docstring)

- [ ] **Step 1: Update the module docstring**

Replace the docstring at the top of `sync.py` (lines 1-12):

```python
"""ClearVote Data Sync Script

Pulls congressional data from Congress.gov and Senate.gov
and saves everything as JSON files in data/synced/ for the
web app to serve.

Usage:
    cd ~/Documents/Claude/Entrepreneurship/Non-Profit/ClearVote
    source .venv/bin/activate

    # Full sync (all 12 steps):
    python sync.py

    # Government data only (for GitHub Actions Saturday cron):
    python sync.py --skip-ai

    # AI generation only (for Sunday /loop via Claude Code):
    python sync.py --ai-only

    # Override default states:
    python sync.py --states NY,FL,CA,TX

    # Skip campaign finance:
    python sync.py --skip-ai --skip-donations
"""
```

- [ ] **Step 2: Run full test suite**

```bash
cd ~/Documents/Claude/Entrepreneurship/Non-Profit/ClearVote
source .venv/bin/activate
pytest tests/ -v --timeout=60
```

Expected: All tests pass, including the new flag tests.

- [ ] **Step 3: Dry-run --skip-ai to verify it starts correctly**

```bash
python sync.py --skip-ai 2>&1 | head -20
```

Expected output should show:
- `=== ClearVote Data Sync ===`
- Steps 1–4, 7, 10 running
- Steps 5, 6, 8, 9, 11 printing "Skipping ... (--skip-ai)"

(Can cancel with Ctrl+C after confirming the output looks right — no need to wait for full API sync.)

- [ ] **Step 4: Dry-run --ai-only to verify it starts correctly**

```bash
python sync.py --ai-only 2>&1 | head -10
```

Expected output should show:
- `=== ClearVote AI-Only Sync ===`
- Mode: Claude CLI (Max plan)
- Steps 5, 6, 8, 9, 11 running

(Can cancel with Ctrl+C after confirming.)

- [ ] **Step 5: Commit**

```bash
git add sync.py
git commit -m "docs: update sync.py docstring with new flag usage examples"
```

---

## Task 6: Add GitHub secrets and test workflow

**Files:** None (GitHub web UI + manual verification)

This task is done manually by the user.

- [ ] **Step 1: Add secrets to GitHub repo**

Go to the ClearVote GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

1. `CONGRESS_API_KEY` — copy from `.env` file
2. `FEC_API_KEY` — copy from `.env` file

- [ ] **Step 2: Trigger a manual workflow run**

Go to the repo → Actions tab → "Weekly Government Data Sync" → "Run workflow" → Run.

Watch the logs to confirm:
- Python installs correctly
- `sync.py --skip-ai` runs
- Steps 5, 6, 8, 9, 11 are skipped
- Data files are committed (or "No data changes" if nothing new)

- [ ] **Step 3: Verify Render deployment**

If the workflow pushed a commit, check Render dashboard to confirm auto-deploy was triggered and the site is serving fresh data (check the footer "Data last updated" timestamp).

---

## Summary

| Task | What it does | Files |
|------|-------------|-------|
| 1 | Add `SYNC_STATES` constant, update default | `sync.py`, `tests/test_sync_flags.py` |
| 2 | Add `--skip-ai` flag | `sync.py`, `tests/test_sync_flags.py` |
| 3 | Add `--ai-only` flag logic | `sync.py`, `tests/test_sync_flags.py` |
| 4 | Create GitHub Actions workflow | `.github/workflows/weekly-sync.yml` |
| 5 | Update docstring, verify full pipeline | `sync.py` |
| 6 | Add GitHub secrets, test workflow | GitHub web UI (manual) |
