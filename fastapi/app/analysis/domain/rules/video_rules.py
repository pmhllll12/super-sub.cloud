"""업로드 클립의 규격 규칙. **HTTP도 DB도 없다.**

SFR-001 이 요구하는 것은 "규격에 맞지 않으면 반려하고 **사유를 남긴다**" 이다.
그래서 이 모듈은 참/거짓이 아니라 **사유 문장**을 돌려준다 — 그 문장이 그대로
`video_validation.reject_reason` 에 들어간다.

상한값은 2026-09-03 에 정했다.

| 항목 | 값 | 왜 |
|---|---|---|
| 용량 | 200MB | 사전 서명 URL 은 크기를 강제하지 못한다. 올라온 뒤 실측으로 건다 |
| 길이 | 60초 | 한 동작을 담기에 충분하다 |
| 해상도 | 1920x1080 | 4K 는 host RAM 이 먼저 터진다(미결 `ho` 9번, 실측) |

🔴 **길이 상한과 에이전트의 프레임 상한이 아직 안 맞는다.**
`agent/src/supersub_agent/pose.py` 의
`max_frames=300` 은 `target_fps=15` 기준 **20초분**이라, 60초 클립을 올리면
에이전트는 앞 20초만 본다. 여기서 혼자 20초로 낮추지 않는 이유는 상한이 남의
영역(`agent/`)의 제약과 맞물려 있어서다 — 미결 항목으로 올렸다.
"""

from __future__ import annotations

from uuid import UUID, uuid4

# 사전 서명 URL 을 내주기 전에 거르는 값. 실제 크기는 올라온 뒤 다시 잰다.
MAX_BYTES = 200 * 1024 * 1024
MAX_DURATION_MS = 60_000
MAX_WIDTH = 1920
MAX_HEIGHT = 1080

# 받아들이는 형식과 저장 키에 붙일 확장자. **화이트리스트다** — 목록에 없으면
# 거부한다. 모르는 형식을 통과시키면 에이전트가 디코딩에서 실패하고, 그 실패는
# 업로드한 사람에게 이유가 안 보이는 자리에서 난다.
CONTENT_TYPES = {
    "video/mp4": "mp4",
    "video/quicktime": "mov",
}

_KEY_PREFIX = "videos"


def extension_for(content_type: str) -> str | None:
    """저장 키에 붙일 확장자. 받지 않는 형식이면 None."""
    return CONTENT_TYPES.get(content_type)


def build_storage_key(user_id: UUID, extension: str) -> str:
    """객체 저장소의 키. `videos/<업로더>/<uuid>.<확장자>`.

    **업로더를 키에 넣는 것이 검사 수단이다.** 등록할 때 이 접두사를 대조하면
    남이 올린 객체의 키를 자기 영상으로 등록하는 것을 막을 수 있다
    (`owns_key`). 날짜로 나누면 그 대조를 할 수 없다.
    """
    return f"{_KEY_PREFIX}/{user_id}/{uuid4()}.{extension}"


def owns_key(user_id: UUID, storage_key: str) -> bool:
    """이 키가 이 사람에게 내준 것인가."""
    return storage_key.startswith(f"{_KEY_PREFIX}/{user_id}/")


def reject_reason(
    *, duration_ms: int, width: int, height: int, size_bytes: int
) -> str | None:
    """규격 위반 사유. 맞으면 None.

    **첫 위반 하나만 돌려준다.** 사유를 모아 붙이면 문장이 길어져 화면
    (`/videos` 의 반려 사유 바텀시트)에서 읽히지 않고, 사람이 고칠 때는
    어차피 하나씩 고친다.
    """
    if size_bytes > MAX_BYTES:
        return f"용량이 상한을 넘습니다: {size_bytes // (1024 * 1024)}MB (상한 {MAX_BYTES // (1024 * 1024)}MB)"
    if duration_ms > MAX_DURATION_MS:
        return f"길이가 상한을 넘습니다: {duration_ms / 1000:.1f}초 (상한 {MAX_DURATION_MS // 1000}초)"
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        return f"해상도가 상한을 넘습니다: {width}x{height} (상한 {MAX_WIDTH}x{MAX_HEIGHT})"
    return None
