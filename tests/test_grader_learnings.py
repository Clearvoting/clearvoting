import pytest
import json
import tempfile
from pathlib import Path
from app.services.grader_learnings import GraderLearnings


def test_load_empty_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        gl = GraderLearnings(Path(tmpdir) / "learnings.json")
        assert gl.get_learnings() == []


def test_save_and_load_learnings():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        gl.add_learning("Writers frequently use 'fiscal year'")
        gl.save()

        gl2 = GraderLearnings(path)
        assert "Writers frequently use 'fiscal year'" in gl2.get_learnings()


def test_no_duplicate_learnings():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        gl.add_learning("CRA resolutions are misinterpreted")
        gl.add_learning("CRA resolutions are misinterpreted")
        assert gl.get_learnings().count("CRA resolutions are misinterpreted") == 1


def test_extract_patterns_from_feedback_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        feedback_list = [
            "Uses 'fiscal year' — say 'the year starting October 2025'",
            "Contains 'fiscal year' jargon",
            "Good summary, no issues",
            "Uses 'fiscal year' again",
            "Acronym-only title not expanded",
        ]
        # 'fiscal year' appears 3/5 times — should be extracted as a pattern
        patterns = gl.extract_patterns(feedback_list, threshold=0.4)
        assert len(patterns) > 0


def test_record_batch_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        gl.record_batch(
            total=10,
            passed=7,
            failed=3,
            grade_distribution={"A": 4, "B": 3, "C": 2, "D": 1, "F": 0},
            needs_review_ids=["119-hr-100", "119-s-200", "119-hjres-50"],
        )
        gl.save()

        gl2 = GraderLearnings(path)
        history = gl2.get_batch_history()
        assert len(history) == 1
        assert history[0]["total"] == 10
        assert history[0]["passed"] == 7
