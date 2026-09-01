"""`sport` · `position` 을 실제 PostgreSQL 로 확인한다. 부록 D 도메인 ①.

**제약은 "적혀 있는지"가 아니라 "막는지"로 본다.** `sport_code` 는 그동안 문자열이라
오타가 그대로 새 종목이 됐다 — 외래키가 실제로 거부하는지 여기서 확인한다.

`position` 의 복합 유일 제약도 마찬가지다. 부록 D.7 이 그렇게 정한 **이유**(약칭이
종목 간 겹친다)가 지켜지는지, 즉 **다른 종목의 같은 약칭은 통과하는지**까지 본다.
막는 것만 검사하면 너무 세게 막아도 통과한다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.card.adapter.outbound.orm.title_definition_orm import TitleDefinitionOrm
from app.user.adapter.outbound.orm.position_orm import PositionOrm
from app.user.adapter.outbound.orm.sport_orm import SportOrm

pytestmark = pytest.mark.db

UNKNOWN = "quidditch"  # sport 에 없는 종목


class TestSportRows:
    def test_루브릭의_세_종목이_들어_있다(self, db_session):
        """`agent/rubrics/` 에 루브릭이 있는 종목만 분석할 수 있다."""
        codes = {s.code for s in db_session.query(SportOrm).all()}
        assert {"football", "baseball", "basketball"} <= codes

    def test_옛_표기는_남아_있지_않다(self, db_session):
        """08-28 팀 병합에서 축소된 표기다. 마이그레이션이 데이터를 옮겼다."""
        assert db_session.get(SportOrm, "futsal") is None

        left = [
            t.code
            for t in db_session.query(TitleDefinitionOrm).all()
            if t.sport_code == "futsal"
        ]
        assert not left, f"title_definition 에 옛 표기가 남았다: {left}"


class TestSportForeignKeys:
    """부록 D.3 이 지정한 외래키 둘. 지정하지 않은 곳은 걸지 않았다."""

    def test_없는_종목의_영상은_거부된다(self, db_session):
        db_session.add(
            VideoOrm(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                sport_code=UNKNOWN,
                storage_key="videos/x.mp4",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_없는_종목의_호칭_정의는_거부된다(self, db_session):
        db_session.add(
            TitleDefinitionOrm(
                code=f"t-{uuid.uuid4().hex[:8]}",
                label="없는 종목",
                category="강점",
                sport_code=UNKNOWN,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_team_에는_외래키를_걸지_않았다(self, db_session):
        """🔴 **부록 D.3 의 외래키 표에 `team.sport_code` 가 없다.**

        문서에 없는 제약을 임의로 늘리지 않기로 한 것이므로, 그 판단이 바뀌면
        이 검사가 먼저 깨져서 알려 준다. 없는 종목이 들어가도 DB 는 막지 않는다.
        """
        from sqlalchemy import inspect

        fks = inspect(db_session.get_bind()).get_foreign_keys("team")
        targets = {fk["referred_table"] for fk in fks}
        assert "sport" not in targets

    def test_metric_definition_에도_아직_걸지_않았다(self, db_session):
        """계약 문서 3-1절이 미결이다 — A 안이면 `sport_code` 컬럼 자체가 사라진다.

        합의가 끝나 외래키를 걸거나 컬럼을 지우는 시점에 이 검사를 함께 고친다.
        """
        from sqlalchemy import inspect

        fks = inspect(db_session.get_bind()).get_foreign_keys("metric_definition")
        targets = {fk["referred_table"] for fk in fks}
        assert "sport" not in targets


class TestPositionUniqueness:
    @pytest.fixture
    def cleanup(self, db_session):
        made: list[uuid.UUID] = []
        yield made
        db_session.rollback()
        for pid in made:
            row = db_session.get(PositionOrm, pid)
            if row is not None:
                db_session.delete(row)
        db_session.commit()

    def test_같은_종목_안에서는_약칭이_유일하다(self, db_session, cleanup):
        code = f"P{uuid.uuid4().hex[:6]}"
        first = PositionOrm(
            id=uuid.uuid4(), sport_code="football", code=code, label="공격수"
        )
        db_session.add(first)
        db_session.commit()
        cleanup.append(first.id)

        db_session.add(
            PositionOrm(
                id=uuid.uuid4(), sport_code="football", code=code, label="중복"
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_종목이_다르면_같은_약칭이_공존한다(self, db_session, cleanup):
        """🔴 **부록 D.7 이 복합 유일을 고른 이유가 이것이다.**

        축구의 `FW` 와 농구의 `FW` 는 다른 것이라 하나로 합쳐지면 안 된다.
        (지표는 정반대다 — 같은 물리량이 종목마다 나뉘면 비교가 불가능해진다.)
        """
        code = f"P{uuid.uuid4().hex[:6]}"
        for sport, label in (("football", "공격수"), ("basketball", "포워드")):
            row = PositionOrm(
                id=uuid.uuid4(), sport_code=sport, code=code, label=label
            )
            db_session.add(row)
            db_session.commit()
            cleanup.append(row.id)

        same = (
            db_session.query(PositionOrm).filter(PositionOrm.code == code).all()
        )
        assert {p.sport_code for p in same} == {"football", "basketball"}

    def test_없는_종목의_포지션은_거부된다(self, db_session):
        db_session.add(
            PositionOrm(
                id=uuid.uuid4(), sport_code=UNKNOWN, code="XX", label="없는 종목"
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()
