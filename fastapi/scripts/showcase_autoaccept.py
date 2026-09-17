"""시연용 더미 계정이 받은 요청을 **3초 안팎으로 자동 수락**한다 (2026-09-17).

`seed_showcase.py` 로 넣은 더미(`showcase-NN@super-sub.example`)는 사람이 아니라서, 시연 중
지인 신청·팀 초대·경기 제안을 보내면 답이 영영 안 온다. 이 프로세스가 대신 누른다.

무엇을 수락하나 — **더미가 받는 쪽**인 것만:

| 요청 | 찾는 곳 | 누르는 경로(더미로 로그인해서) |
|---|---|---|
| 지인 신청 | `user_contact` 대상이 더미, `accepted_at` 없음 | `POST /me/contacts/{id}/accept` |
| 팀 초대 | `team_invitation` 받은 사람이 더미, `pending` | `POST /me/invitations/{id}/accept` |
| 경기 제안(주장이 더미를 부름) | `match_application` 더미, 팀 쪽만 수락됨 | `POST /matches/{m}/applications/{id}/accept` |
| 팀 대 팀 경기 신청 | `team_match_request` 대상 팀 주장이 더미, `pending` | `POST /teams/{t}/match-requests/{id}/accept` |

🔴 **찾기만 DB 로 하고 수락은 API 로 한다.** 수락 규칙(권한·중복·알림 만들기)은 API 뒤의
코드에 있다 — DB 를 직접 고치면 알림이 안 생기고 규칙을 비껴간다. 확인할 목록을 주는
사용자용 API 가 없는 것(경기 제안)도 있어서 찾는 쪽은 DB 다.

「3초」는 **처음 본 순간부터** 잰다(경기 지원 행에는 생성 시각이 없다). 2~4초 사이로 흔들어
사람이 누른 것처럼 보이게 한다. 로그인은 수락할 일이 생긴 더미만 하고 토큰을 재사용한다 —
로그인 경로에 요청 제한(주소당 분당 10회)이 걸려 있다.

    SHOWCASE_PASSWORD=... .venv/bin/python scripts/showcase_autoaccept.py \\
        --api http://127.0.0.1:8000/api/v1

끄려면 Ctrl+C(또는 프로세스 종료). 더미 비밀번호는 `seed_showcase.py` 에 준 것과 같아야 한다.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from uuid import UUID

# 🔴 Python 3.14 는 표준입력 실행에도 `__file__ = "<stdin>"` 을 채운다 — 확장자·실재로 가른다.
_here = Path(globals().get("__file__", ""))
# `resolve()` 가 아니라 `absolute()` — k8s ConfigMap 으로 넣은 파일은 심볼릭 링크라 resolve 하면
# `..data` 안쪽으로 따라 들어가 두 단계 위가 app 이 아니게 된다.
ROOT = _here.absolute().parent.parent if _here.suffix == ".py" and _here.is_file() else Path.cwd()
sys.path.insert(0, str(ROOT))

from sqlalchemy import and_, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import Base, engine_or_none  # noqa: E402

for orm_file in sorted((ROOT / "app").glob("*/adapter/outbound/orm/*_orm.py")):
    importlib.import_module(".".join(orm_file.relative_to(ROOT).with_suffix("").parts))
T = Base.metadata.tables

EMAIL_PREFIX = "showcase-"
EMAIL_DOMAIN = "@super-sub.example"


def log(msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {msg}", flush=True)


class Api:
    """더미별 토큰을 들고 API 를 부른다. 401 이면 한 번 다시 로그인한다."""

    def __init__(self, base: str, password: str) -> None:
        self.base = base.rstrip("/")
        self.password = password
        self.tokens: dict[str, str] = {}

    def _call(self, method: str, path: str, body: dict | None, token: str | None) -> tuple[int, dict | None]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("content-type", "application/json")
        if token:
            req.add_header("authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                raw = res.read()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            raw = err.read()
            try:
                return err.code, json.loads(raw) if raw else None
            except ValueError:
                return err.code, None

    def _login(self, email: str) -> str | None:
        status, body = self._call("POST", "/auth/login", {"email": email, "password": self.password}, None)
        if status != 200 or not body:
            code = (body or {}).get("error", {}).get("code")
            log(f"로그인 실패 {email} — {status} {code}")
            return None
        self.tokens[email] = body["access_token"]
        return self.tokens[email]

    def post_as(self, email: str, path: str) -> tuple[int, str | None]:
        token = self.tokens.get(email) or self._login(email)
        if token is None:
            return 0, "LOGIN_FAILED"
        status, body = self._call("POST", path, {}, token)
        if status == 401:
            token = self._login(email)
            if token is None:
                return 0, "LOGIN_FAILED"
            status, body = self._call("POST", path, {}, token)
        code = (body or {}).get("error", {}).get("code") if isinstance(body, dict) else None
        return status, code


def pending(session: Session, dummies: dict[UUID, tuple[str, str]]) -> list[tuple[str, str, str]]:
    """(키, 더미 이메일, 수락 경로, 설명) — 지금 답을 기다리는 것들."""
    ids = list(dummies)
    out = []
    c = T["user_contact"]
    for cid, requester, target in session.execute(
        select(c.c.id, c.c.requester_user_id, c.c.target_user_id)
        .where(c.c.target_user_id.in_(ids), c.c.accepted_at.is_(None))
    ).all():
        out.append((f"contact:{cid}", dummies[target][0], f"/me/contacts/{cid}/accept",
                    f"지인 신청 → {dummies[target][1]}"))
    inv = T["team_invitation"]
    for iid, invited in session.execute(
        select(inv.c.id, inv.c.invited_user_id)
        .where(inv.c.invited_user_id.in_(ids), inv.c.status == "pending")
    ).all():
        out.append((f"invitation:{iid}", dummies[invited][0], f"/me/invitations/{iid}/accept",
                    f"팀 초대 → {dummies[invited][1]}"))
    app = T["match_application"]
    for aid, mid, uid in session.execute(
        select(app.c.id, app.c.match_id, app.c.user_id).where(
            app.c.user_id.in_(ids), app.c.team_accepted_at.is_not(None), app.c.user_accepted_at.is_(None))
    ).all():
        out.append((f"application:{aid}", dummies[uid][0], f"/matches/{mid}/applications/{aid}/accept",
                    f"경기 제안 → {dummies[uid][1]}"))
    req, tm = T["team_match_request"], T["team_member"]
    for rid, team_id, captain in session.execute(
        select(req.c.id, req.c.target_team_id, tm.c.user_id)
        .select_from(req.join(tm, and_(tm.c.team_id == req.c.target_team_id,
                                        tm.c.role == "owner", tm.c.left_at.is_(None))))  # 주장 역할 값은 "owner"
        .where(tm.c.user_id.in_(ids), req.c.status == "pending")
    ).all():
        out.append((f"match_request:{rid}", dummies[captain][0],
                    f"/teams/{team_id}/match-requests/{rid}/accept", f"팀 경기 신청 → {dummies[captain][1]}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--api", default="http://127.0.0.1:8000/api/v1", help="API 주소(/api/v1 까지)")
    ap.add_argument("--interval", type=float, default=1.0, help="DB 를 보는 간격(초)")
    ap.add_argument("--min-delay", type=float, default=2.0)
    ap.add_argument("--max-delay", type=float, default=4.0)
    args = ap.parse_args()

    password = os.environ.get("SHOWCASE_PASSWORD", "")
    if not password:
        print("SHOWCASE_PASSWORD 를 환경변수로 준다(seed_showcase.py 와 같은 값).", file=sys.stderr)
        return 2
    engine = engine_or_none()
    if engine is None:
        print("DATABASE_URL 이 없다.", file=sys.stderr)
        return 2

    api = Api(args.api, password)
    first_seen: dict[str, float] = {}
    delay: dict[str, float] = {}
    done: set[str] = set()
    dummies: dict[UUID, tuple[str, str]] = {}
    refreshed = 0.0
    log(f"자동 수락 시작 — API {args.api}, {args.min_delay:g}~{args.max_delay:g}초 뒤 수락")

    while True:
        try:
            with Session(engine) as session:
                now = time.monotonic()
                if now - refreshed > 30:
                    u = T["user"]
                    dummies = {uid: (email, nick) for uid, email, nick in session.execute(
                        select(u.c.id, u.c.email, u.c.nickname)
                        .where(u.c.email.like(f"{EMAIL_PREFIX}%{EMAIL_DOMAIN}"))).all()}
                    refreshed = now
                    if not dummies:
                        log("더미가 없다 — seed_showcase.py 를 먼저 돌린다. 30초 뒤 다시 본다.")
                items = pending(session, dummies) if dummies else []
            live = {key for key, *_ in items}
            for key in list(first_seen):  # 사람이 먼저 처리했거나 사라진 것은 잊는다
                if key not in live:
                    first_seen.pop(key, None)
                    delay.pop(key, None)
            for key, email, path, what in items:
                if key in done:
                    continue
                if key not in first_seen:
                    first_seen[key] = time.monotonic()
                    delay[key] = random.uniform(args.min_delay, args.max_delay)
                    continue
                if time.monotonic() - first_seen[key] < delay[key]:
                    continue
                status, code = api.post_as(email, path)
                if 200 <= status < 300:
                    log(f"수락: {what} ({time.monotonic() - first_seen[key]:.1f}초)")
                    done.add(key)
                elif status in (403, 404, 409, 422):
                    log(f"건너뜀: {what} — {status} {code}")
                    done.add(key)
                else:  # 일시적 실패는 5초 뒤 다시
                    log(f"실패, 다시 시도: {what} — {status} {code}")
                    first_seen[key] = time.monotonic()
                    delay[key] = 5.0
        except KeyboardInterrupt:
            log("끝")
            return 0
        except Exception as exc:  # DB·네트워크가 잠깐 끊겨도 프로세스는 살아 있는다
            log(f"오류: {type(exc).__name__}: {exc}")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            log("끝")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
