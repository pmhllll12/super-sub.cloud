"""용병 매칭 유스케이스 — 스텁만으로(DB 없이) 병합 규칙·검증을 확인한다.

라우터 계약 테스트를 따로 두지 않은 이유: `mercenary_router`는 아직
`app/main.py`에 등록되지 않았다(정어진의 배선 몫, pending `min` 16번). 여기는
그와 무관하게 성립하는 인터랙터 자체의 동작만 본다.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.errors import ApiError
from app.user.adapter.outbound.stub.mercenary_stub_repository import (
    MercenaryStubRepository,
)
from app.user.adapter.outbound.stub.stub_embedding_adapter import StubEmbeddingAdapter
from app.user.application.dtos.mercenary_dto import (
    GetMercenaryProfileQuery,
    SearchCandidatesQuery,
    UpdateMercenaryProfileCommand,
)
from app.user.application.use_cases.get_mercenary_profile_interactor import (
    GetMercenaryProfileInteractor,
)
from app.user.application.use_cases.search_candidates_interactor import (
    SearchCandidatesInteractor,
)
from app.user.application.use_cases.update_mercenary_profile_interactor import (
    UpdateMercenaryProfileInteractor,
)
from app.user.domain.entities.mercenary_profile_entity import AvailableSlot, PositionRef

_GK = PositionRef(sport_code="football", code="GK")
_SLOT = AvailableSlot(day="SAT", start="18:00", end="21:00")


def _update_interactor(repository):
    return UpdateMercenaryProfileInteractor(repository, StubEmbeddingAdapter)


def test_처음_조회하면_빈_프로필이다():
    repo = MercenaryStubRepository()
    user_id = uuid.uuid4()
    result = GetMercenaryProfileInteractor(repo)(GetMercenaryProfileQuery(user_id))
    assert result.preferred_positions == []
    assert result.is_searchable is False


def test_None인_필드는_건드리지_않는다():
    repo = MercenaryStubRepository()
    user_id = uuid.uuid4()
    interactor = _update_interactor(repo)

    interactor(
        UpdateMercenaryProfileCommand(user_id=user_id, location="서울 강남")
    )
    result = interactor(
        UpdateMercenaryProfileCommand(user_id=user_id, skill_summary="공중볼 강함")
    )

    assert result.location == "서울 강남"  # 이번 요청이 안 보냈으니 유지
    assert result.skill_summary == "공중볼 강함"


def test_빈_문자열은_지운다():
    repo = MercenaryStubRepository()
    user_id = uuid.uuid4()
    interactor = _update_interactor(repo)

    interactor(UpdateMercenaryProfileCommand(user_id=user_id, location="서울 강남"))
    result = interactor(UpdateMercenaryProfileCommand(user_id=user_id, location=""))

    assert result.location is None


def test_불완전한_프로필은_검색_노출을_거부한다():
    repo = MercenaryStubRepository()
    user_id = uuid.uuid4()
    interactor = _update_interactor(repo)

    with pytest.raises(ApiError) as exc:
        interactor(
            UpdateMercenaryProfileCommand(user_id=user_id, is_searchable=True)
        )
    assert exc.value.code == "MERCENARY_PROFILE_INCOMPLETE"


def test_다_채우면_검색에_노출된다():
    repo = MercenaryStubRepository()
    user_id = uuid.uuid4()
    interactor = _update_interactor(repo)

    interactor(
        UpdateMercenaryProfileCommand(
            user_id=user_id,
            preferred_positions=[_GK],
            available_slots=[_SLOT],
            skill_summary="공중볼 강함",
            is_searchable=True,
        )
    )

    candidates = SearchCandidatesInteractor(repo, StubEmbeddingAdapter())(
        SearchCandidatesQuery(
            sport_code="football", position_code="GK", query_text="골키퍼 구해요"
        )
    )
    assert [c.user_id for c in candidates] == [user_id]


def test_skill_summary를_안바꾸면_임베딩을_다시_계산하지_않는다():
    """임베딩 호출 횟수를 세는 가짜 임베더로 확인한다."""

    calls: list[str] = []

    class _CountingEmbedder(StubEmbeddingAdapter):
        def embed(self, text, *, purpose):
            calls.append(text)
            return super().embed(text, purpose=purpose)

    repo = MercenaryStubRepository()
    user_id = uuid.uuid4()
    interactor = UpdateMercenaryProfileInteractor(repo, _CountingEmbedder)

    interactor(
        UpdateMercenaryProfileCommand(user_id=user_id, skill_summary="공중볼 강함")
    )
    assert len(calls) == 1

    interactor(UpdateMercenaryProfileCommand(user_id=user_id, location="서울"))
    assert len(calls) == 1  # 소개를 안 건드렸으니 다시 안 부른다


def test_빈_query_text는_422다():
    repo = MercenaryStubRepository()
    interactor = SearchCandidatesInteractor(repo, StubEmbeddingAdapter())
    with pytest.raises(ApiError) as exc:
        interactor(
            SearchCandidatesQuery(sport_code="football", position_code="GK", query_text="  ")
        )
    assert exc.value.code == "VALIDATION_ERROR"
