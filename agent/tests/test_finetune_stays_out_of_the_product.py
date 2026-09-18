"""파인튜닝 회차가 **제품 경로에 새어들지 않게** 막는다 (미결 23번 ④).

🔴 **사용자 지시 (2026-09-18)**: 「이 파인튜닝은 완성되기 전까지 에이전트에
관여하지 말게 한다.」 사전 등록에 「어댑터를 배포 경로에 붙이지 않는다」고
적어 두긴 했지만, **문서에 적은 금지는 다음 세션이 안 읽으면 없는 것과
같다.** 그래서 검사로 둔다.

지금 지키는 것 셋:

1. `src/`·`scripts/`·`deploy/` 어디에도 어댑터·LoRA 이야기가 없다
2. 에이전트 의존성에 학습 패키지(`peft`·`trl`)가 없다 — 들어오면 vLLM 쪽
   torch 가 깨진 전례가 있다 (README 5-2)
3. 구운 어댑터가 **git 에 실리지 않는다** — 실리면 배포 동기화를 타고
   조용히 서버로 간다

이 검사가 **깨져야 하는 때**: 파인튜닝이 채택되어 제품에 넣기로 결정한
때다. 그때는 이 파일을 지우는 것이 아니라 **미결 23번에 결정을 적고** 함께
고친다 — 그래야 「왜 금지가 풀렸는가」가 남는다.

`test_deploy_paths.py`(서빙 모델 이름)와 짝이다: 그쪽은 **다른 모델을 서빙하는
것**을, 이쪽은 **다른 가중치가 얹히는 것**을 막는다.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

AGENT = Path(__file__).resolve().parents[1]
PRODUCT = ("src", "scripts", "deploy")
FORBIDDEN = ("pending23_finetune", "adapter.pt", "LoRALinear", "enable-lora",
             "enable_lora")


def _product_files() -> list[Path]:
    out = []
    for folder in PRODUCT:
        for path in (AGENT / folder).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".sh", ".yaml", ".yml",
                                                  ".env", ".example", ".md"}:
                out.append(path)
    return out


def test_the_product_path_never_mentions_the_adapter() -> None:
    hits = []
    for path in _product_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in FORBIDDEN:
            if word in text:
                hits.append(f"{path.relative_to(AGENT)}: {word}")
    assert not hits, (
        "파인튜닝이 제품 경로에 새어들었다 — 미결 23번 ④ 는 아직 판정도 안 났다:\n"
        + "\n".join(hits))


def test_training_packages_are_not_agent_dependencies() -> None:
    spec = tomllib.loads((AGENT / "pyproject.toml").read_text(encoding="utf-8"))
    project = spec.get("project", {})
    declared = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        declared += list(extra)
    bad = [d for d in declared
           if d.split("[")[0].split(">")[0].split("=")[0].strip().lower()
           in {"peft", "trl"}]
    assert not bad, (
        f"학습 패키지가 에이전트 의존성에 들어왔다: {bad}. "
        "파인튜닝은 별도 경로에서 돈다 (사전 등록 6절)")


def test_a_baked_adapter_cannot_be_committed() -> None:
    """어댑터 파일이 git 에 실릴 수 있으면 배포로 흘러간다."""
    probe = "agent/eval/pending23_finetune/adapter.pt"
    done = subprocess.run(["git", "check-ignore", "-q", probe],
                          cwd=AGENT.parent, capture_output=True)
    if done.returncode == 128:
        pytest.skip("git 저장소가 아니다")
    assert done.returncode == 0, (
        f"{probe} 가 .gitignore 에 안 걸린다 — 구운 어댑터가 커밋될 수 있다")
