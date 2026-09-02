"""S3 입출력 — 원본 영상을 받아오고 분석 산출물을 되돌려 놓는다.

boto3는 **선택 의존성**이다(`uv sync --extra aws`). 로컬 WSL 개발은 S3를 쓰지
않으므로 기본 설치에 넣지 않고, import도 함수 안에서 한다 — 이 모듈을 import한
것만으로 boto3가 없다고 실패하면 안 된다.

자격증명은 코드가 들고 있지 않다. EC2에서는 인스턴스 프로파일(IAM 역할)이,
로컬에서는 `aws configure`가 남긴 것을 boto3가 알아서 찾는다. **키를 인자로
받는 함수를 만들지 않는다** — 그러면 어딘가에 적어 두게 된다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

S3_SCHEME = "s3"


def is_s3_uri(value: str) -> bool:
    return str(value).startswith(f"{S3_SCHEME}://")


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """s3://버킷/키 → (버킷, 키).

    키가 비면 거부한다. 빈 키로 download를 부르면 버킷 전체를 가리키는 셈인데
    boto3는 그걸 알아보기 어려운 오류로 돌려준다.
    """
    parsed = urlparse(str(uri))
    if parsed.scheme != S3_SCHEME or not parsed.netloc:
        raise ValueError(f"s3://버킷/키 형식이 아니다: {uri!r}")
    key = parsed.path.lstrip("/")
    if not key:
        raise ValueError(f"객체 키가 없다: {uri!r}")
    return parsed.netloc, key


def _client(region: str | None = None):
    try:
        import boto3
    except ModuleNotFoundError as exc:  # pragma: no cover - 설치 안내 경로
        raise RuntimeError(
            "boto3가 없다. `uv sync --extra aws`로 설치할 것."
        ) from exc
    return boto3.client("s3", region_name=region) if region else boto3.client("s3")


def download(uri: str, dest: Path, region: str | None = None) -> Path:
    """S3 객체를 dest로 내려받는다. dest의 상위 디렉터리는 만들어 준다."""
    bucket, key = parse_s3_uri(uri)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _client(region).download_file(bucket, key, str(dest))
    return dest


def upload_file(path: Path, uri: str, region: str | None = None) -> str:
    """로컬 파일을 S3에 올리고 s3:// URI를 돌려준다."""
    bucket, key = parse_s3_uri(uri)
    _client(region).upload_file(str(path), bucket, key)
    return uri


def upload_json(payload: Any, uri: str, region: str | None = None) -> str:
    """dict를 UTF-8 JSON으로 올린다.

    ensure_ascii=False로 두는 것은 근거 문장이 한글이라서다 — 이스케이프된
    채로 S3에 쌓이면 콘솔에서 그대로 읽을 수 없다.
    """
    bucket, key = parse_s3_uri(uri)
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    _client(region).put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json; charset=utf-8",
    )
    return uri


def join_uri(prefix: str, *parts: str) -> str:
    """s3:// 접두사에 경로 조각을 붙인다. 슬래시 중복·누락을 막는다."""
    base = str(prefix).rstrip("/")
    for part in parts:
        base = f"{base}/{str(part).strip('/')}"
    return base
