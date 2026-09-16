"""지도자에게 내밀 종이가 조용히 낡지 않게 잡아 둔다 (미결 2번).

두 폴더가 각각 한 장씩 만든다 — `pending2_bands`(숫자·구간)와
`pending2_wording`(칭호·카드 문장).

🔴 **커밋해 둔 서식은 사본이다.** 루브릭이나 실측이 바뀌었는데 서식을 다시 안
뽑으면 지도자는 **이미 지난 판을 검수하게 되고**, 그 사실은 아무 데서도 드러나지
않는다 — 돌아온 답이 어느 판에 대한 것인지 모르게 되는 것이 이 검사가 막는
것이다.

**이미 한 번 일어났다.** 임계값 서식은 2026.09.09 에 만들어졌는데 B-6 실측이
2026.09.15 에 갱신됐고(43번 ㉳ 3회차, 마무리 길이를 구간 안에서 세도록 고침),
서식의 분포는 6일 전 숫자인 채로 남아 있었다. 그대로 내밀었으면 **지도자가 지난
측정값을 놓고 선을 그었을 것이다.** 2026.09.16 에 다시 뽑았다.

사본을 아예 안 두는 선택지도 있었지만(스크립트만 두고 필요할 때 뽑기), 서식은
**사람에게 건네는 물건**이라 링크가 걸릴 자리가 있어야 한다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "pending2_wording"))
sys.path.insert(0, str(ROOT / "eval" / "pending2_bands"))

import build_review_packet as bands  # noqa: E402
from build_review_packet import render as render_bands  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

# 🔴 두 폴더의 모듈 이름이 같다(`build_review_packet`). 평범하게 import 하면
#    먼저 들어온 쪽이 캐시에 남아 **다른 폴더의 서식을 검사하게 된다.** 그래서
#    wording 쪽은 파일 경로로 직접 적재한다. 이름을 다르게 짓는 편이 쉽지만,
#    옆 폴더와 같은 이름인 것이 「같은 관례의 서식」임을 읽히게 한다.
def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_wording = _load(
    ROOT / "eval" / "pending2_wording" / "build_review_packet.py",
    "wording_packet",
).render

BANDS = ROOT / "eval" / "pending2_bands" / "packet"
WORDING = ROOT / "eval" / "pending2_wording" / "packet"
RUBRICS = discover_rubrics(ROOT / "rubrics")


def test_the_wording_sheet_matches_the_rubrics():
    """🔴 루브릭 문장을 고쳤으면 서식을 다시 뽑는다.

        uv run python eval/pending2_wording/build_review_packet.py --write
    """
    for rubric in RUBRICS.values():
        path = WORDING / f"{rubric.sport}_{rubric.motion}.md"
        assert path.exists(), f"{rubric.key}: 문구 서식이 없다 — 위 명령으로 뽑을 것"
        assert path.read_text(encoding="utf-8") == render_wording(rubric), (
            f"{rubric.key}: 문구 서식이 루브릭보다 낡았다"
        )


def test_the_threshold_sheet_matches_the_rubrics_and_the_measurements():
    """🔴 구간이든 **실측이든** 바뀌었으면 서식을 다시 뽑는다.

        uv run python eval/pending2_bands/build_review_packet.py --write

    이쪽은 루브릭만 보는 것이 아니라 B-6 산출물의 분포를 싣는다. 그래서 루브릭을
    한 글자도 안 고쳐도 **평가를 다시 돌린 것만으로** 낡는다 — 실제로 그렇게
    낡았다(이 파일 머리말).
    """
    labels = bands.metric_labels()
    for sample_label, rubric, samples in bands.load_samples():
        path = BANDS / f"{rubric.sport}_{rubric.motion}.md"
        assert path.exists(), f"{rubric.key}: 임계값 서식이 없다 — 위 명령으로 뽑을 것"
        assert path.read_text(encoding="utf-8") == render_bands(
            rubric, sample_label, samples, labels
        ), f"{rubric.key}: 임계값 서식이 루브릭·실측보다 낡았다"


def test_no_sheet_survives_a_rubric_that_is_gone():
    """지운 루브릭의 서식이 남아 있으면 **안 하는 종목의 종이**를 내밀게 된다.

    실제로 남아 있었다 — 2026.09.11 축구 단일 종목 전환 때 지운 야구 타격·투구,
    농구 점프슛·레이업 넉 장이 `pending2_bands/packet/` 에 그대로 있었다
    (2026.09.16 정리).
    """
    live = {f"{r.sport}_{r.motion}.md" for r in RUBRICS.values()}
    for folder in (BANDS, WORDING):
        stale = {p.name for p in folder.glob("*.md")} - live
        assert not stale, f"{folder.name}: 루브릭이 없는 서식이 남아 있다 — {sorted(stale)}"


def test_the_wording_sheet_marks_an_empty_sentence_instead_of_leaving_a_blank():
    """문장이 비면 **빈칸이 아니라 표식**이 보여야 한다.

    빈칸은 지도자에게 「검수할 것이 없다」로 읽힌다 — 실제로는 코드가 지은 틀로
    폴백해 **검수받지 않은 문장이 나가는** 상태다.
    """
    for rubric in RUBRICS.values():
        text = render_wording(rubric)
        holes = [(c.id, g) for c in rubric.criteria for g in (2, 1, 0)
                 if not any(s.strip() for s in c.card_lines.get(g, ()))]
        assert not holes or "비어 있습니다" in text, holes
