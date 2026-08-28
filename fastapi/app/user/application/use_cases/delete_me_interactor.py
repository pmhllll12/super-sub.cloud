"""탈퇴 인터랙터. 5장 SEC-006.

계정을 지우면 **파생 데이터가 외래키 연쇄로 함께 지워진다**(부록 D.6) — 자격증명,
외부 신원, 카드, 호칭, 소속, 그리고 영상 → 분석 작업 → 지표 → 리포트 체인.

⚠️ **저장소의 객체는 아직 지우지 않는다.** SEC-006 은 DB 행뿐 아니라 원본·썸네일·
추출 프레임까지 요구하는데, 객체 저장소가 정해지지 않았다(5장 ASM-003). 그래서 이
구현은 SEC-006 을 **절반만** 만족한다 — 저장소가 붙는 시점에 여기서 지우는 호출이
하나 더 붙어야 한다.

비밀번호 확인을 요구하는 기준은 **계정에 비밀번호가 있는지**다. 구글로만 가입한
계정에는 확인할 비밀번호가 없어서, 요구하면 탈퇴할 방법이 사라진다.
"""

from __future__ import annotations

from app.core.errors import ApiError
from app.core.logging import log_auth_event
from app.user.application.dtos.me_dto import DeleteMeCommand
from app.user.application.ports.input.delete_me_use_case import DeleteMeUseCase
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.value_objects.password_vo import Password


class DeleteMeInteractor(DeleteMeUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: DeleteMeCommand) -> None:
        user = self._repository.get(command.user_id)
        if user is None:
            raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")

        if self._repository.has_password(user.id):
            # 토큰만으로 지울 수 있으면 **토큰을 훔친 쪽이 계정을 없앨 수 있다.**
            # 되돌릴 수 없는 동작이라 비밀번호 변경보다 더 엄격해야 한다.
            if command.password is None:
                raise ApiError(
                    422, "PASSWORD_REQUIRED", "탈퇴하려면 비밀번호가 필요합니다."
                )
            verified = self._repository.find_by_credentials(
                user.email, Password(command.password)
            )
            if verified is None:
                raise ApiError(
                    401, "INVALID_CREDENTIALS", "비밀번호가 올바르지 않습니다."
                )

        # 지우기 전에 남긴다 — 지운 뒤에는 무엇을 지웠는지 물어볼 데가 없다(SEC-010).
        log_auth_event("account_deleted", user_id=user.id)
        self._repository.delete(user.id)
