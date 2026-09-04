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


# 분석 대상으로 인정할 확장자.
#
# 🔴 **확장자로 거른다.** S3에는 폴더가 없고 `videos/<UUID>/`도 그냥 키 접두사다.
# 접두사 아래의 **모든** 객체를 영상으로 보면 사이드카 JSON·썸네일·0바이트
# 폴더 표식까지 분석에 넘기게 된다. 실제로 `videos/` 자체가 0바이트 객체로
# 존재한다(콘솔이 폴더를 만들 때 남긴 것).
VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv")


def list_objects(uri: str, region: str | None = None) -> list[tuple[str, int]]:
    """접두사 아래 객체를 (키, 크기)로 모두 돌려준다. 페이지를 이어 붙인다.

    `list_objects_v2`는 한 번에 1000개까지만 준다 — 페이지네이터를 쓰지 않으면
    1001번째부터 **조용히 빠진다.** 지금은 6개뿐이지만 그 조용함이 문제다.
    """
    bucket, key = _split_prefix(uri)
    out: list[tuple[str, int]] = []
    paginator = _client(region).get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=key):
        for item in page.get("Contents", []):
            out.append((item["Key"], int(item.get("Size", 0))))
    return out


def _split_prefix(uri: str) -> tuple[str, str]:
    """s3://버킷/접두사 → (버킷, 접두사). **빈 접두사를 허용한다.**

    `parse_s3_uri`는 빈 키를 거부한다 — 객체 하나를 가리키는 자리에서 버킷
    전체를 뜻하게 되면 알아보기 어려운 오류가 나기 때문이다. 목록 조회는
    반대로 접두사가 비어도 뜻이 분명하므로(버킷 전체) 별도 함수를 둔다.
    """
    parsed = urlparse(str(uri))
    if parsed.scheme != S3_SCHEME or not parsed.netloc:
        raise ValueError(f"s3://버킷/접두사 형식이 아니다: {uri!r}")
    return parsed.netloc, parsed.path.lstrip("/")


def find_videos(uri: str, region: str | None = None) -> list[str]:
    """접두사 아래의 **영상 객체**만 s3:// URI로 돌려준다 (키 순서).

    프론트가 `videos/<UUID>/<파일>.mp4`로 올리므로 "폴더를 줬는데 아무것도
    안 돈다"가 이 함수가 없어서 생기는 증상이다 — S3에 폴더는 없고, 접두사
    아래를 훑어야 그 안의 영상이 보인다.

    0바이트 객체는 뺀다. 업로드가 중간에 끊기면 그런 것이 남고, 그걸
    내려받아 분석하면 "프레임을 읽지 못했습니다"로 죽는다.
    """
    bucket, _ = _split_prefix(uri)
    return [
        f"{S3_SCHEME}://{bucket}/{key}"
        for key, size in list_objects(uri, region)
        if size > 0 and key.lower().endswith(VIDEO_SUFFIXES)
    ]


def object_exists(uri: str, region: str | None = None) -> bool:
    """그 접두사 아래에 객체가 하나라도 있는가. 리포트 유무 판정에 쓴다."""
    return bool(list_objects(uri, region))


def join_uri(prefix: str, *parts: str) -> str:
    """s3:// 접두사에 경로 조각을 붙인다. 슬래시 중복·누락을 막는다."""
    base = str(prefix).rstrip("/")
    for part in parts:
        base = f"{base}/{str(part).strip('/')}"
    return base
