"""Grade existing AI summaries and regenerate failures.

Saves progress incrementally to data/synced/audit_grades.json
so it can be resumed if interrupted.

Usage:
    source .venv/bin/activate
    python audit_summaries.py                      # Grade all (4 parallel workers)
    python audit_summaries.py --workers 6           # Grade with 6 parallel workers
    python audit_summaries.py --fix                 # Regenerate failures (parallel)
    python audit_summaries.py --fix --upgrade        # Also upgrade B grades to A
    python audit_summaries.py --fix --workers 2     # Regenerate with 2 workers
    python audit_summaries.py --rebuild             # Rebuild member votes
    python audit_summaries.py --status              # Show current progress
"""

import asyncio
import json
import sys
import threading
from pathlib import Path

BASE_DIR = Path(__file__).parent
SYNC_DIR = BASE_DIR / "data" / "synced"
CACHE_DIR = BASE_DIR / "data" / "cache"
GRADES_PATH = SYNC_DIR / "audit_grades.json"

# Thread lock for safe file writes from concurrent tasks
_write_lock = threading.Lock()


def _atomic_write_json(path: Path, data: dict | list) -> None:
    import os, tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _save_grades(grades: dict) -> None:
    """Thread-safe save of grades dict."""
    with _write_lock:
        _atomic_write_json(GRADES_PATH, grades)


def _save_summaries(summaries: dict) -> None:
    """Thread-safe save of summaries dict."""
    with _write_lock:
        _atomic_write_json(SYNC_DIR / "ai_summaries.json", summaries)


def _print_status() -> None:
    """Print current grading status."""
    if not GRADES_PATH.exists():
        print("No audit_grades.json yet — run grading first")
        return

    grades = json.load(open(GRADES_PATH))
    dist = {}
    for g in grades.values():
        dist[g["grade"]] = dist.get(g["grade"], 0) + 1
    passed = sum(1 for g in grades.values() if g["passed"])
    failed = sum(1 for g in grades.values() if not g["passed"])

    print(f"Graded: {len(grades)}/177")
    print(f"Grades: {dict(sorted(dist.items()))}")
    print(f"Passed: {passed}, Failed: {failed}")
    print(f"Remaining to grade: {177 - len(grades)}")

    # Show failures needing fix
    already_fixed = sum(1 for g in grades.values() if not g.get("original_failed"))
    needs_fix = sum(1 for g in grades.values() if not g["passed"])
    print(f"Failures needing regeneration: {needs_fix}")


async def grade_all(workers: int = 4) -> None:
    """Phase 1: Grade existing summaries with parallel workers."""
    from app.services.summary_grader import SummaryGrader

    bills = json.load(open(SYNC_DIR / "bills.json")).get("bills", [])
    summaries = json.load(open(SYNC_DIR / "ai_summaries.json"))

    # Load existing grades (for resume)
    grades: dict[str, dict] = {}
    if GRADES_PATH.exists():
        grades = json.load(open(GRADES_PATH))

    bill_lookup = {}
    for bill in bills:
        bt = bill.get("type", "").lower()
        bn = bill.get("number", "")
        key = f"{bill.get('congress', 119)}-{bt}-{bn}"
        bill_lookup[key] = bill

    # Build work queue — only bills not yet graded
    work = [(k, s) for k, s in summaries.items() if k not in grades]

    total = len(summaries)
    already_done = total - len(work)
    print(f"Summaries: {total}, Already graded: {already_done}, Remaining: {len(work)}")
    print(f"Workers: {workers}")
    print()

    if not work:
        print("All summaries already graded!")
        _print_status()
        return

    sem = asyncio.Semaphore(workers)
    counter = {"done": 0}

    async def grade_one(key: str, summary: dict) -> None:
        # Double-check not already done (another worker might have saved it)
        if key in grades:
            return

        bill = bill_lookup.get(key, {})
        title = bill.get("title", key)
        official = ""
        if bill.get("summaries"):
            official = bill["summaries"][0].get("text", "")

        grader = SummaryGrader(api_key=None)

        async with sem:
            result = await grader.grade(
                summary_type="bill_summary",
                summary_text=json.dumps(summary),
                context={"title": title, "official_summary": official},
            )

        grades[key] = {
            "grade": result.grade,
            "passed": result.passed,
            "feedback": result.feedback,
        }

        counter["done"] += 1
        status = f"PASS ({result.grade})" if result.passed else f"FAIL ({result.grade})"
        print(f"  [{already_done + counter['done']}/{total}] {status} — {title[:60]}")

        _save_grades(grades)

    # Process in batches to avoid overwhelming the system
    batch_size = workers * 3
    for batch_start in range(0, len(work), batch_size):
        batch = work[batch_start:batch_start + batch_size]
        tasks = [grade_one(k, s) for k, s in batch]
        await asyncio.gather(*tasks)

    print()
    _print_status()


