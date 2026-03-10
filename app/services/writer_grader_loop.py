import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from app.services.grader_common import Grader, GradeResult, GRADE_ORDER

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3


@dataclass
class LoopResult:
    best_summary: dict
    best_grade: GradeResult
    rounds: int
    needs_review: bool
    all_grades: list[str] = field(default_factory=list)


class WriterGraderLoop:
    def __init__(self, writer_fn: Callable[..., Awaitable[dict]], grader: Grader):
        self.writer_fn = writer_fn
        self.grader = grader

    async def run(
        self,
        summary_type: str,
        writer_kwargs: dict[str, Any],
        grader_context: dict[str, Any],
    ) -> LoopResult:
        best_summary: dict | None = None
        best_grade: GradeResult | None = None
        all_grades: list[str] = []
        last_feedback: str | None = None

        for round_num in range(1, MAX_ROUNDS + 1):
            # Build writer kwargs for this round
            round_kwargs = dict(writer_kwargs)
            if last_feedback:
                round_kwargs["grader_feedback"] = last_feedback

            # Write
            summary = await self.writer_fn(**round_kwargs)

            # Grade
            summary_text = json.dumps(summary) if isinstance(summary, dict) else str(summary)
            grade_result = await self.grader.grade(
                summary_type=summary_type,
                summary_text=summary_text,
                context=grader_context,
            )

            all_grades.append(grade_result.grade)
            logger.info(
                "Round %d/%d: grade=%s passed=%s",
                round_num, MAX_ROUNDS, grade_result.grade, grade_result.passed,
            )

            # Track best
            if best_grade is None or GRADE_ORDER.get(grade_result.grade, 0) > GRADE_ORDER.get(best_grade.grade, 0):
                best_summary = summary
                best_grade = grade_result

            last_feedback = grade_result.feedback

            # Early exit: an A can't be improved
            if grade_result.grade == "A":
                break

        needs_review = not best_grade.passed

        return LoopResult(
            best_summary=best_summary,
            best_grade=best_grade,
            rounds=len(all_grades),
            needs_review=needs_review,
            all_grades=all_grades,
        )
