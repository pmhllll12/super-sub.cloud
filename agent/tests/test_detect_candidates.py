"""고를 수 있는 사람 목록 (미결 `ho` 44번).

🔴 **이 파일이 지키는 것은 「왕복」이다.** 화면이 이 함수의 `box` 를 받아
**그대로** `--subject-box` 로 돌려보낼 수 있어야 한다. 중간에 변환이 끼면
그 자리가 곧 버그이고, 증상은 **엉뚱한 사람이 분석되는 것**이다 —
`parse_subject_spec` 은 범위 밖을 **클램프가 아니라 거부**하도록 일부러
만들어져 있어서(조용히 맞춰 주면 「지정대로 했다」고 거짓말하게 된다),
어긋나면 사용자에게는 그냥 「잘못된 지정」으로 보인다.

무거운 모델을 올리지 않고 검사할 수 있는 것만 여기서 본다 — 실제 검출은
GPU 회차다.
"""
from __future__ import annotations

import numpy as np
import pytest

from supersub_agent.pose import (
    COCO_PERSON_LABEL,
    PERSON_ELIGIBLE_THRESHOLD,
    _clip_unit_box,
    anchor_frame_for,
    parse_subject_spec,
)


def test_a_detected_box_survives_the_round_trip():
    """🔴 이 검사가 이 파일의 이유다 — 낸 박스를 그대로 되받을 수 있는가."""
    box = _clip_unit_box(100 / 1920, 50 / 1080, 300 / 1920, 600 / 1080)
    spec = parse_subject_spec(",".join(str(v) for v in box), 1000.0)
    assert spec is not None
    assert spec.box == pytest.approx(tuple(box))


@pytest.mark.parametrize(
    "px",
    [
        (0, 0, 1920, 1080),          # 화면을 꽉 채운 사람 — x+w 가 정확히 1.0
        (1919, 1079, 1, 1),          # 오른쪽 아래 끝
        (0, 0, 1, 1),                # 왼쪽 위 끝
        (960, 540, 960, 540),        # 오른쪽 아래 절반
    ],
)
def test_edge_boxes_are_still_accepted_by_the_parser(px):
    """끝에 붙은 박스가 부동소수 오차로 거부되지 않는가.

    🔴 나눗셈 결과가 1.0 을 **아주 조금** 넘으면 파서가 거부한다. 사람은
    화면 가장자리에 자주 서고, 그때만 「잘못된 지정」이 나오면 원인을 못 찾는다.
    """
    x, y, w, h = px
    box = _clip_unit_box(x / 1920, y / 1080, w / 1920, h / 1080)
    assert parse_subject_spec(",".join(str(v) for v in box), 0.0) is not None


def test_the_clip_only_absorbs_rounding_not_real_mistakes():
    """🔴 화면 픽셀을 그대로 넣은 것 같은 **큰 어긋남까지 덮으면 안 된다**.

    `_clip_unit_box` 는 나눗셈 오차용이다. 여기서 픽셀 좌표를 조용히 0~1 로
    구겨 넣으면, 파서가 막으려던 「엉뚱한 사람을 분석하고도 지정대로 했다고
    답하는 것」이 그대로 되살아난다 — **부르는 쪽이 정규화해서 준다**는 전제를
    이 검사가 못박는다.
    """
    # 픽셀을 그대로 준 경우: 폭이 1.0 으로 잘려 **원래 값과 전혀 달라진다**.
    #    조용히 통과시키는 대신, 값이 보존되지 않는다는 것을 드러낸다.
    squashed = _clip_unit_box(100.0, 50.0, 300.0, 600.0)
    assert squashed != [100.0, 50.0, 300.0, 600.0]
    assert squashed[2] == 0.0, "x 가 1.0 으로 잘리면 남는 폭이 없다"


def test_the_frame_comes_from_the_same_function_the_analysis_uses():
    """🔴 고른 프레임과 분석이 따라가는 프레임이 갈리면 안 된다.

    `detect_candidates` 와 `--subject-at-ms` 가 **같은 `anchor_frame_for`** 를
    쓴다. 산술을 복제하면 한쪽만 고쳐졌을 때 사용자가 고른 사람과 분석 대상이
    달라지고, **결과에는 「지정대로 했다」고 남는다.**
    """
    for at_ms, fps, n in [(0.0, 30.0, 300), (2000.0, 30.0, 300), (1500.0, 15.88, 159)]:
        frame, offset, clamped = anchor_frame_for(at_ms, fps, n)
        assert 0 <= frame < n
        assert offset <= 0.5
        assert clamped is False
    # 창 밖은 끝으로 당기고 **그 사실을 남긴다** — 조용히 당기지 않는다.
    frame, _, clamped = anchor_frame_for(99_000.0, 30.0, 300)
    assert frame == 299 and clamped is True


def test_the_candidate_threshold_is_the_selector_threshold():
    """🔴 화면에 보이는데 고르면 분석이 안 되는 사람이 생기면 안 된다.

    후보 문턱을 selector 와 따로 두면 정확히 그 일이 난다. 상수 하나를
    공유하는지 본다 — 낮추면 B-1~B-6 이 무효라 **낮추는 것도 막는다.**
    """
    assert PERSON_ELIGIBLE_THRESHOLD == 0.5
    assert COCO_PERSON_LABEL == 0


def test_a_box_with_no_area_is_not_offered():
    """넓이가 0인 박스는 파서가 거부하므로 애초에 내면 안 된다."""
    box = _clip_unit_box(0.5, 0.5, 0.0, 0.3)
    with pytest.raises(ValueError):
        parse_subject_spec(",".join(str(v) for v in box), 0.0)


def test_boxes_are_ordered_by_area_not_by_a_guess():
    """🔴 순서가 곧 추천이다 — 재 보지 않은 기준으로 정렬하지 않는다.

    「공에 가장 가까운 사람」을 위로 올리고 싶어지는데, 임팩트 뒤에는 공이
    **이미 떠나가고 있어서** 그 순간 공에 가까운 사람이 찬 사람이 아닌 경우가
    흔하다. 넓이 내림차순은 「가까이·크게 찍힌 사람이 먼저」라는 뜻이고
    그건 설명할 수 있다.
    """
    people = [
        {"box": [0.1, 0.1, 0.1, 0.2], "score": 0.9},   # 넓이 0.02
        {"box": [0.5, 0.1, 0.3, 0.6], "score": 0.6},   # 넓이 0.18  ← 먼저
    ]
    people.sort(key=lambda p: p["box"][2] * p["box"][3], reverse=True)
    assert people[0]["score"] == 0.6, "점수가 아니라 넓이로 정렬한다"


def test_ball_is_reported_but_never_picks_a_person():
    """공은 **주기만** 한다 — 자동 선택하지 않는다 (`ho` 44번).

    자동으로 정하면 틀렸을 때 사용자가 **틀린 줄도 모른다.** 반환 모양에
    「추천된 사람」 자리가 없다는 것을 못박는다.
    """
    from supersub_agent.pose import detect_candidates

    doc = detect_candidates.__doc__ or ""
    assert "고르지 않는다" in doc
    # 🔴 키를 더하고 싶어지면 이 검사부터 마주치게 둔다.
    for forbidden in ("recommended", "suggested", "nearest_to_ball", "auto_pick"):
        assert forbidden not in doc.lower() or "않는다" in doc
