"""지도자 문구 검수 서식이 루브릭과 어긋나지 않게 잡아 둔다 (미결 2번 문구 축).

🔴 **커밋해 둔 서식은 사본이다.** 루브릭의 문장을 고치고 서식을 다시 안 뽑으면
지도자는 **이미 바뀐 문장을 검수하게 되고**, 그 사실은 아무 데서도 드러나지
않는다 — 돌아온 답이 어느 판에 대한 것인지 모르게 되는 것이 이 검사가 막는
것이다.

사본을 아예 안 두는 선택지도 있었지만(스크립트만 두고 필요할 때 뽑기), 서식은
**사람에게 건네는 물건**이라 링크가 걸릴 자리가 있어야 한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "pending2_wording"))

from build_review_packet import render  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

PACKET = ROOT / "eval" / "pending2_wording" / "packet"
RUBRICS = discover_rubrics(ROOT / "rubrics")


def test_every_rubric_has_a_sheet_and_it_is_not_stale():
    """🔴 루브릭을 고쳤으면 서식을 다시 뽑는다.

        uv run python eval/pending2_wording/build_review_packet.py --write

    닫아 둔 동작(draft)도 낸다 — 여는 시점에 또 검수받지 않으려는 것이다.
    """
    for rubric in RUBRICS.values():
        path = PACKET / f"{rubric.sport}_{rubric.motion}.md"
        assert path.exists(), f"{rubric.key}: 서식이 없다 — 위 명령으로 뽑을 것"
        assert path.read_text(encoding="utf-8") == render(rubric), (
            f"{rubric.key}: 서식이 루브릭보다 낡았다 — 위 명령으로 다시 뽑을 것"
        )


def test_no_sheet_survives_a_rubric_that_is_gone():
    """지운 루브릭의 서식이 남아 있으면, 안 하는 종목 종이를 지도자에게 내민다.

    실제로 그럴 뻔했다 — 옆 폴더 `pending2_bands/packet/` 에는 2026.09.11 축구
    단일 종목 전환 때 지운 야구·농구 루브릭의 서식이 그대로 남아 있다.
    """
    live = {f"{r.sport}_{r.motion}.md" for r in RUBRICS.values()}
    stale = {p.name for p in PACKET.glob("*.md")} - live
    assert not stale, f"루브릭이 없는 서식이 남아 있다: {sorted(stale)}"


def test_the_sheet_marks_an_empty_sentence_instead_of_leaving_a_blank():
    """문장이 비면 **빈칸이 아니라 표식**이 보여야 한다.

    빈칸은 지도자에게 「검수할 것이 없다」로 읽힌다 — 실제로는 코드가 지은 틀로
    폴백해 **검수받지 않은 문장이 나가는** 상태다.
    """
    for rubric in RUBRICS.values():
        text = render(rubric)
        holes = [(c.id, g) for c in rubric.criteria for g in (2, 1, 0)
                 if not (c.card_lines.get(g) or "").strip()]
        assert not holes or "비어 있습니다" in text, holes
