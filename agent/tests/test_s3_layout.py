"""S3에서 **폴더를 줬을 때** 무엇을 분석하고 어디에 놓는가.

프론트는 `videos/<UUID>/<파일>.mp4` 로 올린다. S3에 폴더는 없고 그건 그냥 키
접두사인데, 그 접두사를 객체인 양 내려받으면 "그런 키 없음"으로 죽는다 —
"폴더를 줬는데 아무것도 안 돈다"가 그 증상이다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from supersub_agent import storage  # noqa: E402
from analyze_s3 import report_slug, resolve_videos  # noqa: E402


# --- 리포트를 어디에 놓는가 -------------------------------------------------


def test_report_slug_keeps_the_upload_folder():
    """🔴 파일 이름만 쓰면 서로 다른 업로드가 같은 자리로 간다.

    `videos/<A>/clip.mp4` 와 `videos/<B>/clip.mp4` 가 둘 다 `reports/clip/`
    으로 가면 타임스탬프로만 갈려서 어느 업로드의 결과인지 못 되짚는다.
    """
    a = report_slug("videos/16a37c31-29e2-40e1-8ca0-4587525f90db/clip.mp4")
    b = report_slug("videos/f6a49f2e-fe04-41e5-a31c-94ddc45e65d2/clip.mp4")

    assert a != b
    assert a == "16a37c31-29e2-40e1-8ca0-4587525f90db/clip"


def test_report_slug_leaves_top_level_uploads_where_they_were():
    """`videos/` 바로 아래 파일은 옛 경로를 지킨다 — 이미 올라간 리포트가
    떠내려가면 안 된다."""
    assert report_slug("videos/baseball_pitch_trim.mp4") == "baseball_pitch_trim"


def test_report_slug_handles_a_bare_key():
    assert report_slug("clip.mp4") == "clip"


# --- 무엇을 분석 대상으로 보는가 --------------------------------------------


def test_a_video_key_is_used_as_is(monkeypatch):
    """객체를 직접 주면 목록 조회를 하지 않는다 — 권한도 왕복도 필요 없다."""
    def boom(*a, **k):
        raise AssertionError("객체를 줬는데 목록을 조회했다")

    monkeypatch.setattr(storage, "find_videos", boom)
    uri = "s3://b/videos/A/clip.mp4"

    assert resolve_videos(uri, None) == [uri]


def test_a_folder_is_expanded_to_the_videos_inside(monkeypatch):
    inside = ["s3://b/videos/A/one.mp4", "s3://b/videos/A/two.mp4"]
    monkeypatch.setattr(storage, "find_videos", lambda *a, **k: inside)

    assert resolve_videos("s3://b/videos/A/", None) == inside


def test_an_empty_folder_says_what_to_check(monkeypatch):
    """🔴 콘솔에 폴더로 보여도 객체가 없을 수 있다 — 업로드가 끊기면 그렇다.

    그때 "그런 키 없음"으로 죽으면 원인을 못 찾는다.
    """
    monkeypatch.setattr(storage, "find_videos", lambda *a, **k: [])

    with pytest.raises(SystemExit, match="영상을 찾지 못했다"):
        resolve_videos("s3://b/videos/A/", None)


# --- 접두사 아래를 훑을 때 무엇을 거르는가 ----------------------------------


def _fake_listing(monkeypatch, items):
    monkeypatch.setattr(storage, "list_objects", lambda *a, **k: items)


def test_find_videos_skips_zero_byte_objects(monkeypatch):
    """`videos/` 자체가 0바이트 객체로 존재한다(콘솔이 폴더를 만들 때 남긴 것).
    내려받아 분석하면 '프레임을 읽지 못했습니다'로 죽는다."""
    _fake_listing(monkeypatch, [("videos/", 0), ("videos/A/clip.mp4", 2023622)])

    assert storage.find_videos("s3://b/videos/") == ["s3://b/videos/A/clip.mp4"]


def test_find_videos_skips_non_video_objects(monkeypatch):
    """사이드카·썸네일까지 분석에 넘기지 않는다.

    대상 지정 박스를 S3로 함께 올리자는 이야기가 미결 18번에 있다 — 그때
    `videos/<UUID>/…json` 이 옆에 놓이므로 이 거르기가 미리 있어야 한다.
    """
    _fake_listing(monkeypatch, [
        ("videos/A/clip.mp4", 100),
        ("videos/A/clip.subject.json", 40),
        ("videos/A/thumb.jpg", 900),
    ])

    assert storage.find_videos("s3://b/videos/") == ["s3://b/videos/A/clip.mp4"]


def test_split_prefix_allows_an_empty_key_unlike_parse_s3_uri():
    """목록 조회는 접두사가 비어도 뜻이 분명하다(버킷 전체).
    객체 하나를 가리키는 parse_s3_uri 는 반대로 거부해야 한다."""
    assert storage._split_prefix("s3://b/") == ("b", "")

    with pytest.raises(ValueError):
        storage.parse_s3_uri("s3://b/")
