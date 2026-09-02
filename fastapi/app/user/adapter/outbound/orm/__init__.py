"""SQLAlchemy ORM 모델.

여기 있는 클래스는 **테이블 모양**이지 도메인이 아니다. 도메인 엔티티는
`domain/entities/` 에 있고, 둘 사이 변환은 `../mappers/` 가 맡는다.

⚠️ 새 모델을 만들면 Alembic 이 아는 metadata 에 **반드시 등록한다.**
등록을 빠뜨리면 `--autogenerate` 가 그 테이블을 "DB 에만 있는 것"으로 보고
`DROP TABLE` 을 만든다.

🔴 **참조만 되고 아무도 임포트하지 않는 모델은 여기서 끌어온다.** `sport` 는
리포지토리가 없어 코드 경로로는 절대 로드되지 않는데, `video`·`title_definition`
이 `ForeignKey("sport.code")` 로 **문자열 참조**한다. 문자열은 같은 metadata 에
대상 테이블이 있어야 해석되므로, 안 끌어오면 런타임에

    NoReferencedTableError: ... could not find table 'sport'

로 죽는다. `alembic/env.py` 의 등록은 마이그레이션 때만 쓰이고 **런타임에는
아무 역할도 하지 않는다.** `tests/test_architecture.py` 의
`TestForeignKeyTargets` 가 이 구멍을 지킨다.
"""

from app.user.adapter.outbound.orm import position_orm as position_orm  # noqa: F401
from app.user.adapter.outbound.orm import sport_orm as sport_orm  # noqa: F401