async def fix_failures(workers: int = 4) -> None:
    """Phase 2: Regenerate failed summaries with parallel workers."""
    from app.services.cache import CacheService
    from app.services.ai_summary import AISummaryService
    from app.services.summary_grader import SummaryGrader
    from app.services.writer_grader_loop import WriterGraderLoop

    if not GRADES_PATH.exists():
        print("No audit_grades.json — run grading first")
        return

    grades = json.load(open(GRADES_PATH))
    bills = json.load(open(SYNC_DIR / "bills.json")).get("bills", [])
    summaries = json.load(open(SYNC_DIR / "ai_summaries.json"))

    # --upgrade mode: also target B grades (not just failures)
    upgrade = "--upgrade" in sys.argv
    if upgrade:
        failures = [(k, g) for k, g in grades.items() if not g["passed"] or g["grade"] == "B"]
    else:
        failures = [(k, g) for k, g in grades.items() if not g["passed"]]
    if not failures:
        print("No failures to fix!")
        return

    bill_lookup = {}
    for bill in bills:
        bt = bill.get("type", "").lower()
        bn = bill.get("number", "")
        key = f"{bill.get('congress', 119)}-{bt}-{bn}"
        bill_lookup[key] = bill

    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)

    print(f"Regenerating {len(failures)} failed summaries...")
    print(f"Workers: {workers}")
    print()

    sem = asyncio.Semaphore(workers)
    stats = {"fixed": 0, "still_failing": 0, "done": 0}

    async def fix_one(key: str, grade_info: dict) -> None:
        # Re-check in case another worker/session already fixed it
        current = grades.get(key, {})
        if current.get("passed") and (not upgrade or current.get("grade") != "B"):
            return

        bill = bill_lookup.get(key, {})
        title = bill.get("title", key)
        official = ""
        if bill.get("summaries"):
            official = bill["summaries"][0].get("text", "")
        bill_text = ""
        tv = bill.get("textVersions")
        if isinstance(tv, list) and tv:
            bill_text = tv[0].get("text", "") if isinstance(tv[0], dict) else ""

        writer = AISummaryService(api_key=None, cache=cache)
        grader = SummaryGrader(api_key=None)

        async def writer_fn(grader_feedback=None, _key=key, _title=title, _official=official, _bill_text=bill_text, **kwargs):
            return await writer.generate_summary(
                bill_id=f"regen-{_key}",
                title=_title,
                official_summary=_official,
                bill_text_excerpt=_bill_text[:2000],
                grader_feedback=grader_feedback,
            )

        async with sem:
            loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
            result = await loop.run(
                summary_type="bill_summary",
                writer_kwargs={},
                grader_context={"title": title, "official_summary": official},
            )

        new_summary = result.best_summary
        if result.needs_review:
            new_summary["needs_review"] = True
            stats["still_failing"] += 1
            label = f"STILL FAILING ({result.best_grade.grade})"
        else:
            stats["fixed"] += 1
            label = f"FIXED ({result.best_grade.grade})"

        summaries[key] = new_summary
        grades[key] = {
            "grade": result.best_grade.grade,
            "passed": result.best_grade.passed,
            "feedback": result.best_grade.feedback,
        }

        stats["done"] += 1
        print(f"  [{stats['done']}/{len(failures)}] {label} — {title[:55]}")

        _save_grades(grades)
        _save_summaries(summaries)

    # Process in batches
    batch_size = workers * 2
    for batch_start in range(0, len(failures), batch_size):
        batch = failures[batch_start:batch_start + batch_size]
        tasks = [fix_one(k, g) for k, g in batch]
        await asyncio.gather(*tasks)

    print()
    print(f"Fixed: {stats['fixed']}, Still need review: {stats['still_failing']}")


async def rebuild_votes() -> None:
    """Phase 3: Rebuild member voting records with updated summaries."""
    sys.path.insert(0, str(BASE_DIR))
    from sync import build_member_votes
    await build_member_votes(SYNC_DIR)


def _parse_workers() -> int:
    """Parse --workers N from argv."""
    for i, arg in enumerate(sys.argv):
        if arg == "--workers" and i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
    return 4


if __name__ == "__main__":
    workers = _parse_workers()

    if "--status" in sys.argv:
        _print_status()
    elif "--fix" in sys.argv:
        asyncio.run(fix_failures(workers=workers))
    elif "--rebuild" in sys.argv:
        asyncio.run(rebuild_votes())
    else:
        asyncio.run(grade_all(workers=workers))
