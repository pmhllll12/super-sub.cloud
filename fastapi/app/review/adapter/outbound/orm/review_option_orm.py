"""`review_option` 테이블. 부록 D 도메인 ⑤ — 평가 선택지 정의.

**대리키를 쓰지 않는다.** `position`(도메인 ③)은 같은 코드가 종목 간 겹칠 수 있어
(야구 `C` = 포수, 농구 `C` = 센터) 대리키 + `(sport_code, code)` 유일 제약을 썼지만,
평가 선택지는 범위가 나뉘지 않아 그런 충돌이 없다 — ERD 가 정한 대로 `code` 를
그대로 기본키로 쓴다.

값은 마이그레이션(`20260903_review_trust_tables`)이 넣는다. **초기 9개가 곧 평가
화면의 내용 전부다.**

🔴 **노출 순서를 담을 컬럼이 없다.** 마이그레이션 docstring 이 "순서가 화면 노출
순서다"라고 적었지만 SQL 은 `ORDER BY` 없이 순서를 보장하지 않는다 — 실제로 `label`
하나를 고치자 그 행이 맨 끝으로 갔다(2026-09-04 확인). 어떻게 할지는 미결 `min`
2번 회신의 (2)번이 답을 기다리고 있다.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReviewOptionOrm(Base):
    __tablename__ = "review_option"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    # manner · skill · repeat · caution. 화면이 이 값으로 묶어 보여 준다.
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
