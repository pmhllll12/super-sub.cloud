from abc import ABC, abstractmethod
from uuid import UUID


class PosterCachePort(ABC):
    """떠 둔 장면을 **다시 안 뜨게** 보관한다.

    🔴 **이 포트가 설계의 값을 만든다.** 뜨는 일 자체는 원본을 읽어야 해서
    여전히 비싸고, 한 번만 하도록 만드는 것이 전부다.

    🔴 **영구 저장이 아니다.** 구현은 컨테이너 안의 임시 폴더라 재배포하면
    비고, 그때 처음 부르는 사람이 다시 만든다 — 그래도 맞다고 본 까닭은
    [GetVideoPosterInteractor] 머리말에 있다(DB 는 마이그레이션, S3 는 IAM 이
    걸려 이 작업 범위 밖이다).
    """

    @abstractmethod
    def get(self, video_id: UUID) -> bytes | None:
        """보관된 JPEG. **없으면 None.**"""

    @abstractmethod
    def put(self, video_id: UUID, jpeg: bytes) -> None:
        """보관한다. 🔴 **실패해도 조용히 넘긴다** — 캐시를 못 쓰는 것은
        느려질 뿐이지 요청이 실패할 까닭은 아니다."""
