"""계층·컨텍스트 경계를 실제로 검사한다.

구조는 주석으로 적어 두면 반드시 무너진다. **여기서 임포트를 직접 읽어서 막는다.**

참고한 저장소(anjgkwl.com/fastapi)는 `setup.cfg` 에 import-linter 규칙을 적어 뒀지만
규칙이 `apps.login` 을 가리키는데 실제 임포트는 `login.*` 이었고(`main.py` 가 `apps/` 를
`sys.path` 에 넣는다) `lint-imports` 도 설치돼 있지 않았다. **적어만 두고 안 도는 규칙은
없느니만 못하다** — 그래서 여기는 pytest 로 돌린다.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"
CONTEXTS = ("user", "card")

# 컨텍스트에 속하지 않는 공용 모듈은 전부 `app/core/` 아래에 둔다.
#
# 예전에는 이름을 하나씩 적은 집합이었다. 그러면 **공용 파일을 추가할 때마다 목록을
# 손으로 늘려야 하고, 까먹는 순간 그 파일은 검사에서 조용히 빠진다.** 통과와 구별이
# 안 되는 검사가 된다. 디렉터리로 규칙을 정하면 새 파일이 자동으로 포함된다.
CORE = APP / "core"

# 유일하게 허용된 컨텍스트 간 임포트. 스텁끼리라 DB 가 붙으면 함께 사라진다.
STUB_CROSS_IMPORT = "app/card/adapter/outbound/stub/card_stub_repository.py"


def _modules(path: Path) -> list[str]:
    """이 파일이 임포트하는 모듈 이름을 전부 뽑는다."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def _sources() -> list[tuple[str, Path]]:
    return [
        (str(p.relative_to(APP.parent)).replace("\\", "/"), p)
        for p in sorted(APP.rglob("*.py"))
        if "__pycache__" not in p.parts
    ]


class TestLayering:
    def test_인바운드는_도메인_엔티티와_규칙을_모른다(self):
        """라우터·스키마가 엔티티를 다루면 계층이 무너진다.

        값 객체의 **정책 상수**(비밀번호 최소 길이 등)는 예외로 허용한다.
        스키마가 그것을 직접 들고 있으면 도메인과 값이 갈라지기 때문이다.
        """
        offenders = []
        for rel, path in _sources():
            if "/adapter/inbound/" not in rel:
                continue
            for mod in _modules(path):
                if ".domain.entities" in mod or ".domain.rules" in mod:
                    offenders.append(f"{rel} → {mod}")
        assert not offenders, "인바운드가 도메인을 뚫고 들어갔다:\n  " + "\n  ".join(offenders)

    def test_도메인은_프레임워크와_바깥_계층을_모른다(self):
        offenders = []
        for rel, path in _sources():
            if "/domain/" not in rel:
                continue
            for mod in _modules(path):
                bad = (
                    mod.startswith("fastapi")
                    or mod.startswith("pydantic")
                    or mod.startswith("sqlalchemy")
                    or ".application" in mod
                    or ".adapter" in mod
                )
                if bad:
                    offenders.append(f"{rel} → {mod}")
        assert not offenders, "도메인이 바깥을 임포트했다:\n  " + "\n  ".join(offenders)

    def test_애플리케이션은_어댑터와_HTTP를_모른다(self):
        offenders = []
        for rel, path in _sources():
            if "/application/" not in rel:
                continue
            for mod in _modules(path):
                if mod.startswith("fastapi") or ".adapter" in mod:
                    offenders.append(f"{rel} → {mod}")
        assert not offenders, "애플리케이션이 어댑터·HTTP를 임포트했다:\n  " + "\n  ".join(
            offenders
        )

    def test_포트는_추상클래스다(self):
        """포트가 구체 클래스가 되면 갈아끼울 수 없다."""
        from app.card.application.ports.output.card_port import CardPort
        from app.user.application.ports.output.user_port import UserPort

        for port in (UserPort, CardPort):
            assert getattr(port, "__abstractmethods__", None), f"{port.__name__} 이 추상이 아니다"


class TestContextBoundary:
    def test_컨텍스트끼리_직접_임포트하지_않는다(self):
        """`user` 와 `card` 는 서로를 모른다.

        걸치는 관심사(인증)는 `app/security.py` 로 빼서 양쪽이 그것만 보게 한다.
        """
        offenders = []
        for rel, path in _sources():
            here = next((c for c in CONTEXTS if rel.startswith(f"app/{c}/")), None)
            if here is None or rel == STUB_CROSS_IMPORT:
                continue
            for mod in _modules(path):
                other = next(
                    (c for c in CONTEXTS if c != here and mod.startswith(f"app.{c}.")),
                    None,
                )
                if other:
                    offenders.append(f"{rel} → {mod}")
        assert not offenders, "컨텍스트끼리 직접 얽혔다:\n  " + "\n  ".join(offenders)

    def test_허용된_예외는_스텁_하나뿐이다(self):
        """예외가 늘어나면 여기서 알아차린다."""
        path = APP.parent / STUB_CROSS_IMPORT
        assert path.exists(), "예외 파일이 사라졌으면 이 테스트도 지운다"

        cross = [m for m in _modules(path) if m.startswith("app.user.")]
        assert cross == [
            "app.user.adapter.outbound.stub.user_stub_repository"
        ], "스텁의 컨텍스트 간 임포트가 늘었다"


class TestSharedModules:
    def test_공용_모듈은_컨텍스트를_모른다(self):
        """`app/core/security.py` 같은 공용이 특정 컨텍스트를 알면 공용이 아니다."""
        offenders = []
        for path in sorted(CORE.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = str(path.relative_to(APP.parent)).replace("\\", "/")
            for mod in _modules(path):
                if any(mod.startswith(f"app.{c}.") for c in CONTEXTS):
                    offenders.append(f"{rel} → {mod}")
        assert not offenders, "공용 모듈이 컨텍스트를 임포트했다:\n  " + "\n  ".join(offenders)

    def test_app_루트에는_컨텍스트와_main_만_둔다(self):
        """공용 모듈이 루트로 흩어지면 `app/` 이 컨텍스트와 공용을 겸하게 된다.

        위 규칙(`app/core/` 아래는 전부 공용)이 성립하려면 **루트에 공용이 없어야**
        한다. 루트에 새로 만들면 어느 검사에도 안 걸리므로 여기서 막는다.
        """
        allowed = {"__init__.py", "main.py"}
        strays = sorted(p.name for p in APP.glob("*.py") if p.name not in allowed)
        assert not strays, (
            "공용 모듈은 app/core/ 에 둔다. 루트에 남은 파일:\n  " + "\n  ".join(strays)
        )
