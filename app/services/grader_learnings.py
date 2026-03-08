import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class GraderLearnings:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {"learnings": [], "batch_history": []}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            with open(self.path, "r") as f:
                self._data = json.load(f)

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

    def get_learnings(self) -> list[str]:
        return list(self._data.get("learnings", []))

    def add_learning(self, learning: str) -> None:
        if learning not in self._data["learnings"]:
            self._data["learnings"].append(learning)

    def extract_patterns(self, feedback_list: list[str], threshold: float = 0.3) -> list[str]:
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
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "grade_distribution": grade_distribution,
            "needs_review_ids": needs_review_ids,
        }
        self._data["batch_history"].append(entry)

    def get_batch_history(self) -> list[dict]:
        return self._data.get("batch_history", [])
