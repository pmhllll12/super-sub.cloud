"""`sport` 테이블. 부록 D 도메인 ①.

종목 코드의 정본이다. `video` · `title_definition` 이 이 코드를 참조한다(부록 D.3).

**왜 테이블인가.** 종목을 열거형이나 CHECK 로 고정하면 종목이 늘 때마다
마이그레이션이 필요하다. 행으로 두면 데이터만 넣으면 된다 — `metric_definition`
을 컬럼이 아니라 행으로 둔 것과 같은 이유다(부록 D.4).

🔴 **행은 `agent/rubrics/` 를 따른다.** 루브릭이 있는 종목만 분석할 수 있으므로
목록의 실물은 그쪽이다. 2026-09-01 기준 축구·야구·농구 셋이고, 그 전에 쓰던
`futsal` 은 08-28 팀 병합에서 축소되며 사라졌다(이 마이그레이션이 남은 데이터를
`football` 로 옮긴다).

✅ **부록 D 와의 어긋남은 해소됐다 (2026-09-03).** 본문이 "풋살·야구 2행"이었던
것을 박민호가 "축구·야구·농구 3행"으로 고쳤다(미결 `jin` 4번). 여기 적어 두었던
어긋남 기록은 그래서 지웠다 — **닫힌 경로를 열려 있는 것처럼 두면 다음 사람이
같은 조사를 반복한다.**
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SportOrm(Base):
    __tablename__ = "sport"

    # 코드가 곧 식별자다. `title_definition` 처럼 참조되는 정의 테이블이라
    # 대리키를 두지 않는다 — 참조하는 쪽이 코드를 그대로 들고 있다.
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    # 🔴 **지금 새로 받을 수 있는 종목인가** (`ho` 39번, 2026-09-16). 에이전트가
    # 축구 단일 종목으로 정리되면서 야구·농구 루브릭이 사라졌는데, **행을 지울
    # 수는 없다** — 이미 그 종목으로 올라간 영상이 참조하고 있다(2026-09-16
    # 실측 165건). 그래서 지우는 대신 이 칸을 내린다.
    #
    # 읽기·거르기(`GET /positions`·경기 목록·코치 목록)는 **`false` 여도 그대로
    # 돈다** — 과거 데이터를 계속 볼 수 있어야 해서다. 막는 것은 **새로 만드는
    # 자리**(팀 만들기·영상 등록)뿐이다.
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
