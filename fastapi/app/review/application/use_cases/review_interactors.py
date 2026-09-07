"""평가·신뢰 인터랙터. 판단은 `domain/rules/review_rules.py` 가 한다."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.review.application.dtos.review_dto import (
    FileReportCommand,
    NoShowResult,
    RecordNoShowCommand,
    ReportResult,
    ReviewOptionResult,
    ReviewResult,
    SubmitReviewCommand,
)
from app.review.application.ports.input.review_use_cases import (
    FileReportUseCase,
    ListReviewOptionsUseCase,
    RecordNoShowUseCase,
    SubmitReviewUseCase,
)
from app.review.application.ports.output.review_port import ReviewPort
from app.review.domain.entities.review_entity import (
    NoShowEntity,
    ReportEntity,
    ReviewEntity,
)
from app.review.domain.rules.review_rules import (
    can_record_no_show,
    is_self_review,
    reviewable_at,
    within_window,
)


class _Base:
    def __init__(self, repository: ReviewPort) -> None:
        self._repository = repository

    def _played_at_or_404(self, match_id: UUID) -> datetime:
        played_at = self._repository.match_played_at(match_id)
        if played_at is None:
            raise ApiError(404, "MATCH_NOT_FOUND", "경기를 찾을 수 없습니다.")
        return played_at


class ListReviewOptionsInteractor(ListReviewOptionsUseCase):
    def __init__(self, repository: ReviewPort) -> None:
        self._repository = repository

    def __call__(self) -> list[ReviewOptionResult]:
        return [
            ReviewOptionResult(code=o.code, category=o.category, label=o.label)
            for o in self._repository.list_options()
        ]


class SubmitReviewInteractor(_Base, SubmitReviewUseCase):
    def __call__(self, command: SubmitReviewCommand) -> ReviewResult:
        played_at = self._played_at_or_404(command.match_id)
        now = datetime.now(timezone.utc)

        if not reviewable_at(played_at, now):
            # 아직 안 끝난 경기와 기간이 지난 경기를 **가른다** — 화면이
            # "아직입니다"와 "늦었습니다"를 다르게 안내해야 한다.
            if within_window(played_at, now):
                raise ApiError(
                    422, "MATCH_NOT_PLAYED", "아직 끝나지 않은 경기입니다."
                )
            raise ApiError(422, "REVIEW_WINDOW_CLOSED", "평가 기간이 지났습니다.")

        if is_self_review(command.actor_id, command.reviewee_id):
            raise ApiError(422, "SELF_REVIEW", "자기 자신은 평가할 수 없습니다.")

        # 🔴 **둘 다 확정된 참가자여야 한다.** 평가자를 안 보면 남의 경기에
        #    끼어들어 평가할 수 있고, 대상을 안 보면 안 뛴 사람에게 붙는다.
        if not self._repository.is_confirmed_participant(
            command.match_id, command.actor_id
        ):
            raise ApiError(403, "FORBIDDEN", "이 경기의 참가자가 아닙니다.")
        if not self._repository.is_confirmed_participant(
            command.match_id, command.reviewee_id
        ):
            raise ApiError(
                422, "NOT_A_PARTICIPANT", "평가 대상이 이 경기의 참가자가 아닙니다."
            )

        codes = list(dict.fromkeys(command.option_codes))   # 중복 제거, 순서 유지
        if not codes:
            raise ApiError(422, "NO_OPTION_SELECTED", "선택지를 하나 이상 골라 주십시오.")
        unknown = sorted(set(codes) - self._repository.option_codes())
        if unknown:
            raise ApiError(
                422, "UNKNOWN_OPTION", f"없는 선택지입니다: {', '.join(unknown)}"
            )

        review = ReviewEntity(
            id=uuid4(),
            match_id=command.match_id,
            reviewer_id=command.actor_id,
            reviewee_id=command.reviewee_id,
            submitted_at=now,
            selected_codes=codes,
        )
        if not self._repository.save_review(review):
            raise ApiError(409, "ALREADY_REVIEWED", "이미 평가한 상대입니다.")

        return ReviewResult(
            id=review.id,
            match_id=review.match_id,
            reviewer_id=review.reviewer_id,
            reviewee_id=review.reviewee_id,
            submitted_at=review.submitted_at,
            selected_codes=review.selected_codes,
        )


class RecordNoShowInteractor(_Base, RecordNoShowUseCase):
    def __call__(self, command: RecordNoShowCommand) -> NoShowResult:
        played_at = self._played_at_or_404(command.match_id)
        now = datetime.now(timezone.utc)

        if played_at >= now:
            raise ApiError(422, "MATCH_NOT_PLAYED", "아직 끝나지 않은 경기입니다.")

        # 🔴 주최 팀 주장만. 제재 기록이라 만들 수 있는 사람을 좁힌다
        #    (`review_rules` 의 근거 참고).
        role = self._repository.team_role_of(command.match_id, command.actor_id)
        if not can_record_no_show(role):
            raise ApiError(403, "FORBIDDEN", "주장만 불참을 기록할 수 있습니다.")

        if not self._repository.is_confirmed_participant(
            command.match_id, command.user_id
        ):
            raise ApiError(
                422, "NOT_A_PARTICIPANT", "이 경기에 확정된 사람이 아닙니다."
            )

        no_show = NoShowEntity(
            id=uuid4(),
            match_id=command.match_id,
            user_id=command.user_id,
            recorded_at=now,
        )
        if not self._repository.save_no_show(no_show):
            raise ApiError(409, "ALREADY_RECORDED", "이미 기록된 불참입니다.")

        return NoShowResult(
            id=no_show.id,
            match_id=no_show.match_id,
            user_id=no_show.user_id,
            recorded_at=no_show.recorded_at,
        )


class FileReportInteractor(FileReportUseCase):
    def __init__(self, repository: ReviewPort) -> None:
        self._repository = repository

    def __call__(self, command: FileReportCommand) -> ReportResult:
        if command.actor_id == command.target_user_id:
            raise ApiError(422, "SELF_REPORT", "자기 자신은 신고할 수 없습니다.")
        if not self._repository.user_exists(command.target_user_id):
            raise ApiError(404, "USER_NOT_FOUND", "사용자를 찾을 수 없습니다.")

        report = ReportEntity(
            id=uuid4(),
            reporter_id=command.actor_id,
            target_user_id=command.target_user_id,
            reason=command.reason,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_report(report)
        # ⚠️ 접수만 한다. **처리하는 경로는 없다** — 관리자 화면이 생기면 붙인다.
        return ReportResult(
            id=report.id,
            target_user_id=report.target_user_id,
            created_at=report.created_at,
        )
