"""기준선 환경 가드가 **실제로 막는지** (미결 47번).

47번은 「적어 두면 알 수 있다」로는 안 막혔다 — 계기가 환경을 적고 있었어도
**틀린 환경에서 그대로 돌아** 숫자가 나왔고, 그 숫자는 맞는 숫자와 생김새가
같았다. 그래서 가드를 뒀고, 그 가드가 **정말 멈추는지**를 여기서 잰다.

🔴 **이 검사는 지금 이 기계에 `torchvision` 이 깔려 있는지를 묻지 않는다.**
그것까지 걸면 제품 설치(EC2 는 `--extra aws` 만 깐다)에서 늘 깨진다 —
**무엇이 맞는 환경인가는 미결 49번에서 정한다.** 여기서 지키는 것은 「어긋나면
멈춘다」는 성질 하나다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval/phaseA"))

import env_guard  # noqa: E402


def test_a_matching_environment_passes() -> None:
    assert env_guard.drifted({"a": True}, {"a": True}) == []


def test_a_drifted_environment_is_named_not_just_flagged() -> None:
    """무엇이 어떻게 다른지가 메시지에 있어야 고칠 수 있다."""
    out = env_guard.drifted({"transformers_sees_torchvision": True},
                            {"transformers_sees_torchvision": False})
    assert len(out) == 1
    assert "transformers_sees_torchvision" in out[0]
    assert "True" in out[0] and "False" in out[0]


def test_a_missing_key_counts_as_drift() -> None:
    """환경을 못 읽은 것은 「같다」가 아니다."""
    assert env_guard.drifted({"a": True}, {}) != []


def test_preflight_stops_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(env_guard.DRIFT_ENV_VAR, raising=False)
    monkeypatch.setattr(env_guard, "current_env",
                        lambda: {"transformers_sees_torchvision": False})
    with pytest.raises(SystemExit) as caught:
        env_guard.preflight("시험")
    message = str(caught.value)
    # 멈추기만 하고 왜인지 안 알려 주면 다음 사람이 또 다섯 회차를 쓴다.
    assert "47" in message and "uv sync --all-extras" in message


def test_an_intentional_comparison_round_can_proceed_after_saying_so(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """일부러 다른 환경에서 재는 회차(S0 대 S1 같은)는 막지 않는다 — 밝히면."""
    monkeypatch.setenv(env_guard.DRIFT_ENV_VAR, "1")
    monkeypatch.setattr(env_guard, "current_env",
                        lambda: {"transformers_sees_torchvision": False})
    assert env_guard.preflight("시험") != []   # 진행하되 어긋남을 돌려준다


def test_the_baseline_claim_is_the_one_the_fifth_round_measured() -> None:
    """기준선 환경은 **재서 알아낸 사실**이다 — 바꾸려면 다시 재야 한다."""
    assert env_guard.BASELINE_ENV == {"transformers_sees_torchvision": True}
