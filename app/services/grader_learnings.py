import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CONTENT_TYPE = "bill_summary"


class GraderLearnings:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            with open(self.path, "r") as f:
                raw = json.load(f)

            # Migration: flat format → nested content-type format
            if "learnings" in raw and isinstance(raw.get("learnings"), list):
                # Old flat format — migrate to bill_summary key
                self._data = {
                    DEFAULT_CONTENT_TYPE: {
                        "learnings": raw["learnings"],
                        "batch_history": raw.get("batch_history", []),
                    }
                }
            else:
                self._data = raw
        else:
            self._data = {}

    def _ensure_section(self, content_type: str) -> dict:
        if content_type not in self._data:
            self._data[content_type] = {"learnings": [], "batch_history": []}
        return self._data[content_type]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def get_learnings(self, content_type: str = DEFAULT_CONTENT_TYPE) -> list[str]:
        section = self._data.get(content_type, {})
        return list(section.get("learnings", []))

    def add_learning(self, learning: str, content_type: str = DEFAULT_CONTENT_TYPE) -> None:
        section = self._ensure_section(content_type)
        if learning not in section["learnings"]:
            section["learnings"].append(learning)

    def extract_patterns(
        self, feedback_list: list[str], threshold: float = 0.3,
        content_type: str = DEFAULT_CONTENT_TYPE,
    ) -> list[str]:
        """Extract frequently occurring words/phrases from grader feedback.

        Returns phrases that appear in more than threshold fraction of feedback items.
        """
        if not feedback_list:
            return []

        # Simple word-frequency approach — find phrases appearing often
        word_counts: Counter = Counter()
        for feedback in feedback_list:
            words = set(feedback.lower().split())
            for word in words:
                if len(word) > 4:  # skip short common words
                    word_counts[word] += 1

        total = len(feedback_list)
        patterns = []
        for word, count in word_counts.most_common(10):
            if count / total >= threshold:
                # Find the original feedback that contains this word as representative example
                for fb in feedback_list:
                    if word in fb.lower():
                        patterns.append(fb)
                        break

        return patterns

    def record_batch(
        self,
        total: int,
        passed: int,
        failed: int,
        grade_distribution: dict[str, int],
        needs_review_ids: list[str],
        content_type: str = DEFAULT_CONTENT_TYPE,
    ) -> None:
        section = self._ensure_section(content_type)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "grade_distribution": grade_distribution,
            "needs_review_ids": needs_review_ids,
        }
        section["batch_history"].append(entry)

    def get_batch_history(self, content_type: str = DEFAULT_CONTENT_TYPE) -> list[dict]:
        section = self._data.get(content_type, {})
        return section.get("batch_history", [])
