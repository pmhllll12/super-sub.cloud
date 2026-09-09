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
    titles: dict[int, str] = field(default_factory=dict)
    # 등급 판정 구간. band_metric 하나의 값으로 등급이 결정된다.
    band_metric: str = ""
    bands: dict[int, tuple[Interval, ...]] = field(default_factory=dict)

    def title_for(self, grade: int) -> str:
        """해당 등급의 칭호. 정의되지 않았으면 항목명으로 대체한다."""
        return self.titles.get(grade) or self.name

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
    # 임팩트를 정의할 사지 — "leg"(축구 슈팅) 또는 "arm"(농구 슛·야구 투구).
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
                titles={int(k): v for k, v in (entry.get("titles") or {}).items()},
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


def aggregate(
    judgments: dict[str, dict[str, Any]],
    rubric: Rubric,
    expected_ids: Iterable[str] | None = None,
    features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """항목별 판정을 총점으로 합산한다.

    judgments: {criterion_id: {"grade": int, "evidence": str, "metric_ref": str}}

    `features`를 주면 0등급이 **구간 위에서** 왔는지를 `out_of_band`로 표시한다
    (미결 20번). 🔴 **점수는 그것과 무관하다** — 안 주면 그 필드가 빈 문자열일
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
                "title": c.title_for(grade),
                "band": c.band_text(grade),
                # 🔴 이 0등급이 **구간 위에서** 왔는가 (미결 20번). 점수는 안
                # 바뀐다 — 「쟀는데 못했다」와 「구간 밖이다」를 화면이 가를 수
                # 있게 하는 표시일 뿐이다. features 를 안 주면 빈 문자열이다.
                "out_of_band": c.out_of_band(features) if features else "",
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
        "breakdown": breakdown,
        # 측정하지 못해 판정에서 빠진 항목 — 0점이 아니라 제외다.
        "skipped": skipped,
        "rubric_version": rubric.version,
        "pipeline_version": rubric.pipeline_version,
        # 검수 전 루브릭으로 낸 점수는 대외 노출하지 않는다.
        "provisional": rubric.review_required,
    }


def _band(score: int, bands: dict[str, int]) -> str:
    for label, floor in sorted(bands.items(), key=lambda kv: kv[1], reverse=True):
        if score >= floor:
            return label
    return min(bands, key=lambda k: bands[k])
