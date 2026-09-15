"""내 정보 수정 인터랙터.

닉네임(항상 보냄)과 지인 검색 노출 여부(선택, 미결 `jin` 35번)를 바꾼다. 이메일은
계정 식별자라(부록 D.7 유일 제약) 바꾸려면 재인증·중복 검사가 붙으므로 별건이다.
"""

from __future__ import annotations

from dataclasses import replace

from app.core.errors import ApiError
from app.user.application.dtos.me_dto import UNSET, MeResult, UpdateMeCommand
from app.user.application.ports.input.update_me_use_case import UpdateMeUseCase
from app.user.application.ports.output.user_port import UserPort
from app.user.application.use_cases.me_assembler import build_me_result
from app.user.domain.rules.membership_rules import active_memberships
from app.user.domain.value_objects.nickname_vo import Nickname


class UpdateMeInteractor(UpdateMeUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: UpdateMeCommand) -> MeResult:
        user = self._repository.get(command.user_id)
        if user is None:
            # 토큰은 유효한데 사용자가 없다 — 탈퇴했거나 위조된 id 다.
            # 조회(`MeInteractor`)와 같은 판단이어야 화면 동작이 갈리지 않는다.
            raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")

        # 정규화(앞뒤 공백 제거)는 값 객체가 한다. 여기서 strip 을 또 하면
        # "어디선가 빼먹는" 자리가 하나 더 생긴다.
        nickname = Nickname.of(command.nickname)
        self._repository.update_nickname(user.id, nickname)

        # `UNSET`이면 안 건드린다 — 보낸 필드만 바뀌는 규칙(`card`의
        # `UpdateMyCardCommand`와 같은 판단).
        is_nickname_searchable = user.is_nickname_searchable
        if command.is_nickname_searchable is not UNSET:
            is_nickname_searchable = command.is_nickname_searchable
            self._repository.update_searchable(user.id, is_nickname_searchable)

        memberships = active_memberships(self._repository.list_memberships(user.id))
        # 저장한 값을 다시 읽지 않는다 — 같은 요청 안이라 결과가 같고 왕복만 는다.
        return build_me_result(
            replace(
                user, nickname=nickname, is_nickname_searchable=is_nickname_searchable
            ),
            memberships,
        )
