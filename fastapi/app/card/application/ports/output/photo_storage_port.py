"""카드 사진 저장소 출력 포트 (2026-09-18, 사용자 요청).

🔴 **`analysis` 의 `StoragePort` 를 쓰지 않는다.** 컨텍스트끼리 임포트하지
않는 것이 이 저장소의 규칙이고(`tests/test_architecture.py` 가 실제로 막는다),
그 포트는 영상에 맞춰 커졌다(크기·지문·옮기기·프리픽스 삭제). 사진에 필요한
것은 **올리기·내려받기·지우기 셋**뿐이라 그만큼만 둔다.

🔴 **왜 S3 인가.** `style` JSON 에 data URL 로 담으면 카드를 읽는 **모든**
응답에 사진이 실린다 — 스쿼드 판 하나가 자리마다 카드를 부르므로 5~7장이
매번 함께 나간다. 영상과 같이 브라우저↔S3 직통으로 두면 키만 오가고 이미지는
브라우저가 캐시한다(PER-002 — 「재생도 앱 서버를 지나지 않는다」).

키를 어떻게 짓는지는 여기 없다. 그것은 저장소가 아니라 **우리가 정한 규칙**이라
`domain/rules/card_rules.py` 에 있다(`build_photo_key`·`owns_photo_key`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PhotoStoragePort(ABC):
    @abstractmethod
    def create_upload_url(self, storage_key: str, content_type: str) -> tuple[str, int]:
        """그 키에 **올릴 수 있는** URL 과 유효 시간(초).

        🔴 **`ContentType` 이 서명에 들어간다** — 클라이언트가 같은 값을 헤더로
        보내야 하고, 다르면 S3 가 거절한다. 계약 문서에 적어 둔다.
        🔴 **이 URL 은 용량 상한을 강제하지 못한다.** 사전 서명 PUT 은 크기를
        조건으로 걸 수 없다 — 화면이 올리기 전에 줄인다.
        """

    @abstractmethod
    def create_download_url(self, storage_key: str) -> tuple[str, int]:
        """그 키를 **내려받을 수 있는** URL 과 유효 시간(초).

        키 존재 여부는 확인하지 않는다 — 서명만 만든다(영상과 같다). 아직
        안 올린 키면 브라우저가 403 을 받고, 화면은 사진 없는 카드를 그린다.
        """

    @abstractmethod
    def delete_object(self, storage_key: str) -> None:
        """그 키의 객체를 지운다. 없어도 조용히 지나간다.

        사진을 바꾸거나 뺄 때 **옛 파일을 남기지 않기 위한 것**이다 — 안 지우면
        버킷에 주인 없는 사진이 쌓이고, 키를 아는 사람은 계속 볼 수 있다.
        """
