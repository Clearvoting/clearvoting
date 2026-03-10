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


# --- Content-type scoping tests ---


def test_content_type_scoping_isolates_learnings():
    """Learnings for different content types are isolated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)

        gl.add_learning("Bill pattern A", content_type="bill_summary")
        gl.add_learning("Narrative pattern B", content_type="member_narrative")
        gl.add_learning("Coherence pattern C", content_type="page_coherence")

        assert "Bill pattern A" in gl.get_learnings(content_type="bill_summary")
        assert "Bill pattern A" not in gl.get_learnings(content_type="member_narrative")
        assert "Narrative pattern B" in gl.get_learnings(content_type="member_narrative")
        assert "Coherence pattern C" in gl.get_learnings(content_type="page_coherence")


def test_content_type_scoping_batch_history():
    """Batch history is scoped by content type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)

        gl.record_batch(total=10, passed=8, failed=2,
                        grade_distribution={"A": 8, "B": 0, "C": 2, "D": 0, "F": 0},
                        needs_review_ids=[], content_type="bill_summary")

        gl.record_batch(total=5, passed=4, failed=1,
                        grade_distribution={"A": 4, "B": 0, "C": 1, "D": 0, "F": 0},
                        needs_review_ids=[], content_type="member_narrative")

        assert len(gl.get_batch_history(content_type="bill_summary")) == 1
        assert gl.get_batch_history(content_type="bill_summary")[0]["total"] == 10
        assert len(gl.get_batch_history(content_type="member_narrative")) == 1
        assert gl.get_batch_history(content_type="member_narrative")[0]["total"] == 5
        assert gl.get_batch_history(content_type="page_coherence") == []


def test_flat_to_nested_migration():
    """Old flat format is migrated to bill_summary key on load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"

        # Write old flat format
        flat_data = {
            "learnings": ["CRA votes are tricky", "Avoid jargon"],
            "batch_history": [{"total": 5, "passed": 3, "failed": 2}],
        }
        with open(path, "w") as f:
            json.dump(flat_data, f)

        # Load — should migrate
        gl = GraderLearnings(path)

        # Old learnings should now be under bill_summary
        assert "CRA votes are tricky" in gl.get_learnings(content_type="bill_summary")
        assert "Avoid jargon" in gl.get_learnings(content_type="bill_summary")

        # Other content types should be empty
        assert gl.get_learnings(content_type="member_narrative") == []

        # Batch history should migrate too
        history = gl.get_batch_history(content_type="bill_summary")
        assert len(history) == 1
        assert history[0]["total"] == 5


def test_flat_to_nested_migration_persists_on_save():
    """Migrated data is saved in new format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"

        # Write old flat format
        flat_data = {"learnings": ["Old pattern"], "batch_history": []}
        with open(path, "w") as f:
            json.dump(flat_data, f)

        # Load, add new learning, save
        gl = GraderLearnings(path)
        gl.add_learning("New narrative pattern", content_type="member_narrative")
        gl.save()

        # Reload and verify new format
        gl2 = GraderLearnings(path)
        assert "Old pattern" in gl2.get_learnings(content_type="bill_summary")
        assert "New narrative pattern" in gl2.get_learnings(content_type="member_narrative")

        # Verify file structure
        with open(path) as f:
            raw = json.load(f)
        assert "bill_summary" in raw
        assert "member_narrative" in raw
        # Old flat keys should NOT exist
        assert "learnings" not in raw


def test_default_content_type_is_bill_summary():
    """Default content type for backward compat is bill_summary."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)

        gl.add_learning("Test pattern")
        assert "Test pattern" in gl.get_learnings()
        assert "Test pattern" in gl.get_learnings(content_type="bill_summary")


def test_content_type_extract_patterns():
    """extract_patterns works with content_type parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)

        feedback = [
            "Cherry-picking environmental votes",
            "Cherry-picking minority positions",
            "Good narrative",
        ]
        patterns = gl.extract_patterns(feedback, threshold=0.5,
                                       content_type="member_narrative")
        assert len(patterns) > 0
