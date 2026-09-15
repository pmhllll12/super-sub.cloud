"""고정 선수 참조 데이터. 부록 D 도메인 ②. `paik` 29번."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReferencePlayerEntity:
    """비교 화면이 보여주는 데모 선수 1명.

    **영상 파일 자체는 안 갖는다** — S3에 원본이 없다(EC2 역할이 `videos/`
    접두사에 쓰기 권한이 없다). 화면은 계속 정적 파일(`www/public/compare/`)
    로 재생하고, 이 엔티티는 그 선수의 **분석 리포트가 있는 S3 키**만 안다.
    """

    id: str
    name: str
    report_key: str
