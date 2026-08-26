"""`CardPort` 의 PostgreSQL 구현.

🔴 **`user` 컨텍스트를 임포트하지 않는다.**

카드에는 주인 닉네임이 필요한데 그 값은 `user` 테이블에 있다. 그렇다고
`app.user...user_orm` 을 가져오면 컨텍스트 경계가 무너진다
(`tests/test_architecture.py` 가 막는다).

그래서 **모듈이 아니라 컬럼 두 개를 읽는다.** SQLAlchemy 의 경량
`table()`/`column()` 은 metadata 에 등록되지 않는 순수 SQL 조각이라,
"이 테이블을 소유한다"가 아니라 "이 두 컬럼을 읽는다"를 정확히 표현한다.
Alembic 도 이것을 보지 않으므로 카드 쪽에서 `user` 테이블을 만들려 들지 않는다.

⚠️ 대가: `user.nickname` 의 이름이 바뀌면 **여기가 조용히 깨진다.** 파이썬이
잡아 주지 않는다. 그래서 DB 통합 테스트로 고정해 둔다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from app.card.adapter.outbound.mappers.card_mapper import (
    to_card_entity,
    to_title_entity,
)
from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm
from app.card.adapter.outbound.orm.title_definition_orm import TitleDefinitionOrm
from app.card.adapter.outbound.orm.user_title_orm import UserTitleOrm
from app.card.application.ports.output.card_port import CardPort
from app.card.domain.entities.card_entity import CardEntity
from app.card.domain.entities.title_entity import TitleEntity
from app.card.domain.value_objects.public_slug_vo import PublicSlug

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_user = table("user", column("id"), column("nickname"))


class CardPgRepository(CardPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_owner(self, user_id: UUID) -> CardEntity | None:
        return self._load(PlayerCardOrm.user_id == user_id)

    def find_by_slug(self, slug: PublicSlug) -> CardEntity | None:
        return self._load(PlayerCardOrm.public_slug == str(slug))

    def _load(self, where) -> CardEntity | None:
        stmt = (
            select(PlayerCardOrm, _user.c.nickname)
            .join(_user, _user.c.id == PlayerCardOrm.user_id)
            .where(where)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None

        card_row, nickname = row
        return to_card_entity(card_row, nickname, self._titles(card_row.user_id))

    def _titles(self, user_id: UUID) -> list[TitleEntity]:
        """부여된 호칭만 온다 — `user_title` 에 행이 있다는 것이 곧 부여다.

        일부러 **오래된 것부터** 준다. 표시 순서는 도메인 규칙이 뒤집으므로,
        여기서 이미 정렬해 두면 그 규칙이 실제로 도는지 확인되지 않는다.
        """
        stmt = (
            select(UserTitleOrm, TitleDefinitionOrm)
            .join(
                TitleDefinitionOrm,
                TitleDefinitionOrm.code == UserTitleOrm.title_code,
            )
            .where(UserTitleOrm.user_id == user_id)
            .order_by(UserTitleOrm.granted_at.asc())
        )
        return [
            to_title_entity(granted, definition)
            for granted, definition in self._session.execute(stmt).all()
        ]
