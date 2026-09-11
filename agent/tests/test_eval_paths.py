"""평가 스크립트에 **기계별 경로가 박히지 못하게** (미결 14번).

🔴 **여기 있는 검사는 지우면 안 된다.** 막고 있는 것은 이것이다:

경로를 박으면 (1) 다른 기계에서 아무것도 안 돌고 (2) 저장소에 사본을 떠 두어도
**읽히지 않는다.** 그 상태가 실제 사고로 이어졌다 — 2026-09-02에 평가 스크립트가
`/mnt/d` 의 낡은 코드를 import 해 라벨 재매핑이 빠진 채 B-1/B-2 가 돌았고,
**예외도 경고도 없이 숫자만 달랐다**(selector A 70.9% 대 70.1%).

그래서 「어디서 읽는가」는 `eval/phaseA/paths.py` 한 곳에서 정한다. 이 검사는
그 규칙이 **다음에 스크립트를 하나 더할 때** 지켜지는지를 본다 — 사람이 기억할
일로 두면 새 파일이 `Path("/mnt/d/...")` 로 시작한다.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 기계에 매인 접두사. 이걸 코드에 박으면 그 기계에서만 돈다.
MACHINE = ("/mnt/", "/home/", "C:", "D:/", "D:\\")

#: 🔴 **예외는 이유와 함께만 늘어난다.** 「돌리려니 걸려서」는 이유가 아니다.
ALLOWED = {
    # 외부 자산 뿌리의 **기본값을 선언하는 자리**다. 여기 한 곳에 있어야 나머지가
    # 이 모듈을 부를 수 있고, `SUPERSUB_PHASEA_ROOT` 로 덮을 수 있다.
    "eval/phaseA/paths.py",
    # 데이터셋 기본 위치. 같은 성질이고 `SUPERSUB_3DSP_ROOT` 로 덮는다.
    "eval/dataset_3dsp/probe_3dsp.py",
    # 🔴 **라벨 파일에 적히는 출처 표기다** — 코드 경로가 아니라 **기록**이다.
    # 바꾸면 그 라벨이 어디서 왔는지를 잘못 적는 것이 된다(labeling/labels.json
    # 은 수정 금지 자산이다).
    "eval/phaseA/labeling/label_cli.py",
    "eval/phaseA/labeling/set_labels.py",
    # 명세가 정한 데이터셋 기본 위치(`D:/sports_dataset`, `SPORTS_DATASET_ROOT`
    # 로 덮는다)와 **WSL 경로 번역 그 자체**(`/mnt/<드라이브>`)가 여기 있다.
    # 번역이 없으면 윈도우 표기가 저장소 안에 `D:` 폴더를 만든다.
    "scripts/dataset_pipeline/config.py",
}


def _docstring_ids(tree: ast.AST) -> set[int]:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                out.add(id(first.value))
    return out


def _offenders(folders: tuple[str, ...]) -> list[str]:
    """주석·독스트링은 세지 않는다 — 거기 적힌 경로는 설명이다."""
    bad: list[str] = []
    for folder in folders:
        for f in sorted((ROOT / folder).rglob("*.py")):
            rel = f.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or rel in ALLOWED:
                continue
            tree = ast.parse(f.read_text(encoding="utf-8"))
            docs = _docstring_ids(tree)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and id(node) not in docs
                        and node.value.startswith(MACHINE)):
                    bad.append(f"{rel}:{node.lineno}  {node.value}")
    return bad


def test_eval_scripts_do_not_hardcode_a_machine_path():
    """🔴 `eval/` 의 데이터 경로는 `paths.py` 가 정한다.

    걸렸다면 고치는 방법은 하나다 — `from paths import external_root` 로 받아
    쓴다(같은 폴더가 아니면 `sys.path` 에 `eval/phaseA` 를 넣는다). **예외
    목록에 추가하는 것은 답이 아니다**: 그러면 다음 사람이 그 줄을 보고 새
    스크립트에도 경로를 박는다.
    """
    bad = _offenders(("eval",))
    assert not bad, (
        "🔴 기계별 경로가 코드에 박혀 있다 (미결 14번):\n  " + "\n  ".join(bad)
        + "\n\n`eval/phaseA/paths.py` 의 external_root() 를 쓸 것. 박아 두면 다른 "
          "기계에서 안 돌고, 저장소 사본을 떠도 읽히지 않는다 — 2026-09-02에 그 "
          "상태로 B-1/B-2 가 낡은 코드로 돌았고 숫자만 달랐다."
    )


def test_production_and_scripts_never_name_a_machine_path():
    """서비스 코드는 아예 예외가 없다 — 배포되는 것이기 때문이다."""
    bad = _offenders(("src", "scripts"))
    assert not bad, (
        "🔴 서비스·CLI 코드에 기계별 경로가 있다:\n  " + "\n  ".join(bad)
        + "\n\n설정(환경변수·인자)으로 받을 것."
    )
