"""Phase A 평가 자산의 위치를 한 곳에서 정한다.

**왜 있는가.** 평가 스크립트 14개가 `ROOT = Path("/mnt/d/supersub-phaseA")`를
각자 하드코딩하고 있었다(미결 14번). 그래서

- 다른 기계에서는 아무것도 안 돌고,
- 저장소에 사본을 떠 두어도 **읽히지 않았다** — 미결 11번이 "읽히지 않는
  백업"이라고 적어 둔 그 상태이고, 실제 사고로 이어졌다(2026-09-02: 평가
  스크립트가 `/mnt/d`의 낡은 코드를 import 해 라벨 재매핑이 빠진 채 B-1/B-2가
  돌았고, 예외도 경고도 없이 숫자만 달랐다).

**동작점을 이름에 드러낸다.** `cache/`가 아니라 `cache_target15/`·
`cache_target30/`다. 어느 fps인지 이름으로 보이지 않으면 섞어 쓰게 되고,
그것이 미결 10번(서비스와 평가가 target_fps를 서로 다르게 얻는다)의 형태다.
**기본값을 두지 않고 호출자가 고르게 한다.**

  from paths import cache_dir, candidates_dir, external_root

  cache_dir(30)            # 저장소 사본. 없으면 외부에서 찾는다
  candidates_dir(15)
  external_root()          # clips/·frames/·labeling/ — 저장소에 없는 것들

**저장소에 있는 것과 없는 것.**

| 자산 | 어디 |
|---|---|
| `cache_target{15,30}/` (1.3MB / 2.4MB) | **저장소** |
| `candidates_target{15,30}/` (652KB / 2.2MB) | **저장소** |
| `clips/*.mp4` (130MB) | `/mnt/d` 뿐 — 크기 때문에 저장소에 넣지 않는다 |
| `frames/`, `labeling/renders/` (31MB) | `/mnt/d` 뿐 |

외부 경로는 `SUPERSUB_PHASEA_ROOT`로 바꿀 수 있다.
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: 저장소에 들어와 있는 동작점들. 새 동작점을 뜨면 여기 더한다.
TARGETS = (15, 30)

_DEFAULT_EXTERNAL = Path("/mnt/d/supersub-phaseA")


def external_root() -> Path:
    """저장소에 넣지 못한 큰 자산(clips·frames·labeling)의 뿌리.

    `SUPERSUB_PHASEA_ROOT`로 바꾼다. **존재를 보장하지 않는다** —
    쓰는 쪽에서 `require_external()`로 확인할 것.
    """
    return Path(os.environ.get("SUPERSUB_PHASEA_ROOT", _DEFAULT_EXTERNAL))


def require_external(what: str = "") -> Path:
    """외부 자산이 실제로 있을 때만 경로를 준다. 없으면 왜 없는지 말해 준다."""
    root = external_root()
    if not root.is_dir():
        raise FileNotFoundError(
            f"Phase A 외부 자산을 찾을 수 없다: {root}\n"
            f"{'필요한 것: ' + what if what else ''}\n"
            "clips/·frames/·labeling/ 은 크기 때문에 저장소에 없다(미결 11번).\n"
            "다른 위치에 있으면 SUPERSUB_PHASEA_ROOT 로 알려줄 것."
        )
    return root


def _resolve(kind: str, target: int) -> Path:
    if target not in TARGETS:
        raise ValueError(f"target 은 {TARGETS} 중 하나여야 한다: {target!r}")
    repo = HERE / f"{kind}_target{target}"
    if repo.is_dir():
        return repo
    # 저장소에 없으면 외부를 본다. 외부는 동작점 구분이 없으므로(마지막 실행이
    # 덮어쓴다) **무엇을 읽고 있는지 알 수 없다** — 그래서 저장소를 먼저 본다.
    ext = external_root() / kind
    if ext.is_dir():
        return ext
    raise FileNotFoundError(
        f"{kind}_target{target} 를 저장소({repo})에서도 외부({ext})에서도 찾지 못했다."
    )


def cache_dir(target: int) -> Path:
    """포즈 추출 캐시(`*.npz`, keypoints 포함)."""
    return _resolve("cache", target)


def candidates_dir(target: int) -> Path:
    """사람 검출 후보(`*.npz`, boxes 포함)."""
    return _resolve("candidates", target)


def clip_ids(target: int = 30) -> list[str]:
    """캐시에 들어 있는 클립 id 목록 (정렬)."""
    return sorted(p.stem for p in cache_dir(target).glob("*.npz") if ".ERROR" not in p.name)
