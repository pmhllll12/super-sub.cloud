"""`Settings` 가 읽는 키와 `.env.example` 템플릿이 어긋나지 않는지 검사한다.

`app/core/config.py` 는 `pydantic-settings` 라 **키 이름이 틀리거나 빠지면 예외
없이 조용히 기본값**(대개 `""`)으로 떨어진다. `S3_BUCKET` 을 `S3_BUCKETNAME` 으로
오타 내면 업로드가 503 이 되는데, 그 503 은 "환경 문제"라 계약 테스트가 안 잡는다.

`fastapi/.env.example` 은 그 파일 스스로 *"이 API 서버가 실제로 읽는 항목"* 이라고
선언한다. 그 선언이 참인지 — 코드가 읽는 것 = 템플릿에 적힌 것 — 을 여기서 고정한다.
2026-09-10 에 실제로 4개(`S3_BUCKET`·`AWS_REGION`·`UPLOAD_URL_TTL_SECONDS`·
`PROVISIONAL_VIDEO_TTL_HOURS`)가 코드에만 있고 템플릿엔 없었다.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.config import Settings

_ENV_EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"

# 일부러 한쪽에만 두는 키 — 이유를 함께 둔다. 이유 없이 늘리면 검사가 무의미해진다.
# `code_only`: `Settings` 에는 있으나 템플릿에서 뺀 키 (배포자에게 안 보여도 되는 것).
# `template_only`: 템플릿에는 있으나 코드가 아직 안 읽는 키 (곧 쓸 예정 등).
_EXEMPT_CODE_ONLY: dict[str, str] = {}
_EXEMPT_TEMPLATE_ONLY: dict[str, str] = {}


def _template_keys() -> set[str]:
    """`.env.example` 의 `KEY=` 줄에서 키 이름만 뽑는다. 주석·빈 줄은 건너뛴다."""
    keys: set[str] = set()
    for line in _ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if m:
            keys.add(m.group(1))
    return keys


def _settings_env_keys() -> set[str]:
    """`Settings` 필드가 읽어들이는 환경변수 이름. 별칭이 없으면 대문자화다.

    `@property`(`dsn`·`google_audiences` 등)는 `model_fields` 에 없어서 자동으로 빠진다.
    """
    keys: set[str] = set()
    for name, field in Settings.model_fields.items():
        alias = getattr(field, "alias", None)
        keys.add((alias or name).upper())
    return keys


def test_템플릿이_비어_있지_않다():
    """정규식이나 파일 경로가 어긋나 0건을 뽑으면 아래 검사가 통과와 구별이 안 된다."""
    assert len(_template_keys()) >= 10


def test_코드가_읽는_키가_전부_템플릿에_있다():
    code = _settings_env_keys()
    template = _template_keys()
    missing = code - template - set(_EXEMPT_CODE_ONLY)
    assert not missing, (
        "`Settings` 가 읽는데 `.env.example` 에 없다 — 배포자가 이 템플릿만 보면 "
        "빠뜨리고, 앱은 조용히 기본값으로 떨어진다:\n  "
        + "\n  ".join(sorted(missing))
        + "\n템플릿에 추가하거나, 배포자에게 안 보여도 되면 `_EXEMPT_CODE_ONLY` 에 이유와 함께 넣을 것."
    )


def test_템플릿의_키를_코드가_전부_읽는다():
    code = _settings_env_keys()
    template = _template_keys()
    extra = template - code - set(_EXEMPT_TEMPLATE_ONLY)
    assert not extra, (
        "`.env.example` 에 있는데 `Settings` 가 안 읽는다 — 필드 이름을 바꾸고 "
        "템플릿의 옛 키를 안 지웠을 수 있다:\n  "
        + "\n  ".join(sorted(extra))
        + "\n템플릿에서 지우거나, 곧 쓸 예정이면 `_EXEMPT_TEMPLATE_ONLY` 에 이유와 함께 넣을 것."
    )


def test_면제_목록이_낡지_않았다():
    """면제해 둔 키가 실제로는 양쪽에 다 있으면(어긋남이 해소됨) 면제를 지워야 한다."""
    code = _settings_env_keys()
    template = _template_keys()
    stale_code = {k for k in _EXEMPT_CODE_ONLY if k in template}
    stale_template = {k for k in _EXEMPT_TEMPLATE_ONLY if k in code}
    assert not (stale_code or stale_template), (
        "면제가 필요 없어졌다 — 해당 항목을 `_EXEMPT_*` 에서 지울 것: "
        f"{sorted(stale_code | stale_template)}"
    )
