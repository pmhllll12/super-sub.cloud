#!/usr/bin/env python3
"""`jekyll build|serve` 가 **엉뚱한 폴더를 소스로** 잡는 것을 막는다.

## 무엇을 막는가

jekyll 은 **현재 디렉터리를 소스로** 삼는다. `agent/` 에서 돌리면 `agent/` 에
`_config.yml` 이 없는데도 **에러가 안 난다** — bundler 가 `Gemfile` 을 찾아
위로 올라가기 때문이다. 그래서 jekyll 은 `agent/.venv` 를 `agent/_site` 로
복사하기 시작하고 **7.8GB** 가 쌓인 뒤 멈춘다. 2026-09-11 에 두 번,
2026-09-14 에 두 번 겪었다.

🔴 **`.gitignore` 는 이것을 안 막는다.** `_site` 가 깊이 무관 패턴이라 커밋에는
안 들어가지만 **디스크와 시간은 그대로 나간다.**

## 어떻게 막는가 — 막지 않고 **고쳐서** 통과시킨다

`--source`·`--destination` 을 저장소 루트로 박아 준다. 절대경로라 **어느 cwd
에서 돌려도 결과가 같다.** 사람이 기억할 것이 없어지는 것이 핵심이다.

🔴 **막는 설계 둘이 먼저 실패했다. 되살리지 말 것.**

- **「명령문에 `cd <루트>` 를 요구」** — 하네스가 선두 `cd <루트>` 를 명령에서
  **떼어내** 작업 디렉터리로 옮긴다. 훅이 받는 `tool_input.command` 에는 그
  `cd` 가 **없다.** 만족 불가능한 조건이라 올바른 빌드까지 전부 막힌다.
- **「payload 의 `cwd` 로 판별」** — `cwd` 는 **언제나 프로젝트 루트**로 온다.
  Bash 툴이 실제로 쓰는 셸의 cwd 가 아니라서 판별에 못 쓴다.

**그래서 위치를 알아내려 하지 않는다. 위치에 안 기대게 만든다.**

## 건드리지 않는 경우

- `-s`/`--source` 를 이미 준 명령 — 사람이 정한 것을 덮지 않는다.
  🔴 `demo/`(별개 Jekyll 사이트)를 빌드하려면 `--source <...>/demo` 를 주면 된다
- 저장소 루트에 `_config.yml` 이 없는 경우 — 이 저장소가 아니면 손대지 않는다
- `grep`·`echo` 처럼 **글자로만 언급**한 명령 — 명령 자리에서 시작하는 호출만 본다
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# 명령 자리에서 시작하는 호출만 잡는다. 앞이 줄머리이거나 `;`·`&`·`|` 여야
# 하므로 `grep "jekyll build" CLAUDE.md` 처럼 인용부호 안에 든 것은 안 걸린다.
INVOCATION = re.compile(r"(^|[;&|\n])(\s*(?:bundle\s+exec\s+)?jekyll\s+(?:build|serve))")
ALREADY_SET = re.compile(r"(^|\s)(-s|--source)(\s|=)")


def repo_root(cwd: str) -> str | None:
    """저장소 루트. Jekyll 소스 루트가 저장소 루트 자체다 (루트 CLAUDE.md)."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    root = out.stdout.strip() if out.returncode == 0 else ""
    # `_config.yml` 이 있어야 Jekyll 소스 루트다. 없으면 다른 저장소이므로
    # 손대지 않는다 — 남의 빌드를 조용히 바꾸는 것이 더 나쁘다.
    return root if root and os.path.isfile(os.path.join(root, "_config.yml")) else None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                      # payload 를 못 읽으면 아무것도 하지 않는다

    tool_input = data.get("tool_input", {})
    cmd = tool_input.get("command", "")
    if not INVOCATION.search(cmd) or ALREADY_SET.search(cmd):
        return 0

    root = repo_root(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    if not root:
        return 0

    flags = f' --source "{root}" --destination "{root}/_site"'
    new = INVOCATION.sub(lambda m: m.group(1) + m.group(2) + flags, cmd)
    if new == cmd:
        return 0

    updated = dict(tool_input)
    updated["command"] = new
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": updated,
            "permissionDecisionReason": (
                "jekyll 의 source/destination 을 저장소 루트로 박았다 — "
                "하위 폴더에서 돌면 .venv 까지 복사해 ~8GB 를 쓴다."
            ),
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
