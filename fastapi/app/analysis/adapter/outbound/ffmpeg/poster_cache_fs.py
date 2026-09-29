"""떠 둔 장면을 컨테이너 안 임시 폴더에 둔다."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from uuid import UUID

from app.analysis.application.ports.output.poster_cache_port import PosterCachePort

logger = logging.getLogger(__name__)

#: 기본 자리. 🔴 **`/app` 아래가 아니다** — 이미지는 비루트(`supersub`)로 돌고
#: 앱 폴더는 읽기 위주다. 임시 폴더가 쓰기가 되는 것이 확실하다.
DEFAULT_DIR = Path(tempfile.gettempdir()) / "supersub-posters"


class FsPosterCache(PosterCachePort):
    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or Path(
            os.environ.get("POSTER_CACHE_DIR", str(DEFAULT_DIR))
        )

    def _path(self, video_id: UUID) -> Path:
        # 🔴 **UUID 를 글자로 다시 만들어 쓴다** — 받은 문자열을 그대로 이어
        #    붙이면 경로 조작이 된다. `UUID` 로 파싱된 값이라 안전하다.
        return self._dir / f"{video_id}.jpg"

    def get(self, video_id: UUID) -> bytes | None:
        try:
            return self._path(video_id).read_bytes()
        except OSError:
            return None

    def put(self, video_id: UUID, jpeg: bytes) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            # 🔴 **임시 이름으로 쓰고 옮긴다.** 그냥 쓰면 두 요청이 같은 파일을
            #    동시에 쓰다가 **반쪽짜리 JPEG** 를 읽는 쪽이 생긴다.
            tmp = self._path(video_id).with_suffix(f".{os.getpid()}.part")
            tmp.write_bytes(jpeg)
            tmp.replace(self._path(video_id))
        except OSError:
            # 캐시를 못 쓰면 느려질 뿐이다 — 요청을 실패시키지 않는다.
            logger.warning("event=poster_cache_write_failed video_id=%s", video_id)
