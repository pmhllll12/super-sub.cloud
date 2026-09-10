"""출력 포트 — 용병 매칭 프로필·검색.

`UserPort`에 얹지 않은 이유: 저 포트는 이미 크고, 이 기능은 인증·소속과 무관한
별개 수명주기(검색용 프로필)라 갈라 둬야 스텁·PG 구현이 각자 더 짧게 읽힌다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.user.domain.entities.candidate_entity import CandidateEntity
from app.user.domain.entities.mercenary_profile_entity import MercenaryProfileEntity


class MercenaryPort(ABC):
    @abstractmethod
    def get_profile(self, user_id: UUID) -> MercenaryProfileEntity:
        """없어도 빈 프로필(전부 기본값)을 돌려준다 — 아직 아무도 안 채운 정상 상태다."""

    @abstractmethod
    def save_profile(self, profile: MercenaryProfileEntity) -> None:
        """전체 갈아끼우기(upsert). 부분 수정은 유스케이스가 기존 값과 병합해 넘긴다."""

    @abstractmethod
    def search_candidates(
        self,
        *,
        sport_code: str,
        position_code: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[CandidateEntity]:
        """`is_searchable = true`이고 `position_code`를 원하는 사람만, 임베딩
        코사인 유사도 순으로 최대 `limit`명.

        `sport_code`는 지금 `user`에 저장하지 않는다 — `position_code`가 이미
        종목 안에서만 뜻을 갖는 코드라(예: 축구 GK ≠ 야구 C) 포지션 필터만으로
        종목까지 같이 걸러진다. 인자로 남긴 것은 저장소 구현이 나중에
        `position` 테이블과 조인해 검증하고 싶을 때를 위해서다.
        """
