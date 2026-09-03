"""객체 저장소 출력 포트.

저장소는 S3 로 정했다(2026-09-03). **포트를 두는 이유는 갈아끼우기 위해서가
아니라 검사하기 위해서다** — 계약 테스트가 실제 S3 없이 돌아야 한다.

키를 어떻게 짓는지는 여기 없다. 그것은 저장소가 아니라 **우리가 정한 규칙**이라
`domain/rules/video_rules.py` 에 있다(`build_storage_key`·`owns_key`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class StoragePort(ABC):
    @abstractmethod
    def create_upload_url(self, storage_key: str, content_type: str) -> tuple[str, int]:
        """그 키에 **올릴 수 있는** URL 과 유효 시간(초)을 만든다.

        🔴 **이 URL 은 용량 상한을 강제하지 못한다.** 사전 서명 PUT 은 크기를
        조건으로 걸 수 없어서, 상한은 올라온 뒤 `size_of` 로 실측해서 건다.
        """

    @abstractmethod
    def size_of(self, storage_key: str) -> int | None:
        """올라온 객체의 크기(바이트). **없으면 None** — 아직 안 올렸다는 뜻이다."""
