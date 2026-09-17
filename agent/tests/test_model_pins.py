"""모델 가중치가 **커밋으로 고정돼 있는지** (미결 11번의 남은 것).

🔴 **여기 있는 검사는 지우면 안 된다.** 막고 있는 것은 이것이다:

저장소 이름만으로 적재하면 업스트림이 가중치를 갈아 끼워도 **조용히 바뀐다.**
그리고 로컬 HF 캐시가 살아 있는 동안은 **드러나지도 않는다** — 같은 코드가 같은
영상에서 다른 점수를 내는데 아무 신호가 없다. 그때 판단은 "이번 결과를 채택할까"
가 아니라 **"B-2~B-6의 어느 결론까지 다시 봐야 하는가"** 가 된다(미결 11번).

`revision=` 한 조각이라 「관련 없어 보인다」고 지우기 쉽다. 지우면 결함이 **다음
누군가의 재실행에서** 돌아오고, 그때는 무엇이 달라졌는지 알 방법이 없다.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

from supersub_agent import judge as J
from supersub_agent import pose as P

SRC = Path(P.__file__).parent
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _from_pretrained_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "from_pretrained"]


def test_the_pose_models_are_pinned_to_a_commit():
    """검출기·포즈 모델은 **해시**로 고정한다 — 태그나 브랜치가 아니다."""
    for name, rev in (("PERSON_DETECTOR_REVISION", P.PERSON_DETECTOR_REVISION),
                      ("POSE_MODEL_REVISION", P.POSE_MODEL_REVISION)):
        assert HEX40.match(rev), (
            f"{name} 이 40자 커밋 해시가 아니다: {rev!r}. 브랜치·태그는 움직이므로 "
            "고정이 아니다."
        )


def test_every_pose_load_names_a_revision():
    """🔴 `revision=` 을 빼면 그 한 줄만으로 고정이 풀린다."""
    calls = _from_pretrained_calls(SRC / "pose.py")
    assert len(calls) == 4, (
        f"pose.py 의 from_pretrained 호출이 {len(calls)}개다 — 늘었으면 그것도 "
        "고정해야 한다(프로세서까지 포함해서 넷이었다)."
    )
    for c in calls:
        kw = {k.arg for k in c.keywords if k.arg}
        assert "revision" in kw, (
            f"pose.py:{c.lineno} 의 from_pretrained 에 revision 이 없다 — "
            "업스트림이 갈아 끼우면 조용히 바뀐다 (미결 11번)."
        )


def test_the_default_judge_model_is_pinned():
    """기본 판정 모델(1.2B)은 표에 있어야 한다.

    3.5 계열은 **비어 있는 것이 의도다** — 캐시가 없어 확인할 수 없고, 확인
    못 한 해시를 적으면 있는 근거처럼 보인다. 그래서 「전부 고정」이 아니라
    **기본값이 고정돼 있는지**를 검사한다.
    """
    default = J.MODELS["1.2B"]
    assert default in J.MODEL_REVISIONS, (
        f"{default} 가 MODEL_REVISIONS 에 없다 — 기본 판정 모델은 고정한다."
    )
    assert HEX40.match(J.MODEL_REVISIONS[default])


def _cached_head(repo_id: str) -> str | None:
    """HF 캐시가 지금 가리키는 커밋. 캐시가 없으면 None."""
    home = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    ref = (Path(home) / "hub" / f"models--{repo_id.replace('/', '--')}"
           / "refs" / "main")
    return ref.read_text(encoding="utf-8").strip() if ref.exists() else None


@pytest.mark.parametrize(
    ("repo", "pinned"),
    [
        (P.PERSON_DETECTOR, P.PERSON_DETECTOR_REVISION),
        (P.POSE_MODEL, P.POSE_MODEL_REVISION),
        (J.MODELS["1.2B"], J.MODEL_REVISIONS[J.MODELS["1.2B"]]),
    ],
)
def test_the_pin_still_matches_this_machines_cache(repo, pinned):
    """🔴 **이 검사가 표류를 알려 주는 자리다.**

    빨개지는 경우는 둘이고 **대응이 다르다.**

    | 무엇 | 어떻게 아나 | 할 일 |
    |---|---|---|
    | 업스트림이 갈아 끼웠다 | 고정한 해시는 그대로인데 `refs/main` 이 달라졌다 | **고정을 그대로 둔다.** 우리는 옛 가중치로 계속 돌고, 올리려면 재실행 회차를 연다 |
    | 내가 고정을 올렸다 | 해시를 방금 바꿨다 | 재실행 결과와 함께 커밋한다 |

    캐시가 없는 기계(새 클론·CI)에서는 **건너뛴다** — 없는 것은 어긋난 것이
    아니다. 대신 `revision=` 이 붙어 있으므로 처음 받을 때 이 해시를 받는다.
    """
    head = _cached_head(repo)
    if head is None:
        pytest.skip(f"{repo} 캐시가 이 기계에 없다")
    assert head == pinned, (
        f"🔴 {repo}: 고정 {pinned[:12]} 인데 캐시가 {head[:12]} 를 가리킨다.\n"
        "   업스트림이 갈아 끼웠거나 누가 받아 두었다는 뜻이다. **고정을 캐시에 "
        "맞추지 말 것** — 그러면 과거 결과와 다른 가중치로 조용히 갈아타는 것이다. "
        "올리려면 재실행 회차를 열고 결과와 함께 올린다 (미결 11번)."
    )
