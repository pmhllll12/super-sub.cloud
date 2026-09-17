"""루브릭 적재와 점수 합산.

설계 원칙: **총점은 언어 모델이 아니라 이 모듈이 계산한다.**
모델은 항목별 0/1/2 등급만 판정하고, 가중합은 결정론적 코드가 수행한다.
따라서 같은 판정에서는 언제나 같은 점수가 나오고, 가중치를 조정해도
재분석 없이 재계산된다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .features import MIRROR_ANTISYMMETRIC_METRICS

MAX_GRADE = 2

# 등급 판정 구간 (최소, 최대). None은 한쪽이 열린 구간을 뜻한다.
Interval = tuple[float | None, float | None]


class RubricError(ValueError):
    """루브릭 정의 자체가 잘못된 경우."""


def _parse_bands(entry: dict[str, Any]) -> tuple[str, dict[int, tuple[Interval, ...]]]:
    """루브릭 항목의 bands 블록을 파싱하고 검증한다."""
    raw = entry.get("bands")
    if not raw:
        raise RubricError(
            f"{entry['id']}: bands 없음. 등급은 코드가 구간으로 판정하므로 "
            "모든 항목에 bands가 있어야 한다."
        )

    metric = raw.get("metric")
    if metric not in entry.get("measured_by", []):
        raise RubricError(
            f"{entry['id']}: bands.metric {metric!r}가 measured_by에 없음. "
            "판정 근거가 아닌 지표로 등급을 정할 수 없다."
        )

    bands: dict[int, tuple[Interval, ...]] = {}
    for grade in (0, 1, 2):
        if grade not in raw:
            raise RubricError(f"{entry['id']}: bands에 {grade}등급 구간 누락")
        intervals: list[Interval] = []
        for pair in raw[grade]:
            if len(pair) != 2:
                raise RubricError(f"{entry['id']}: {grade}등급 구간 형식 오류 {pair!r}")
            lo, hi = pair
            lo = None if lo is None else float(lo)
            hi = None if hi is None else float(hi)
            if lo is not None and hi is not None and lo > hi:
                raise RubricError(f"{entry['id']}: {grade}등급 구간 역전 {pair!r}")
            intervals.append((lo, hi))
        if not intervals:
            raise RubricError(f"{entry['id']}: {grade}등급 구간이 비어 있음")
        if grade != 0 and any(lo is None or hi is None for lo, hi in intervals):
            raise RubricError(
                f"{entry['id']}: {grade}등급 구간의 끝이 열려 있음 {intervals!r}. "
                "열린 끝은 0등급에만 둔다 — 위가 열린 상위 등급은 측정 오류를 "
                "만점으로 만든다."
            )
        bands[grade] = tuple(intervals)

    return metric, bands


def _parse_phrases(
    entry: dict[str, Any], bands: dict[int, tuple[Interval, ...]], field_name: str
) -> dict[int, tuple[str, ...]]:
    """선수에게 보이는 문구를 읽는다 — 등급마다 **하나 또는 구간마다 하나**.

    `titles`(칭호)와 `card_lines`(추천 카드 문장)가 같은 규칙을 쓴다. 같은 함수로
    읽는 이유는 **두 곳에 같은 규칙을 적어 두면 한쪽만 고쳐지기** 때문이다.

    🔴 **자리가 어긋나면 반대로 말한다.** 골반 회전 1등급처럼 「덜 돌았다」와
    「너무 많이 돌았다」가 한 등급에 같이 있는 자리에서, 문장 순서가 구간 순서와
    다르면 **덜 돈 선수에게 「지나치게 많이 돌린다」**고 말한다. 예외도 경고도
    없이 문장만 반대인 형태라 여기서 막는다.
    """
    parsed: dict[int, tuple[str, ...]] = {}
    for key, written in (entry.get(field_name) or {}).items():
        grade = int(key)
        per_interval = not isinstance(written, str)
        lines = tuple(written) if per_interval else (written,)
        if not lines or not all(isinstance(s, str) and s.strip() for s in lines):
            raise RubricError(f"{entry['id']}: {grade}등급 {field_name} 이 비었다")
        # 🔴 목록으로 쓰면 **구간마다 쓰겠다는 뜻**이다. 그러면 개수가 맞아야
        #    한다 — 하나만 적어 두면 다른 방향의 선수는 조용히 틀로 떨어진다.
        if per_interval and len(lines) != len(bands.get(grade, ())):
            raise RubricError(
                f"{entry['id']}: {grade}등급 {field_name} {len(lines)}개가 구간 "
                f"{len(bands.get(grade, ()))}개와 안 맞는다. 구간마다 쓸 때는 "
                "bands 순서와 자리가 맞아야 한다 — 어긋나면 반대 방향을 말한다."
            )
        parsed[grade] = lines
    return parsed


@dataclass(frozen=True)
class Criterion:
    id: str
    name: str
    weight: float
    measured_by: tuple[str, ...]
    grades: dict[int, str]
    anchors: tuple[dict[str, Any], ...]
    rationale: str = ""
    # 등급별 칭호 — 선수에게 보여줄 짧은 표현. 채점에는 관여하지 않는다.
    # 지도자가 검수하는 문구이므로 UI가 아니라 루브릭에 둔다.
    #
    # `card_lines` 와 **같은 규칙**이다 — 등급마다 하나, 또는 구간마다 하나
    # (한 등급에 반대 방향이 있는 자리). 둘을 같은 함수로 읽는다(`_parse_phrases`).
    titles: dict[int, tuple[str, ...]] = field(default_factory=dict)
    # 추천 카드의 불릿 문장 (미결 `paik` 27번). 🔴 **칭호와 같은 자리에 둔다** —
    # 지도자가 검수할 문구라서 UI 가 아니라 루브릭에 산다. 채점에 관여하지 않는다.
    #
    # 등급마다 **문장 하나 또는 구간마다 하나**다. 뒤쪽은 한 등급에 **반대 방향
    # 구간**이 둘 있을 때 쓴다 — 예: 골반 회전 1등급은 「덜 돌았다」와 「너무
    # 많이 돌았다」가 같은 등급인데, 한 문장으로 부르면 **고칠 방향이 안 보인다.**
    # 여러 개면 `bands[grade]` 의 구간 순서와 **자리가 맞아야 한다**(적재가 검사).
    card_lines: dict[int, tuple[str, ...]] = field(default_factory=dict)
    # 등급 판정 구간. band_metric 하나의 값으로 등급이 결정된다.
    band_metric: str = ""
    bands: dict[int, tuple[Interval, ...]] = field(default_factory=dict)

    def title_for(self, grade: int, value: float | None = None) -> str:
        """해당 등급의 칭호. 정의되지 않았으면 항목명으로 대체한다.

        🔴 **한 등급에 반대 방향이 둘이면 `value` 가 있어야 고른다** (2026.09.16).
        「치우친 상체」처럼 한 말로 양쪽을 부르면 **어느 쪽으로 치우쳤는지**가
        안 보인다. 값이 없으면 방향을 찍지 않고 **항목명**으로 떨어진다 —
        `card_line_for` 가 빈 문자열로 떨어지는 것과 같은 판단이다.

        값을 넘기는 곳은 `aggregate` 하나다(거기에 `features` 가 있다). 서비스
        경로는 늘 넘긴다 — 안 넘기는 것은 합성 판정 데모(`scripts/demo.py`)뿐이고,
        거기서는 항목명이 나온다.
        """
        written = self.titles.get(grade, ())
        if not written:
            return self.name
        if len(written) == 1:
            return written[0]
        if value is None:
            return self.name
        for phrase, (lo, hi) in zip(written, self.bands.get(grade, ())):
            if (lo is None or value >= lo) and (hi is None or value <= hi):
                return phrase
        return self.name

    def card_line_for(self, grade: int, value: float | None = None) -> str:
        """추천 카드에 쓸 한 줄. 루브릭이 안 적었으면 빈 문자열이다.

        🔴 **여기서 지어내지 않는다** — 없으면 `scoring.card` 가 코드가 짓는
        틀로 떨어진다. 그 폴백이 단조로운 것은 알지만, **없는 말을 만드는 것보다
        낫다.**

        🔴 **문장에 숫자를 적지 않는다.** 이 줄은 구간마다 **고정**이라 측정값과
        함께 움직이지 않는다 — 「약 16cm」를 적어 두면 그 구간의 모든 영상이
        재지도 않은 수치를 달고 나간다. 수치가 필요한 자리는 `evidence` 다.
        `tests/test_summary.py` 가 루브릭에서 이걸 막는다.

        🔴 **문장이 구간마다 있으면 `value` 가 있어야 고를 수 있다.** 없으면 빈
        문자열이다 — **방향을 찍지 않는다.** 덜 돈 선수에게 「너무 많이 돌린다」고
        말하는 것은 아무 말도 안 하는 것보다 나쁘다.
        """
        written = self.card_lines.get(grade, ())
        if not written:
            return ""
        if len(written) == 1:
            # 방향과 무관한 한 문장 — 값이 없어도 쓸 수 있다.
            return written[0]
        if value is None:
            return ""
        for sentence, (lo, hi) in zip(written, self.bands.get(grade, ())):
            if (lo is None or value >= lo) and (hi is None or value <= hi):
                return sentence
        return ""

    def title_is_earned(self, grade: int) -> bool:
        """이 칭호가 **받은 것**인가 (`paik` 23번).

        🔴 `title_for` 는 폴백이 있어 **언제나 비지 않는다** — 0등급도
        「무너지는 축」 같은 문구를 받는다. 그래서 「`title` 이 있으면 받은
        것」으로 읽으면 화면이 **못한 항목에 호칭을 단다.** 받은 것은 최고
        등급뿐이고, 그 선은 이미 `summarize` 가 「강점」을 부르는 선과 같다.

        루브릭이 그 등급의 문구를 **안 적었으면 받지 않은 것으로 본다** —
        폴백은 항목명이지 지도자가 지어 준 칭호가 아니다.
        """
        return grade == MAX_GRADE and bool(self.titles.get(grade))

    def band_text(self, grade: int) -> str:
        """해당 등급의 수치 구간을 사람이 읽을 문장으로 만든다.

        **이 문구는 화면 쪽이 쓴다 — 판정 모델에게는 주지 않는다.** 예전에는
        프롬프트에 넣었다. 등급 정의만 주면 모델이 없는 상한을 지어냈기 때문인데
        ("40도 이상"인 기준이 화면에 "40~165도"로 나갔다), 구간을 주자 이번에는
        그 구간을 문장에 옮겨 쓰면서 등급 번호까지 함께 틀렸다 — 감점 문장 11건 중
        6건이 자기 등급과 반대로 말했다(미결 23번). 그래서 **문장에서 표기를 빼고
        등급·칭호·구간은 코드가 붙이는** 쪽으로 옮겼고, 이 메서드가 그 자리다.
        """
        parts = []
        for lo, hi in self.bands.get(grade, ()):
            if lo is None and hi is None:
                continue
            if lo is None:
                parts.append(f"{hi:g} 이하")
            elif hi is None:
                parts.append(f"{lo:g} 이상")
            else:
                parts.append(f"{lo:g}~{hi:g}")
        return " 또는 ".join(parts)

    def top_ceiling(self) -> float | None:
        """최상위 등급 구간의 **닫힌 위끝**. 위가 열려 있으면 None.

        상위 등급의 위를 닫는 것은 오측정이 만점이 되는 것을 막으려고 생긴
        규칙이다 — 투구 실클립의 골반 회전 181.1도가 「40도 이상」에 걸려
        장점으로 표시된 적이 있다. 그 규칙은 맞다.
        """
        if not self.bands:
            return None
        highs = [hi for _lo, hi in self.bands.get(max(self.bands), ()) if hi is not None]
        return max(highs) if highs else None

    def out_of_band(self, features: dict[str, Any]) -> str:
        """0등급이 **구간 위에서** 왔으면 `"above"`, 아니면 `""` (미결 20번).

        🔴 **점수를 바꾸지 않는다. 표시만 한다.**

        닫은 위쪽이 갈 곳이 0등급뿐이라 **「쟀는데 못했다」와 「구간 밖이다」가
        같은 0점**이 된다. 선수는 둘 다 "못했다"로 읽는다. 실측으로는 0등급
        117건 중 23건(20%)이 구간 위에서 왔고, active 루브릭에서도 난다
        (`eval/pending20_band_ceiling/`).

        🔴 **이것은 처방이 아니라 드러내기다.** 어느 처방(상한을
        PLAUSIBLE_RANGE 로 · 밴드에 excluded 구간 · 표시만)이 옳은지는 임계값
        검수(미결 2번)에 달려 있다. 미결 9번이 `timebase.limited_by` 로 한 것과
        같은 형태다 — 결함을 보이게 두되 동작점은 안 옮긴다.
        """
        if not self.band_metric or self.band_metric not in features:
            return ""
        ceiling = self.top_ceiling()
        if ceiling is None or self.grade_for(features) != 0:
            return ""
        return "above" if float(features[self.band_metric]) > ceiling else ""

    def view_dependent(self, features: dict[str, Any]) -> str:
        """이 항목의 등급이 **촬영 방향에 의존하는가** (미결 37번).

        🔴 **점수를 바꾸지 않는다. 표시만 한다.** `out_of_band`(미결 20번)·
        `timebase.limited_by`(미결 9번)와 같은 형태다 — 결함을 보이게 두되
        동작점은 안 옮긴다.

        | 값 | 뜻 |
        |---|---|
        | `""` | 이 항목의 판정 지표는 좌우 반전에 안 변한다 |
        | `"metric"` | 지표는 방향에 의존하지만 **이 값에서는 등급이 같다** |
        | `"grade"` | 🔴 **반대편에서 찍혔으면 등급이 달랐다** |

        🔴 **「그래서 이 점수가 틀렸다」가 아니다.** 정답이 없어 어느 부호가
        옳은지 모른다. 말할 수 있는 것은 **「같은 자세가 촬영 방향에 따라 다른
        등급을 받는다」**까지이고, 이 필드가 그것을 숨기지 않게 한다.

        처방 (가)밴드 0 대칭화·(나)방향 인식 지표는 각각 임계값 이동과
        `features` 변경을 부른다. 이것은 **셋 중 대가가 없는 (다)**이다.
        """
        metric = self.band_metric
        if metric not in MIRROR_ANTISYMMETRIC_METRICS or metric not in features:
            return ""
        mirrored = self._grade_at(-float(features[metric]))
        # 반전값이 어느 구간에도 없으면(밴드가 한쪽만 덮는 경우) 등급을 지어내지
        # 않는다 — 지표가 방향에 의존한다는 것까지만 말한다.
        if mirrored is None or mirrored == self.grade_for(features):
            return "metric"
        return "grade"

    def is_applicable(self, features: dict[str, Any]) -> bool:
        """이 항목을 판정할 근거 지표가 모두 측정됐는지.

        도구 기반 지표는 공이 검출되지 않은 영상에서 빠진다. 그런 항목은 판정하지
        않고 가중치에서도 제외한다 — 측정하지 못한 것을 0점으로 매기면 촬영
        조건이 나빴다는 이유로 선수가 감점된다.
        """
        return all(m in features for m in self.measured_by)

    def band_margin(self, features: dict[str, Any]) -> float:
        """측정값이 자기 등급 구간의 **안쪽에 얼마나 들어와 있는지** (0~0.5).

        구간 폭 대비 가까운 경계까지의 거리다. 경계 위면 0, 한가운데면 0.5,
        열린 끝(0등급) 쪽은 0.5로 본다.

        장단점 표기에 쓴다. 경계에 걸친 값을 "장점"이라고 부르면 다음 클립에서
        뒤집힌다 — 선수 카드에 남는 문구는 한 프레임 차이로 바뀌지 않는 것만
        올린다 (CONFIDENT_MARGIN).
        """
        if self.band_metric not in features:
            return 0.0
        value = float(features[self.band_metric])
        for lo, hi in self.bands[self.grade_for(features)]:
            if (lo is None or value >= lo) and (hi is None or value <= hi):
                if lo is None or hi is None:
                    return 0.5
                width = hi - lo
                if width <= 0:
                    return 0.0
                return min(value - lo, hi - value) / width
        return 0.0

    def grade_for(self, features: dict[str, Any]) -> int:
        """측정값을 구간과 대조해 등급을 결정한다.

        **등급은 언어 모델이 아니라 이 함수가 정한다.** 루브릭의 등급 정의가
        이미 수치 구간이므로 판정에 추론이 필요 없다. EXAONE 1.2B는 실제로
        141.7이 140~165 범위 안이라는 비교를 틀렸다(재현되는 오답).

        구간은 양끝을 포함하고, 2 → 1 → 0 순으로 먼저 맞는 등급을 취한다.
        경계값(예: 150)이 두 등급에 걸치면 높은 등급으로 간다.
        """
        if self.band_metric not in features:
            raise RubricError(
                f"{self.id}: 등급 판정 지표 {self.band_metric!r}가 측정값에 없음"
            )
        value = float(features[self.band_metric])
        grade = self._grade_at(value)
        if grade is None:
            raise RubricError(
                f"{self.id}: {self.band_metric}={value}가 어느 등급 구간에도 없음. "
                "루브릭 bands가 값 범위를 모두 덮지 않는다."
            )
        return grade

    def _grade_at(self, value: float) -> int | None:
        """구간 판정의 알맹이. 어느 구간에도 없으면 None (grade_for가 오류로 옮긴다)."""
        for grade in (2, 1, 0):
            for lo, hi in self.bands.get(grade, ()):
                if (lo is None or value >= lo) and (hi is None or value <= hi):
                    return grade
        return None

    def _interval_at(self, value: float, grade: int) -> Interval | None:
        for lo, hi in self.bands.get(grade, ()):
            if (lo is None or value >= lo) and (hi is None or value <= hi):
                return (lo, hi)
        return None

    def _nearest(self, grades: tuple[int, ...], value: float) -> tuple[float, float | None]:
        """주어진 등급들의 구간 중 가장 가까운 것까지의 (거리, 그 구간의 폭).

        구간 안이면 거리 0. 폭은 한쪽이 열려 있으면 None이다.
        """
        best: tuple[float, float | None] = (float("inf"), None)
        for grade in grades:
            for lo, hi in self.bands.get(grade, ()):
                inside = (lo is None or value >= lo) and (hi is None or value <= hi)
                ends = [e for e in (lo, hi) if e is not None]
                if not inside and not ends:
                    continue
                distance = 0.0 if inside else min(abs(value - e) for e in ends)
                width = hi - lo if lo is not None and hi is not None else None
                if distance < best[0]:
                    best = (distance, width)
        return best

    def _risk_edges(self, interval: Interval) -> tuple[float, ...]:
        """이 구간의 끝 중 **넘어가면 등급이 떨어지는** 쪽만.

        위가 열린 최상위 구간(`hip_rotation`의 25~180 같은 것)은 끝이 물리적
        한계일 뿐 위험이 아니다. 그 끝까지 거리를 재서 감점하면 **잘한 값을
        깎는다** — 180도로 완전히 돌린 골반이 한가운데 102도보다 낮은 점수를
        받게 된다. 그래서 실제로 아래 등급이 붙어 있는 끝만 센다.
        """
        edges = []
        for end, outward in ((interval[0], -1.0), (interval[1], +1.0)):
            if end is None:
                continue
            beyond = self._grade_at(end + outward * 1e-6)
            if beyond is not None and beyond < max(self.bands):
                edges.append(end)
        return tuple(edges)

    def score_for(self, features: dict[str, Any]) -> float | None:
        """항목별 **연속 점수** 0~100. 측정값이 없으면 None.

        🔴 **총점은 이 값에서 나오지 않는다.** 총점·등급은 `aggregate`가
        등급(0/1/2)의 가중합으로 내고 이 함수는 거기에 관여하지 않는다.
        레이더 차트처럼 **항목 사이의 모양**을 보여줄 때 0·50·100 세 자리만
        찍히면 읽을 것이 없어서 만든 표시용 값이다.

        뜻은 **「이상 구간(최상위 등급)에서 얼마나 떨어져 있는가」**다.

        | 등급 | 점수대 | 안에서의 위치 |
        |---|---|---|
        | 2 | 85~100 | 위험한 끝에서 멀수록 높다 (`_risk_edges`) |
        | 1 | 50~85 | 이상 구간에 가까울수록 높다 |
        | 0 | 0~50 | 바로 위 등급 구간에 가까울수록 높다 |

        구간이 겹치지 않으므로 **등급 순서를 뒤집지 않는다** — 2등급 항목이
        1등급 항목보다 낮게 찍히는 일이 없다. 루브릭에 빈틈이 생겨도 그렇도록
        마지막에 등급별 점수대로 자른다.
        """
        if self.band_metric not in features:
            return None
        value = float(features[self.band_metric])
        grade = self.grade_for(features)
        top = max(self.bands)
        floor, ceiling = SCORE_BANDS[grade]

        if grade == top:
            interval = self._interval_at(value, top)
            edges = self._risk_edges(interval) if interval else ()
            width = (
                interval[1] - interval[0]
                if interval and interval[0] is not None and interval[1] is not None
                else None
            )
            if not edges or not width:
                score = ceiling
            else:
                # 자(尺)는 **떨어질 수 있는 거리**다. 양끝이 다 위험하면
                # 한가운데가 가장 먼 자리라 반폭이고, 한쪽만 위험하면
                # (`hip_rotation` 25~180) 반대쪽 끝까지가 전부 여유라 전폭이다.
                # 반폭으로 통일하면 위가 열린 구간에서 한가운데를 넘는 값이
                # 전부 만점이 되어 **더 잘한 것과 덜 잘한 것이 같아진다.**
                ruler = width / 2 if len(edges) == 2 else width
                room = min(abs(value - e) for e in edges) / ruler
                score = floor + (ceiling - floor) * min(1.0, room)
        elif grade == 1:
            interval = self._interval_at(value, 1)
            # 1·2등급 구간은 양끝이 닫혀 있다(_parse_bands가 강제한다).
            width = interval[1] - interval[0] if interval else None
            distance, _ = self._nearest((top,), value)
            score = (
                ceiling - (ceiling - floor) * min(1.0, distance / width)
                if width
                else floor
            )
        else:
            # 0등급은 열린 끝을 가질 수 있어 자기 구간 폭을 자로 쓸 수 없다.
            # 바로 위 등급 구간까지의 거리를 그 구간의 폭으로 잰다.
            distance, width = self._nearest(tuple(g for g in self.bands if g > 0), value)
            score = ceiling * max(0.0, 1.0 - distance / width) if width else floor

        return round(min(max(score, floor), ceiling), 1)


CONFIDENT_MARGIN = 0.2

# 등급별로 항목 점수(`Criterion.score_for`)가 놓일 자리. 겹치지 않게 둔다 —
# 겹치면 화면의 레이더 차트가 리포트의 등급과 반대로 말한다.
SCORE_BANDS: dict[int, tuple[float, float]] = {
    2: (85.0, 100.0),
    1: (50.0, 85.0),
    0: (0.0, 50.0),
}


@dataclass(frozen=True)
class Rubric:
    sport: str
    motion: str
    version: str
    criteria: tuple[Criterion, ...]
    grade_bands: dict[str, int]
    review_required: bool
    pipeline_version: str
    # 임팩트를 정의할 사지 — "leg"(축구 슈팅) 또는 "arm". 팔 종목 루브릭은
    # 2026.09.11 에 지웠지만 **어휘는 남긴다** — `features.py` 의 임팩트 정의가
    # 사지로 갈리고, 그 분기는 축구만 남아도 그대로 돈다.
    # 루브릭이 선언하고 features.extract_features가 따른다.
    impact_limb: str = "leg"
    # 임팩트로 삼을 사건 — "extension_peak"(채찍질) 또는 "distal_apex"(들어올림).
    impact_event: str = "extension_peak"
    # 화면 표기용 한글 이름. 없으면 sport·motion을 그대로 쓴다.
    sport_ko: str = ""
    motion_ko: str = ""
    # 이 루브릭으로 실제 영상을 끝까지 돌려 본 근거. 비어 있으면 미검증이다.
    # 임계값이 임시값인 것(review_required)과는 다른 문제다 — 이쪽은 파이프라인이
    # 그 종목 영상에서 지표를 뽑을 수 있는지 자체를 확인했는가를 뜻한다.
    validated_on: str = ""
    # 사용자에게 내보낼지 여부 — "active"만 선택지에 오른다.
    #
    # review_required와 축이 다르다. 이쪽은 **범위**(지금 여는 동작인가), 저쪽은
    # **검수**(임계값이 확정됐는가)다. 열려 있으면서 검수 전일 수 있고(지금 세
    # 루브릭이 그렇다, 결과에 provisional로 표기된다), 검수가 끝나도 범위 밖이라
    # 닫아 둘 수 있다.
    #
    # "draft"를 지우지 않고 두는 이유는 임계값·칭호가 이미 들어 있어서다. 계약
    # 테스트는 draft도 포함해 돌므로, 닫아 둔 동안 파이프라인이 바뀌어 지표가
    # 어긋나면 여는 시점이 아니라 그때 걸린다.
    status: str = "active"

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def key(self) -> str:
        """루브릭 식별자 "종목/동작". 루브릭은 (종목, 동작) 단위로 하나씩 있다."""
        return f"{self.sport}/{self.motion}"

    @property
    def label(self) -> str:
        """사람이 읽을 이름. UI의 종목 선택이 이걸 쓴다."""
        return f"{self.sport_ko or self.sport} · {self.motion_ko or self.motion}"

    @property
    def criterion_ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.criteria)

    def get(self, criterion_id: str) -> Criterion:
        for c in self.criteria:
            if c.id == criterion_id:
                return c
        raise KeyError(criterion_id)

    def applicable_criteria(self, features: dict[str, Any]) -> tuple[Criterion, ...]:
        """이번 영상에서 판정 가능한 항목만 고른다.

        도구가 검출되지 않으면 그 도구를 쓰는 항목이 빠지고, 남은 항목들로만
        가중치를 재정규화해 총점을 낸다 (aggregate 참고).
        """
        applicable = tuple(c for c in self.criteria if c.is_applicable(features))
        if not applicable:
            raise RubricError("판정 가능한 항목이 하나도 없음 — 측정값이 비었다")
        return applicable

    def required_metrics(self) -> set[str]:
        """모든 항목이 근거로 삼는 지표 이름의 합집합."""
        return {m for c in self.criteria for m in c.measured_by}


def discover_rubrics(directory: str | Path) -> dict[str, Rubric]:
    """디렉터리의 루브릭을 모두 읽어 "sport/motion" 키로 돌려준다.

    루브릭 추가가 코드 변경이 아니라 **파일 추가**가 되도록 하는 진입점이다.
    파일명이 아니라 파일 안의 sport·motion을 키로 삼는다 — 이름과 내용이
    어긋나는 것을 막는다.
    """
    found: dict[str, Rubric] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        rubric = load_rubric(path)
        if rubric.key in found:
            raise RubricError(
                f"루브릭 키 중복 {rubric.key!r}: {path.name}. "
                "sport·motion 조합은 파일마다 고유해야 한다."
            )
        found[rubric.key] = rubric
    if not found:
        raise RubricError(f"루브릭을 찾지 못함: {directory}")
    return found


def load_rubric(path: str | Path) -> Rubric:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    criteria: list[Criterion] = []
    for entry in raw.get("criteria", []):
        grades = {int(k): v for k, v in entry["grades"].items()}
        missing = {0, 1, 2} - grades.keys()
        if missing:
            raise RubricError(f"{entry['id']}: 등급 정의 누락 {sorted(missing)}")
        if not entry.get("measured_by"):
            raise RubricError(
                f"{entry['id']}: measured_by가 비어 있음. "
                "근거 지표가 없는 항목은 판정할 수 없다."
            )
        band_metric, bands = _parse_bands(entry)
        criteria.append(
            Criterion(
                id=entry["id"],
                name=entry["name"],
                weight=float(entry["weight"]),
                measured_by=tuple(entry["measured_by"]),
                grades=grades,
                anchors=tuple(entry.get("anchors", [])),
                rationale=entry.get("rationale", ""),
                titles=_parse_phrases(entry, bands, "titles"),
                card_lines=_parse_phrases(entry, bands, "card_lines"),
                band_metric=band_metric,
                bands=bands,
            )
        )

    if not criteria:
        raise RubricError("채점 항목이 하나도 없음")

    total_weight = sum(c.weight for c in criteria)
    if abs(total_weight - 1.0) > 1e-6:
        raise RubricError(f"가중치 합이 1.0이 아님: {total_weight:.4f}")

    return Rubric(
        sport=raw["sport"],
        motion=raw["motion"],
        version=str(raw.get("version", "0")),
        criteria=tuple(criteria),
        grade_bands=raw.get("grade_bands", {"A": 85, "B": 70, "C": 50, "D": 0}),
        review_required=bool(raw.get("review_required", False)),
        pipeline_version=raw.get("pipeline_version", "unknown"),
        impact_limb=_parse_choice(raw, "impact_limb", ("leg", "arm")),
        impact_event=_parse_choice(
            raw, "impact_event", ("extension_peak", "distal_apex")
        ),
        sport_ko=raw.get("sport_ko", ""),
        motion_ko=raw.get("motion_ko", ""),
        validated_on=raw.get("validated_on", ""),
        status=_parse_status(raw),
    )


def _parse_status(raw: dict[str, Any]) -> str:
    """루브릭을 사용자에게 내보낼지 읽는다. 기본은 active다.

    오타가 나면 조용히 닫히는 것이 아니라 적재에서 걸리게 한다 — 열려 있어야
    할 동작이 선택지에서 사라지는 쪽이 더 알아채기 어렵다.
    """
    value = raw.get("status", "active")
    if value not in ("active", "draft"):
        raise RubricError(f"status는 'active' 또는 'draft'여야 한다: {value!r}")
    return value


def _parse_choice(raw: dict[str, Any], field_name: str, allowed: tuple[str, ...]) -> str:
    """kinematics 블록의 열거형 필드를 읽고 검증한다.

    기본값은 allowed의 첫 값이다 — 이 필드들이 생기기 전에 쓴 루브릭이 그대로
    동작해야 하므로, 옛 동작(다리·신전 각속도)을 첫 값으로 둔다.
    """
    value = (raw.get("kinematics") or {}).get(field_name, allowed[0])
    if value not in allowed:
        raise RubricError(
            f"kinematics.{field_name}은 {list(allowed)} 중 하나여야 한다: {value!r}"
        )
    return value


def _has_final_consonant(word: str) -> bool | None:
    """마지막 글자에 받침이 있는가. 한글이 아니면 None (모르면 안 고른다)."""
    for ch in reversed(word.strip()):
        if ch.isspace():
            continue
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            return (code - 0xAC00) % 28 != 0
        return None
    return None


def _with_particle(word: str, after_consonant: str, after_vowel: str) -> str:
    """조사를 붙인다. 🔴 판별이 안 되면 **둘 다 적는다**(`이(가)`).

    선수에게 보이는 글이라 「차는 다리 뻗기이(가)」 같은 것이 그대로 나가면
    안 된다. 다만 한글이 아닌 이름(영문·숫자)에서 아무 쪽이나 고르면 틀린
    조사를 확신에 차서 쓰게 되므로, 그때는 모른다는 것을 드러낸다.
    """
    final = _has_final_consonant(word)
    if final is None:
        return f"{word}{after_consonant}({after_vowel})"
    return f"{word}{after_consonant if final else after_vowel}"


def _ro(word: str) -> str:
    """`로`/`으로`. ㄹ 받침은 `로`를 쓴다 (「채찍이 된 다리」로 · 「잠긴 골반」으로)."""
    for ch in reversed(word.strip()):
        if ch.isspace():
            continue
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            final = (code - 0xAC00) % 28
            return "로" if final in (0, 8) else "으로"
        return "로(으로)"
    return "로(으로)"


def summarize(breakdown: list[dict[str, Any]]) -> str:
    """선수에게 보여줄 두 문장 이내의 요약 (미결 `paik` 7번 · `min` 9번).

    🔴 **모델을 부르지 않는다. 코드가 짓는다.**

    근거 문장(`evidence`)은 모델이 쓰지만 요약은 아니다. 이유가 둘이다.

    1. **계약 3장 4가 총점·등급 숫자를 금지한다.** 모델에게 맡기면 그것을
       지키는지 매번 확인해야 한다 — 미결 23번에서 근거 문장이 자기 등급과
       반대로 말하는 것을 잡는 데 2회차가 걸렸고 아직 1/19이 남아 있다.
       **여기서는 숫자를 쓸 자리 자체를 안 만든다**(검사가 자릿수 0을 지킨다).
    2. **정답이 없다.** 「더 나은 요약」은 좋아졌는지 판정할 방법이 없다.
       코드가 지으면 같은 판정에서 **같은 문장**이 나와 재현된다.

    재료는 이미 확정된 것뿐이다 — 등급이 가장 높은 항목의 칭호와 가장 낮은
    항목의 칭호. 🔴 **없는 것은 지어내지 않는다**: 전부 잘했으면 아쉬운 점을
    만들지 않고, 전부 못했으면 강점을 만들지 않는다.

    나중에 모델이 쓰는 코칭 문장으로 바꾸려면 **별도 회차 + 사전 등록**이다.
    """
    if not breakdown:
        return ""

    # 같은 등급이면 **비중이 큰 쪽**을 고른다. 총점을 움직인 항목이 선수에게도
    # 할 말이 많은 항목이다. 정렬을 안정시키려고 criterion_id 까지 넣는다 —
    # 같은 판정이 같은 문장을 내야 재현이 성립한다.
    def rank(item: dict[str, Any]) -> tuple:
        return (int(item["grade"]), float(item.get("weight") or 0.0),
                str(item["criterion_id"]))

    ordered = sorted(breakdown, key=rank)
    worst, best = ordered[0], ordered[-1]

    parts: list[str] = []
    # 🔴 **강점은 최고 등급일 때만 그렇게 부른다.** 1등급을 「강점」이라 하면
    #    고칠 것이 있는 동작을 잘했다고 말하게 된다.
    if int(best["grade"]) == MAX_GRADE:
        parts.append(f"{_with_particle(best['name'], '이', '가')} "
                     f"「{best['title']}」{_ro(best['title'])} 이번 동작의 강점입니다.")
    if int(worst["grade"]) < MAX_GRADE and worst["criterion_id"] != best["criterion_id"]:
        parts.append(f"{_with_particle(worst['name'], '은', '는')} "
                     f"「{worst['title']}」{_ro(worst['title'])} 가장 아쉬웠습니다.")

    if not parts:
        # 전부 중간 등급이라 강점·약점이 안 갈렸거나 항목이 하나뿐인 경우.
        # 🔴 갈리지 않았는데 갈린 척하지 않는다.
        parts.append(f"{_with_particle(worst['name'], '은', '는')} "
                     f"「{worst['title']}」{_ro(worst['title'])} 나왔습니다.")
    return " ".join(parts)


def card(breakdown: list[dict[str, Any]],
         rubric: "Rubric | None" = None,
         features: dict[str, Any] | None = None) -> dict[str, Any]:
    """추천 카드에 쓸 **짧은 수식어 + 불릿 두 줄** (미결 `paik` 27번의 설명 칸).

    화면(`SquadSuggest.tsx`)이 후보마다 이름 아래에 한 줄(`title`)과 불릿
    둘(`notes`)을 그리는데 지금은 **붙박이 문자열**이다. 그 자리를 분석으로
    채우기 위한 블록이다.

    🔴 **모델을 부르지 않는다.** `summarize` 와 같은 이유다 — 정답이 없는 문장을
    모델에게 맡기면 좋아졌는지 판정할 수 없고, 같은 판정이 매번 다른 말을 한다.

    🔴 **이 카드가 말할 수 있는 것은 「이 영상에서 잰 자세」뿐이다.** 붙박이
    문자열에는 「활동량이 많고 꾸준합니다」·「10경기 연속」 같은 것이 섞여
    있는데, 그건 **경기 기록**이지 우리가 잰 것이 아니다. 여기서 만들지 않는다 —
    화면이 그런 줄을 함께 쓰고 싶으면 **출처가 다른 줄**로 따로 받아야 한다.

    | | |
    |---|---|
    | `title` | **가장 잘한 항목의 칭호.** 🔴 `title_earned` 가 참일 때만 — 안 그러면 0등급의 「무너지는 축」이 수식어로 걸린다(`paik` 23번) |
    | `notes` | **가장 잘한 등급의 항목만** 최대 두 줄, 가중치 큰 것부터 |

    🔴 **아쉬운 항목을 여기 적지 않는다** (2026.09.16 결정). 이 카드는 **남이
    보는 화면**이고 묻는 것은 「이 선수를 부를까」다. 사람 이름 옆에 붙는 약점
    한 줄은 그 판단에 보태는 것보다 **사람을 규정하는 쪽**으로 읽힌다 — 못 받은
    칭호를 수식어로 달지 않기로 한 것(`paik` 23번)과 같은 자리다. **본인
    리포트에는 그대로 있다** — 거기서는 아쉬운 항목이 코칭이지 낙인이 아니다.

    🔴 **그래도 비우지는 않는다.** 2등급이 하나도 없으면 **그 선수에게서 가장
    나은 등급의 항목**을 적는다. 실측으로는 드물다 — 축구 18편에서 2등급을
    하나라도 가진 편이 **17편**(나머지 1편은 최고가 1등급, 0등급이 최고인 편은
    없었다). 편당 2등급 개수는 중앙값 2라 **두 줄을 강점으로만 채울 수 있다.**

    🔴 **1등급을 「강점」이라 부르지 않는다** (`summarize` 와 같은 규칙). 가장
    나은 등급이 2등급이 아니면 문장은 **그 등급의 문장**이지 칭찬이 아니다.

    🔴 **불릿 문장은 루브릭이 등급마다 적어 둔 `card_lines` 다** (2026.09.16).
    코드가 짓던 틀(「…가 이번 동작의 강점입니다」)은 항목 이름만 갈아 끼우는
    문장이라 **카드마다 같은 말**로 읽혔다. 칭호(`titles`)와 **같은 자리에 두는
    이유도 같다** — 선수에게 보이는 문구는 지도자가 검수해야 하고, 검수 대상은
    코드가 아니라 데이터여야 한다.

    🔴 **여기서 다양성을 기대하지 않는다.** 같은 항목·같은 등급이면 문장도 같다.
    이 블록이 사는 것은 **검수된 자연스러운 문구**이지 카드마다 다른 말이 아니다.
    선수마다 달라지는 문장이 필요하면 그건 `evidence` 의 일이다.

    🔴 **`rubric` 을 안 주면 코드가 지은 틀로 떨어진다.** 이 함수는 루브릭 없이도
    (평가·재현 경로가 `breakdown` 만 들고 부른다) 돌아야 하고, 빈 카드를 내보내는
    것보다 단조로운 문장이 낫다.

    점수와 무관하다(`summary`·`stat` 과 같은 성질) — 이 키를 빼도 총점은 한
    비트도 안 바뀌고 **B-6 재실행을 부르지 않는다**.
    """
    if not breakdown:
        return {"title": None, "notes": []}

    def rank(item: dict[str, Any]) -> tuple:
        return (int(item["grade"]), float(item.get("weight") or 0.0),
                str(item["criterion_id"]))

    ordered = sorted(breakdown, key=rank)
    best = ordered[-1]

    # 🔴 받은 칭호만 수식어가 된다. 못 받았으면 **비운다** — 화면이 이름 아래에
    #    아무것도 안 그리는 편이, 아쉬운 항목의 칭호를 자랑처럼 다는 것보다 낫다.
    title = best["title"] if best.get("title_earned") else None

    def line(item: dict[str, Any], fallback: str) -> str:
        """그 항목·그 등급에 대해 루브릭이 적어 둔 한 줄. 없으면 코드가 지은 틀.

        한 등급에 **반대 방향 구간**이 둘 있는 항목은 측정값이 있어야 어느 쪽인지
        고를 수 있다 — `features` 를 안 주면 루브릭 문장 대신 **방향을 말하지
        않는 틀**로 떨어진다(`card_line_for` 가 빈 문자열을 준다).
        """
        if rubric is None:
            return fallback
        try:
            criterion = rubric.get(str(item["criterion_id"]))
        except KeyError:
            # 판정에만 있고 루브릭에 없는 항목 — aggregate가 먼저 막지만,
            # 이 함수는 breakdown만 들고 따로 불릴 수 있다.
            return fallback
        measured = (features or {}).get(criterion.band_metric)
        value = measured if isinstance(measured, (int, float)) else None
        return criterion.card_line_for(int(item["grade"]), value).strip() or fallback

    # 🔴 **가장 잘한 등급에 있는 항목만** 고른다. 그 아래 등급은 이 카드에
    #    안 나온다 — 아쉬운 항목은 본인 리포트의 몫이다(위 표).
    top_grade = int(best["grade"])
    picked = sorted(
        (it for it in breakdown if int(it["grade"]) == top_grade),
        # 가중치가 큰 것부터 — 이 동작에서 더 중요한 항목이 먼저 보인다.
        key=lambda it: (-float(it.get("weight") or 0.0), str(it["criterion_id"])),
    )

    def fallback(item: dict[str, Any]) -> str:
        """루브릭이 문장을 안 줬을 때 코드가 짓는 틀.

        🔴 **2등급이 아니면 「강점」이라 부르지 않는다** (`summarize` 와 같은
        규칙). 그 자리는 그저 **이 선수에게서 가장 나은 항목**이지 잘한 것이
        아니다.
        """
        if top_grade == MAX_GRADE:
            # 🔴 수식어(칭호)를 불릿에서 **다시 말하지 않는다** — 화면이 둘을
            #    나란히 그리므로 같은 말이 두 번 보인다. 여기는 **항목 이름**이다.
            return f"{_with_particle(item['name'], '이', '가')} 이번 동작의 강점입니다"
        return (f"{_with_particle(item['name'], '은', '는')} "
                f"「{item['title']}」{_ro(item['title'])} 나왔습니다")

    # 두 줄까지다. 하나뿐이면 하나만 — 채우려고 아래 등급을 끌어오지 않는다.
    notes = [line(it, fallback(it)) for it in picked[:2]]
    return {"title": title, "notes": notes}


def aggregate(
    judgments: dict[str, dict[str, Any]],
    rubric: Rubric,
    expected_ids: Iterable[str] | None = None,
    features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """항목별 판정을 총점으로 합산한다.

    judgments: {criterion_id: {"grade": int, "evidence": str, "metric_ref": str}}

    `features`를 주면 0등급이 **구간 위에서** 왔는지를 `out_of_band`로(미결
    20번), 등급이 **촬영 방향에 의존하는지**를 `view_dependent`로(미결 37번)
    표시한다. 🔴 **점수는 그 둘과 무관하다** — 안 주면 두 필드가 빈 문자열일
    뿐이고 나머지는 한 비트도 같다. B-6 재실행을 부르지 않는 이유다.
    """
    unknown = judgments.keys() - set(rubric.criterion_ids)
    if unknown:
        raise ValueError(f"루브릭에 없는 항목의 판정: {sorted(unknown)}")

    # expected_ids를 주면 그 목록은 반드시 다 채워져 있어야 한다. 도구 미검출로
    # 빠지는 것과 판정이 실패해 빠지는 것을 구분하기 위한 장치다 — 주지 않으면
    # 없는 항목이 조용히 제외되므로, 파이프라인은 항상 넘긴다.
    if expected_ids is not None:
        missing = set(expected_ids) - judgments.keys()
        if missing:
            raise ValueError(f"판정이 누락된 항목: {sorted(missing)}")

    judged = [c for c in rubric.criteria if c.id in judgments]
    if not judged:
        raise ValueError("판정이 하나도 없음")

    # 판정된 항목만으로 가중치를 재정규화한다. 도구 미검출로 빠진 항목이 있어도
    # 남은 항목의 상대 비중이 유지되고 총점은 100점 만점을 지킨다.
    # 빠진 항목을 0점으로 두면 촬영 조건 때문에 선수가 감점된다.
    total_weight = sum(c.weight for c in judged)
    if total_weight <= 0:
        raise ValueError("판정된 항목의 가중치 합이 0")

    ratio = 0.0
    breakdown = []
    for c in judged:
        j = judgments[c.id]
        grade = int(j["grade"])
        if grade not in (0, 1, 2):
            raise ValueError(f"{c.id}: 등급은 0/1/2만 허용, 받은 값 {grade}")
        weight = c.weight / total_weight
        contribution = weight * (grade / MAX_GRADE)
        ratio += contribution
        # 한 등급에 **반대 방향 구간**이 둘 있는 항목은 이 값이 있어야 어느 쪽
        # 칭호인지 고른다. 없으면 `title_for` 가 항목명으로 떨어진다 — 방향을
        # 찍지 않는다. 🔴 **점수는 이 값과 무관하다**(등급은 이미 판정돼 왔다).
        measured = (features or {}).get(c.band_metric)
        value = measured if isinstance(measured, (int, float)) else None
        breakdown.append(
            {
                "criterion_id": c.id,
                "name": c.name,
                "grade": grade,
                "weight": round(weight, 4),
                "contribution": round(contribution * 100, 1),
                # 등급 표기는 **여기서** 붙는다. 모델 문장(evidence)에는 등급
                # 번호도 구간도 없다 — 미결 23번의 처방이다. 화면이 칭호·구간을
                # 보여주려면 루브릭을 다시 열지 않고 이 두 필드를 쓰면 된다.
                "title": c.title_for(grade, value),
                # 🔴 위 `title` 은 **모든 등급에 있다** — 「받았는가」는 이쪽이
                # 답한다 (`paik` 23번). 화면이 `title != null` 로 선을 그으면
                # 0등급의 「무너지는 축」까지 호칭으로 그린다. 점수는 안 바뀐다.
                "title_earned": c.title_is_earned(grade),
                "band": c.band_text(grade),
                # 🔴 이 0등급이 **구간 위에서** 왔는가 (미결 20번). 점수는 안
                # 바뀐다 — 「쟀는데 못했다」와 「구간 밖이다」를 화면이 가를 수
                # 있게 하는 표시일 뿐이다. features 를 안 주면 빈 문자열이다.
                "out_of_band": c.out_of_band(features) if features else "",
                # 🔴 이 등급이 **촬영 방향에 의존하는가** (미결 37번). 여기도
                # 점수는 안 바뀐다 — `"grade"` 면 반대편에서 찍혔을 때 등급이
                # 달랐다는 뜻이고, **지금 점수가 틀렸다는 뜻이 아니다.**
                "view_dependent": c.view_dependent(features) if features else "",
                # 항목별 연속 점수 0~100 (`Criterion.score_for`). 레이더 차트의
                # 축 값이다. 🔴 **총점은 여기서 나오지 않는다** — 위 grade의
                # 가중합이고, 이 값은 features를 안 주면 None일 뿐 나머지는
                # 한 비트도 같다. out_of_band와 같은 성질이다.
                "stat": c.score_for(features) if features else None,
                "evidence": j.get("evidence", ""),
                "metric_ref": j.get("metric_ref", ""),
            }
        )

    skipped = [
        {"criterion_id": c.id, "name": c.name, "weight": c.weight}
        for c in rubric.criteria
        if c.id not in judgments
    ]

    score = round(ratio * 100)
    return {
        "score": score,
        "grade": _band(score, rubric.grade_bands),
        # 선수에게 보여줄 두 문장 이내 요약 (계약 3장 4 · 미결 `paik` 7번).
        # 🔴 `score`·`grade` 와 **무관하게** breakdown 에서만 짓는다 — 이 키를
        # 빼도 점수는 한 비트도 안 바뀐다. `stat`·`out_of_band` 와 같은 성질이라
        # B-6 재실행을 부르지 않는다.
        "summary": summarize(breakdown),
        # 추천 카드의 설명 칸 (`paik` 27번). `summary` 와 같은 성질이다 —
        # breakdown 에서만 짓고 점수를 안 건드린다.
        "card": card(breakdown, rubric, features),
        "breakdown": breakdown,
        # 측정하지 못해 판정에서 빠진 항목 — 0점이 아니라 제외다.
        "skipped": skipped,
        "rubric_version": rubric.version,
        "pipeline_version": rubric.pipeline_version,
        # 🔴 **검수되지 않은 루브릭으로 낸 값**이라는 표시. 2026.09.17에
        # 지도자 검수 없이 가기로 해서(미결 2번) **이 값이 영구히 true 다.**
        # 앞서 여기 «대외 노출하지 않는다»고 적어 둔 것을 정정한다 — 노출하고
        # 있고, 막는 대신 이 표시로 말한다. `review_required` 를 false 로
        # 바꾸지 않는다: 화면의 「검수 전」 배지가 이 값을 그린다.
        "provisional": rubric.review_required,
    }


def _band(score: int, bands: dict[str, int]) -> str:
    for label, floor in sorted(bands.items(), key=lambda kv: kv[1], reverse=True):
        if score >= floor:
            return label
    return min(bands, key=lambda k: bands[k])
