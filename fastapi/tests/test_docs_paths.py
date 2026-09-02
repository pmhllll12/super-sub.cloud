"""`docs/` 의 문서가 가리키는 파일 경로가 실재하는지 검사한다.

**없는 파일을 지시하는 문서는 거짓 문서다.** 특히 `client-contract-changes.md` 는
받는 쪽 Claude 가 읽고 **그대로 실행**하는 지시서라, 경로가 낡으면 엉뚱한 파일을
만들거나 "없으니 이미 처리됐나 보다"로 잘못 판정한다.

2026-09-01 에 그 문서의 경로 20건을 손으로 확인했는데, 손으로 하는 확인은 다음
사람이 안 한다. 여기서 돌린다.

## 검사 범위

`docs/*.md` 의 **백틱 안에 든 경로만** 본다. 산문 속 경로는 문장부호가 섞여
오탐이 나고, 백틱은 이 저장소에서 경로를 적는 관례다.

## 기준 디렉터리가 문맥마다 다르다

같은 문서가 `www` 얘기를 하면서 `src/lib/api/client.ts` 로 쓰고, 백엔드 얘기를
하면서 `tests/test_architecture.py` 로 쓴다. 그래서 **저장소 루트 · `fastapi/` ·
`www/` 셋 중 하나에서 찾히면 통과**로 본다.

## 무엇을 경로로 볼 것인가

`application/json` · `GET /me` · `POST /api/v1/videos` 처럼 **경로가 아닌데
슬래시가 든 것**이 많다. 그래서 **알려진 최상위 이름으로 시작하는 것만** 본다 —
목록에 없는 첫 조각은 조용히 건너뛴다. 새 최상위 폴더가 생기면 `_TOP` 에 넣는다.
"""

from __future__ import annotations

import re
from pathlib import Path

FASTAPI = Path(__file__).resolve().parent.parent
REPO = FASTAPI.parent
DOCS = FASTAPI / "docs"

# 경로를 해석할 기준. 문서마다 어느 쪽을 기준으로 쓰는지가 다르다.
_BASES = (REPO, FASTAPI, REPO / "www")

# 이 이름으로 시작할 때만 경로로 본다. `application/json` 같은 것을 걸러낸다.
_TOP = frozenset(
    {
        "fastapi", "www", "flutter", "agent", "jekyll", "assets", "guide",
        "_posts", ".github", "app", "tests", "src", "docs", "scripts",
        "alembic", "goldenset", "public",
    }
)

# 백틱 안, 공백 없이 슬래시를 포함한 것. `/` 로 시작하는 API 경로는 제외한다.
_CANDIDATE = re.compile(r"`([^`\s/][^`\s]*/[^`\s]*)`")


def _looks_like_path(text: str) -> bool:
    return text.split("/")[0] in _TOP


def _exists(rel: str) -> bool:
    """기준 셋 중 하나에서 찾히면 있는 것으로 본다."""
    rel = rel.rstrip("/")
    for base in _BASES:
        target = base / rel
        if target.exists():
            return True
        # `src/app/api/auth/*/route.ts` 같은 와일드카드. 대괄호는 glob 의 문자
        # 클래스와 겹치므로(`[id]` 는 Next.js 의 실제 폴더명이다) `*` 가 있을
        # 때만 glob 으로 간다.
        if "*" in rel:
            try:
                if any(base.glob(rel)):
                    return True
            except (ValueError, OSError):
                pass
    return False


def _collect() -> list[tuple[str, int, str]]:
    found = []
    for doc in sorted(DOCS.glob("*.md")):
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for match in _CANDIDATE.findall(line):
                if _looks_like_path(match):
                    found.append((doc.name, lineno, match))
    return found


class TestDocPaths:
    def test_문서가_가리키는_경로가_실재한다(self):
        missing = [
            f"{doc}:{lineno}  {rel}"
            for doc, lineno, rel in _collect()
            if not _exists(rel)
        ]
        assert not missing, (
            "문서가 없는 파일을 가리킨다 — 받는 쪽이 그대로 실행하면 엉뚱한 곳을 만든다.\n"
            "경로를 고치거나, 파일이 옮겨졌으면 문서를 따라 옮길 것:\n  "
            + "\n  ".join(missing)
        )

    def test_검사할_경로를_실제로_찾고_있다(self):
        """🔴 **이 검사가 없으면 위 검사는 조용히 무의미해질 수 있다.**

        정규식이나 `_TOP` 이 어긋나 후보를 하나도 못 모으면 `missing` 이 빈 리스트가
        되어 **아무것도 안 보고 통과한다.** 통과와 "검사 대상이 0건"을 구별한다.
        """
        collected = _collect()
        assert len(collected) >= 10, (
            f"경로 후보를 {len(collected)}건밖에 못 모았다 — 정규식이나 _TOP 이 "
            "문서 표기와 어긋났을 수 있다"
        )

        docs_with_paths = {doc for doc, _, _ in collected}
        assert "client-contract-changes.md" in docs_with_paths, (
            "받는 쪽이 그대로 실행하는 지시서인데 경로가 하나도 안 잡혔다"
        )
