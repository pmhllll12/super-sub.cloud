"""카드 조회를 **실제 PostgreSQL** 에 대고 확인한다.

스텁은 응답 형태까지만 답한다. 여기서 보는 것은 스텁이 답할 수 없는 것들이다:

- `player_card` · `user_title` · `title_definition` 세 테이블의 조인이 맞는가
- 🔴 **주인 닉네임이 `user` 테이블에서 제대로 읽히는가** — 카드 저장소는 `user`
  컨텍스트를 임포트하지 않고 `table()`/`column()` 으로 컬럼 두 개만 읽는다.
  컬럼 이름이 바뀌면 **파이썬이 잡아 주지 않으므로** 이 테스트가 유일한 방어선이다.
- 표시 순서를 도메인 규칙이 실제로 뒤집는가 (저장소는 오래된 것부터 준다)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm
from app.card.adapter.outbound.orm.title_definition_orm import TitleDefinitionOrm
from app.card.adapter.outbound.orm.user_title_orm import UserTitleOrm
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _at(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


@pytest.fixture
def card(db_client, db_session):
    """카드까지 갖춘 계정을 하나 만든다. 끝나면 전부 지운다.

    시드된 데모 데이터에 기대지 않는다 — 기대면 테스트가 시드 실행 여부에 묶인다.
    """
    email = f"card-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "카드주인"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])

    slug = f"slug-{uuid.uuid4().hex[:10]}"
    card_id = uuid.uuid4()
    codes = [f"t1-{uuid.uuid4().hex[:6]}", f"t2-{uuid.uuid4().hex[:6]}"]

    db_session.add(
        TitleDefinitionOrm(
            code=codes[0], label="주말 개근", category="활동", sport_code="football"
        )
    )
    db_session.add(
        TitleDefinitionOrm(
            code=codes[1], label="슈팅이 매서운", category="강점", sport_code="football"
        )
    )
    db_session.add(
        PlayerCardOrm(
            id=card_id,
            user_id=user_id,
            public_slug=slug,
            og_image_key=f"cards/{card_id}.png",
        )
    )
    db_session.flush()
    # 오래된 것을 먼저 넣는다. 규칙이 뒤집지 않으면 여기서 잡힌다.
    db_session.add(
        UserTitleOrm(
            id=uuid.uuid4(),
            user_id=user_id,
            title_code=codes[0],
            granted_at=_at(2026, 8, 1, 9, 0),
        )
    )
    db_session.add(
        UserTitleOrm(
            id=uuid.uuid4(),
            user_id=user_id,
            title_code=codes[1],
            granted_at=_at(2026, 8, 20, 12, 0),
        )
    )
    db_session.commit()

    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200

    yield {
        "email": email,
        "slug": slug,
        "card_id": str(card_id),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }

    # user_title -> player_card -> user 순서로 지운다 (외래키 방향의 역순).
    db_session.execute(
        text("delete from user_title where user_id = :u"), {"u": str(user_id)}
    )
    db_session.execute(
        text("delete from player_card where user_id = :u"), {"u": str(user_id)}
    )
    db_session.execute(
        text("delete from title_definition where code = any(:c)"), {"c": codes}
    )
    db_session.execute(text('delete from "user" where email = :e'), {"e": email})
    db_session.commit()


class TestMyCardFromDb:
    def test_DB_의_카드를_돌려준다(self, db_client, card):
        res = db_client.get(f"{V1}/me/card", headers=card["headers"])
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["id"] == card["card_id"]
        assert body["public_slug"] == card["slug"]

    def test_주인_닉네임이_user_테이블에서_읽힌다(self, db_client, card):
        """🔴 카드 저장소는 `user` 를 임포트하지 않고 컬럼만 읽는다.

        컬럼 이름이 바뀌면 파이썬이 못 잡는다 — 여기가 유일한 방어선이다.
        """
        body = db_client.get(f"{V1}/me/card", headers=card["headers"]).json()
        assert body["user"]["nickname"] == "카드주인"

    def test_닉네임을_바꾸면_카드에도_반영된다(self, db_client, card):
        """카드가 닉네임을 **복사해 두지 않고** 조인해서 읽는다는 증거다."""
        db_client.patch(
            f"{V1}/me", json={"nickname": "바뀐주인"}, headers=card["headers"]
        )
        body = db_client.get(f"{V1}/me/card", headers=card["headers"]).json()
        assert body["user"]["nickname"] == "바뀐주인"

    def test_호칭이_최신순으로_나온다(self, db_client, card):
        """저장소는 오래된 것부터 준다. 뒤집는 것은 도메인 규칙의 몫이다."""
        titles = db_client.get(f"{V1}/me/card", headers=card["headers"]).json()["titles"]
        assert [t["label"] for t in titles] == ["슈팅이 매서운", "주말 개근"]

    def test_분류가_열거형_값으로_나온다(self, db_client, card):
        titles = db_client.get(f"{V1}/me/card", headers=card["headers"]).json()["titles"]
        assert {t["category"] for t in titles} == {"강점", "활동"}

    def test_카드가_없는_사용자면_404(self, db_client, db_session):
        email = f"nocard-{uuid.uuid4().hex[:10]}@super-sub.example"
        db_client.post(
            f"{V1}/auth/signup",
            json={"email": email, "password": PASSWORD, "nickname": "카드없음"},
        )
        login = db_client.post(
            f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
        )
        res = db_client.get(
            f"{V1}/me/card",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"

        db_session.execute(text('delete from "user" where email = :e'), {"e": email})
        db_session.commit()


class TestPublicCardFromDb:
    def test_슬러그로_인증_없이_보인다(self, db_client, card):
        res = db_client.get(f"{V1}/cards/{card['slug']}")
        assert res.status_code == 200, res.text
        assert res.json()["public_slug"] == card["slug"]

    def test_내부_id_가_나가지_않는다(self, db_client, card):
        """SFR-009 — 공유 링크는 슬러그로만 접근한다."""
        body = db_client.get(f"{V1}/cards/{card['slug']}").json()
        assert "id" not in body

    def test_수치가_실려_나가지_않는다(self, db_client, card):
        """부록 D.5 — 카드에 수치 능력치를 노출하지 않는다."""
        from app.card.domain.rules.card_rules import FORBIDDEN_CARD_FIELDS

        body = db_client.get(f"{V1}/cards/{card['slug']}").json()
        assert not (set(body) & FORBIDDEN_CARD_FIELDS)

    def test_없는_슬러그면_404(self, db_client):
        res = db_client.get(f"{V1}/cards/no-such-slug-here")
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"
