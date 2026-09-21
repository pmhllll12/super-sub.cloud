"""업로드 클립의 규격 규칙. **HTTP도 DB도 없다.**

SFR-001 이 요구하는 것은 "규격에 맞지 않으면 반려하고 **사유를 남긴다**" 이다.
그래서 이 모듈은 참/거짓이 아니라 **사유 문장**을 돌려준다 — 그 문장이 그대로
`video_validation.reject_reason` 에 들어간다.

상한값은 2026-09-03 에 정했다.

| 항목 | 값 | 왜 |
|---|---|---|
| 용량 | 200MB | 사전 서명 URL 은 크기를 강제하지 못한다. 올라온 뒤 실측으로 건다 |
| 길이 | 60초 | 한 동작을 담기에 충분하다 |
| 해상도 | **상한 없음** (2026-09-19 정정 — 아래 참고) | |

🔴 **정정 (2026-09-19, 박민호 결정 — `jin` 43번)**: 해상도 상한 자체를 없앴다.
미결 `jin` 43번의 실측이 이미 보였듯, 메모리 가드가 `ho` 9번에서 장수(300)가
아니라 **바이트**로 옮겨진 뒤로는 해상도가 커질수록 분석 프레임 수가 스스로
줄어 예산을 지킨다 — 그래서 여기서 **긴 변·짧은 변을 따로 재는 것 자체가
더는 막을 이유가 없는 관문**이었다. DCI 4K 세로(2160×4096) 영상이 이 관문
하나 때문에 반려된 것을 사용자가 직접 겪고서 결정했다.

🔴 **바이트 예산(`DEFAULT_MAX_FRAME_BYTES`, `agent/`)은 건드리지 않았다** —
그건 4K 클립의 분석 프레임 수를 늘려 **결과를 바꾸는** 별개의 판단이고,
이번 결정은 "몇 프레임을 볼지"가 아니라 "몇 화소까지 받을지"에만 해당한다.
해상도가 아주 크면 보는 시간이 짧아질 수 있지만(예산이 그만큼만 프레임을
내주므로), 그건 이미 `ho` 9번이 `limited_by`로 구분해 처리해 둔 축이다 —
거부하지 않고 그만큼만 본 것으로 처리된다.

🔴 **곁가지로 더 흔한 버그 하나를 같이 잡았었다(2026-09-11)**: 옛 상한은
`width`·`height` 를 그대로 비교했다(`width > 1920 or height > 1080`).
**세로로 찍은 보통 1080p 영상(1080×1920, 스마트폰 기본 방향)조차
`height=1920 > 1080` 에 걸려 반려됐다** — 화질과 무관하게 방향만으로 막히고
있었다. 상한 자체를 없앤 지금은 이 버그가 재발할 자리도 없다.

🔴 **길이 상한과 에이전트의 프레임 상한이 아직 안 맞는다.**
`agent/src/supersub_agent/pose.py` 의
`max_frames=300` 은 `target_fps=15` 기준 **20초분**이라, 60초 클립을 올리면
에이전트는 앞 20초만 본다. 여기서 혼자 20초로 낮추지 않는 이유는 상한이 남의
영역(`agent/`)의 제약과 맞물려 있어서다 — 미결 항목으로 올렸다.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

# 사전 서명 URL 을 내주기 전에 거르는 값. 실제 크기는 올라온 뒤 다시 잰다.
MAX_BYTES = 200 * 1024 * 1024
MAX_DURATION_MS = 60_000
# 🔴 해상도 상한은 없다(2026-09-19 결정, 위 모듈 docstring 참고) — 메모리
# 예산은 agent/ 쪽 바이트 가드가 해상도와 무관하게 스스로 지킨다.

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


#: 슬러그에 남기는 문자 — 유니코드 글자·숫자·`_`(한글 음절·자모·한자 포함)와
#: `-`. 나머지(공백·문장부호·이모지 등)는 `-` 로 접는다.
_SLUG_STRIP = re.compile(r"[^\w-]+", re.UNICODE)


def _slug(text: str, max_len: int) -> str:
    """콘솔에서 알아볼 수 있는 조각으로 줄인다. 비면 빈 문자열."""
    s = _SLUG_STRIP.sub("-", (text or "").strip()).strip("-")
    return s[:max_len].strip("-")


def build_storage_key(
    user_id: UUID,
    extension: str,
    *,
    nickname: str = "",
    original_filename: str = "",
    now: datetime | None = None,
) -> str:
    """객체 저장소의 키. 미결 `jin` 24번 — 사람이 알아볼 수 있게 짓는다.

    `videos/<user_id>/<닉네임>-<원본이름>-<YYYYMMDD-HHMM>-<8자>.<확장자>`

    🔴 **`<user_id>/` 접두사는 그대로 둔다.** 등록할 때 이 접두사를 대조해
    남이 올린 객체의 키를 자기 영상으로 등록하는 것을 막고(`owns_key`), 닉네임이
    바뀌어도 이 UUID 로 주인을 되짚는다. 닉네임 조각은 **업로드 시점 라벨**이라
    rename 해도 옛 키는 안 바뀐다.

    `<8자>` 는 무작위다 — 같은 사람이 같은 이름·같은 분에 두 번 올려도 안 겹치게
    하는 것이라 `video_id` 일 필요는 없다(그 시점엔 아직 없다).
    """
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M")
    stem = original_filename.rsplit(".", 1)[0] if original_filename else ""
    parts = [
        _slug(nickname, 20) or "user",
        _slug(stem, 40) or "clip",
        stamp,
        uuid4().hex[:8],
    ]
    return f"{_KEY_PREFIX}/{user_id}/{'-'.join(parts)}.{extension}"


def owns_key(user_id: UUID, storage_key: str) -> bool:
    """이 키가 이 사람에게 내준 것인가."""
    return storage_key.startswith(f"{_KEY_PREFIX}/{user_id}/")


_REPORT_PREFIX = "reports"


def is_provisional_key(storage_key: str) -> bool:
    """아직 `videos/` 에 있는 임시 원본인가. 프로필에 저장되면 `reports/` 로
    옮겨지므로(미결 `jin` 24번), 이미 옮겨진 것에 `keep` 을 다시 불러도 안전하게
    아무것도 안 하도록 가른다.
    """
    return storage_key.startswith(f"{_KEY_PREFIX}/")


def report_source_key(user_id: UUID, video_id: UUID, current_key: str) -> str:
    """"프로필에 저장"된 원본이 갈 자리 — 리포트 산출물과 같은 폴더.

    `reports/<user_id>/<video_id>/source.<ext>`. 정상호의 리포트 키 레이아웃
    (`reports/<user_id>/<video_id>/report.json` 옆)과 한 자리다. 파일명이
    `source` 로 고정이라 폴더만 알면 되짚을 수 있다 — 확장자는 원본에서 딴다.
    """
    ext = current_key.rsplit(".", 1)[-1] if "." in current_key else "mp4"
    return f"{_REPORT_PREFIX}/{user_id}/{video_id}/source.{ext}"


def reject_reason(
    *, duration_ms: int, width: int, height: int, size_bytes: int, analyze: bool = True
) -> str | None:
    """규격 위반 사유. 맞으면 None.

    **첫 위반 하나만 돌려준다.** 사유를 모아 붙이면 문장이 길어져 화면
    (`/videos` 의 반려 사유 바텀시트)에서 읽히지 않고, 사람이 고칠 때는
    어차피 하나씩 고친다.

    🔴 **해상도는 안 본다**(2026-09-19 결정, 위 모듈 docstring 참고) — `width`·
    `height`는 기록용으로만 받는다. `analyze`는 여전히 받아 두는데, 해상도가
    아닌 값(용량·길이)에는 지금도 그대로 적용되기 때문이다.
    """
    if size_bytes > MAX_BYTES:
        return f"용량이 상한을 넘습니다: {size_bytes // (1024 * 1024)}MB (상한 {MAX_BYTES // (1024 * 1024)}MB)"
    if duration_ms > MAX_DURATION_MS:
        return f"길이가 상한을 넘습니다: {duration_ms / 1000:.1f}초 (상한 {MAX_DURATION_MS // 1000}초)"
    return None
