"""시연용 더미 선수 10명 — 지인 찾기와 AI 추천 판에 뜨게 한다 (2026-09-17).

`seed_demo.py`(데모 계정 하나, 개발 전용)와 달리 **운영 사이트 시연**까지 겨냥한다.
그래서 비밀번호를 코드에 두지 않고, 더미를 한 번에 지울 수 있게 만든다.

무엇을 넣나 — 선수마다:

- 계정(`user` · `user_credential`) — 이메일 `showcase-NN@super-sub.example`
  (`.example` 은 실제로 존재할 수 없는 예약 도메인이라 진짜 사람과 안 겹친다)
- 카드(`player_card`) · 한 줄 소개
- 매칭 조건 — 포지션·지역·가능 시간(`member_match_*`). AI 추천 판의 후보 원자료가
  `member_match_position` 이고, 팀이 시간을 등록했으면 시간이 겹쳐야 한다
- 대표 영상 + 분석 결과(`video` → `analysis_job` → `analysis_metric` →
  `analysis_report`). 추천 판의 등급·불릿이 **대표 영상의 리포트**에서 온다.
  🔴 분석 결과는 **실제 분석이 아니다** — `pipeline_version`·`model_name` 에
  `showcase-dummy` 를 박고, 리포트 요약에 더미라고 적는다

`--contacts-to <이메일>` 을 주면 그 계정에 더미 셋이 지인으로, 셋이 지인 신청(알림
포함)으로 붙는다.

🔴 **영상 파일은 이 스크립트가 올리지 않는다.** `--manifest <경로>` 로 (샘플 파일,
저장소 키) 목록을 받아 따로 올린다 — 안 올리면 목록·등급은 보이고 재생만 안 된다.

    SHOWCASE_PASSWORD=... .venv/bin/python scripts/seed_showcase.py \\
        [--contacts-to me@example.com] [--manifest out.json]
    .venv/bin/python scripts/seed_showcase.py --delete

운영에서 돌릴 때는 `--allow-prod` 가 있어야 한다(실수로 운영 DB 에 쓰지 않게).
이미 더미가 있으면 아무것도 안 하고 멈춘다 — 다시 넣으려면 `--delete` 뒤에 돌린다.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

# 파일로 돌리면 fastapi/ 를, 표준입력으로 흘려 넣으면(운영 파드) 작업 디렉터리를 쓴다.
# 🔴 `"__file__" in globals()` 로 가르지 않는다 — Python 3.14 는 표준입력 실행에도
#    `__file__ = "<stdin>"` 을 채워서 운영 파드에서 경로가 틀렸다(테이블을 못 불러 KeyError).
_here = Path(globals().get("__file__", ""))
# `resolve()` 가 아니라 `absolute()` — k8s ConfigMap 으로 넣은 파일은 심볼릭 링크라 resolve 하면
# `..data` 안쪽으로 따라 들어가 두 단계 위가 app 이 아니게 된다.
ROOT = _here.absolute().parent.parent if _here.suffix == ".py" and _here.is_file() else Path.cwd()
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, insert, or_, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine_or_none  # noqa: E402
from app.core.password import hash_password  # noqa: E402

# 테이블을 metadata 에 올린다 — 컨텍스트마다 ORM 모듈을 전부 불러온다(alembic env 와 같은 방식).
for orm_file in sorted((ROOT / "app").glob("*/adapter/outbound/orm/*_orm.py")):
    importlib.import_module(".".join(orm_file.relative_to(ROOT).with_suffix("").parts))
T = Base.metadata.tables

EMAIL_PREFIX = "showcase-"
EMAIL_DOMAIN = "@super-sub.example"
DUMMY_MARK = "showcase-dummy"

# (닉네임, 포지션들, 지역들, 분석 등급 A~D, 카드 불릿, 한 줄 소개, 샘플 파일, 폭, 높이, 길이ms, 영상 제목)
# 등급은 표시 규칙상 리뷰가 없으면 A→A, D→F 로 보인다(S 는 리뷰가 있어야 나온다).
PLAYERS = [
    ("왼발의마법사", ["FW", "MF"], ["서울 마포구", "서울 서대문구"], "A",
     ["차는 다리를 끝까지 뻗습니다", "디딤발을 공 옆에 정확히 붙입니다"], "왼발 하나로 끝낸다",
     "mixkit-43499.mp4", 1280, 720, 8133, "경기 중 마무리 슛"),
    ("골문지킴이", ["GK"], ["서울 마포구", "서울 은평구"], "A",
     ["공을 끝까지 보고 몸을 던집니다"], "마지막 한 명",
     # 실내 페널티킥(Pexels 6084025)은 운영에서 사람 계정이 이미 올린 영상이라 겹치지 않게 바꿨다
     "mixkit-43501.mp4", 1280, 720, 18685, "발 기술 연습"),
    ("라인브레이커", ["FW"], ["서울 영등포구", "서울 마포구"], "B",
     ["첫 터치 뒤 곧바로 슛으로 잇습니다"], "뒷공간 전문",
     "mixkit-43494.mp4", 1280, 720, 5672, "페널티킥"),
    ("중원엔진", ["MF"], ["서울 용산구", "서울 마포구"], "B",
     ["패스 뒤 곧바로 다음 자리로 움직입니다", "양발을 고르게 씁니다"], "90분 뛰는 폐",
     "mixkit-43486.mp4", 1280, 720, 22189, "둘이 주고받기"),
    ("철벽수비", ["DF"], ["서울 서대문구", "서울 종로구"], "B",
     ["상대와 공 사이에 몸을 먼저 넣습니다"], "몸싸움 환영",
     "mixkit-43483.mp4", 1280, 720, 5005, "1대1 수비"),
    ("리프팅장인", ["MF"], ["서울 마포구"], "C",
     ["공을 발등 가운데로 받습니다"], "볼 터치 연습 중",
     "mixkit-43490.mp4", 1280, 720, 12930, "리프팅 연습"),
    ("주말스트라이커", ["FW"], ["서울 강서구", "서울 영등포구"], "C",
     ["슛 타이밍을 스스로 만듭니다"], "주말엔 공 찬다",
     "mixkit-736.mp4", 1280, 720, 11917, "슬로모션 킥"),
    ("풀백러너", ["DF", "MF"], ["서울 은평구", "서울 마포구"], "C",
     ["측면을 따라 끝까지 오르내립니다"], "오버래핑 좋아함",
     "mixkit-43484.mp4", 1280, 720, 3504, "측면 돌파"),
    ("새내기키퍼", ["GK"], ["서울 동작구", "서울 영등포구"], "D",
     ["공을 정면으로 받으려 자리를 잡습니다"], "골키퍼 입문",
     "mixkit-43495.mp4", 1280, 720, 7174, "첫 페널티킥 수비"),
    ("풋살초보", ["MF", "DF"], ["서울 마포구", "서울 용산구"], "D",
     ["공을 몸 가까이에 두려 합니다"], "같이 뛰실 분",
     "mixkit-42541.mp4", 720, 1280, 14640, "공 다루기 연습"),
]

# 모두에게 넓게 준다 — 팀이 등록한 시간과 겹쳐야 추천 판에 뜬다. weekday 0=월 … 6=일.
SLOTS = [(1, time(19, 0), time(22, 30)), (3, time(19, 0), time(22, 30)),
         (5, time(8, 0), time(18, 0)), (6, time(8, 0), time(18, 0))]


def dummy_email(n: int) -> str:
    return f"{EMAIL_PREFIX}{n:02d}{EMAIL_DOMAIN}"


def dummy_user_ids(session: Session) -> list[UUID]:
    u = T["user"]
    return list(session.execute(
        select(u.c.id).where(u.c.email.like(f"{EMAIL_PREFIX}%{EMAIL_DOMAIN}"))
    ).scalars())


def delete_all(session: Session) -> int:
    ids = dummy_user_ids(session)
    if not ids:
        return 0
    c, n = T["user_contact"], T["notification"]
    # 지인 신청 알림은 받은 사람(더미가 아닐 수 있다) 쪽에 남는다 — 신청 행이 지워지면
    # 가리킬 곳이 없는 알림이 되므로 먼저 지운다.
    contact_ids = list(session.execute(
        select(c.c.id).where(or_(c.c.requester_user_id.in_(ids), c.c.target_user_id.in_(ids)))
    ).scalars())
    if contact_ids:
        session.execute(delete(n).where(n.c.subject_type == "user_contact",
                                        n.c.subject_id.in_(contact_ids)))
    # 나머지(자격증명·카드·매칭 조건·영상→분석·지인)는 외래키 연쇄가 지운다(부록 D.6).
    session.execute(delete(T["user"]).where(T["user"].c.id.in_(ids)))
    return len(ids)


def seed(session: Session, password: str, contacts_to: str | None) -> list[dict]:
    u = T["user"]
    if dummy_user_ids(session):
        raise SystemExit("더미가 이미 있다 — 다시 넣으려면 --delete 뒤에 돌린다.")
    nicknames = [p[0] for p in PLAYERS]
    taken = list(session.execute(select(u.c.nickname).where(u.c.nickname.in_(nicknames))).scalars())
    if taken:
        raise SystemExit(f"닉네임이 이미 쓰인다: {taken} — PLAYERS 의 닉네임을 바꾼다.")

    target_id = None
    if contacts_to:
        target_id = session.execute(select(u.c.id).where(u.c.email == contacts_to)).scalar_one_or_none()
        if target_id is None:
            raise SystemExit(f"지인으로 붙일 계정이 없다: {contacts_to}")

    pos = dict(session.execute(
        select(T["position"].c.code, T["position"].c.id).where(T["position"].c.sport_code == "football")
    ).all())
    region = dict(session.execute(select(T["region"].c.label, T["region"].c.id)).all())
    password_hash = hash_password(password)
    now = datetime.now(timezone.utc)
    manifest = []

    for i, (nick, positions, regions, grade, notes, tagline, clip, w, h, dur, title) in enumerate(PLAYERS, 1):
        joined = now - timedelta(days=20 - i)
        uid, card_id, video_id, job_id, metric_id = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
        session.execute(insert(u).values(
            id=uid, email=dummy_email(i), nickname=nick, created_at=joined, token_version=0,
            is_searchable=True, is_nickname_searchable=True,
            preferred_positions=positions, location=regions[0],
        ))
        session.execute(insert(T["user_credential"]).values(
            id=uuid4(), user_id=uid, password_hash=password_hash, updated_at=joined))
        session.execute(insert(T["player_card"]).values(
            id=card_id, user_id=uid, public_slug=f"showcase-{i:02d}-{uid.hex[:6]}",
            og_image_key=f"cards/{card_id}.png", tagline=tagline))
        for code in positions:
            session.execute(insert(T["member_match_position"]).values(
                id=uuid4(), user_id=uid, position_id=pos[code]))
        for label in regions:
            if label in region:
                session.execute(insert(T["member_match_region"]).values(
                    id=uuid4(), user_id=uid, region_id=region[label]))
        for weekday, start, end in SLOTS:
            session.execute(insert(T["member_match_slot"]).values(
                id=uuid4(), user_id=uid, weekday=weekday, start_time=start, end_time=end))

        uploaded = joined + timedelta(days=2)
        storage_key = f"videos/{uid}/{DUMMY_MARK}-{clip}"
        session.execute(insert(T["video"]).values(
            id=video_id, user_id=uid, sport_code="football", storage_key=storage_key,
            duration_ms=dur, width=w, height=h, is_public=True, title=title,
            original_filename=clip, kept=True, is_featured=True, created_at=uploaded))
        session.execute(insert(T["analysis_job"]).values(
            id=job_id, video_id=video_id, status="succeeded", job_type="analyze",
            created_at=uploaded, started_at=uploaded + timedelta(seconds=30),
            finished_at=uploaded + timedelta(minutes=3)))
        session.execute(insert(T["analysis_metric"]).values(
            id=metric_id, analysis_job_id=job_id, pipeline_version=DUMMY_MARK,
            rubric_sport="football", created_at=uploaded + timedelta(minutes=3)))
        session.execute(insert(T["analysis_report"]).values(
            id=uuid4(), analysis_metric_id=metric_id,
            summary="시연용 더미 리포트입니다 — 실제 영상 분석 결과가 아닙니다.",
            model_name=DUMMY_MARK, schema_version="1.5", provisional=True,
            overall_grade=grade, card_notes=notes, created_at=uploaded + timedelta(minutes=3)))
        manifest.append({"nickname": nick, "clip": clip, "storage_key": storage_key})

        if target_id is not None and i <= 6:
            contact_id = uuid4()
            accepted = i <= 3  # 앞 셋은 이미 지인, 다음 셋은 신청만 와 있다
            session.execute(insert(T["user_contact"]).values(
                id=contact_id, requester_user_id=uid, target_user_id=target_id,
                accepted_at=now - timedelta(days=1) if accepted else None,
                created_at=now - timedelta(days=3, hours=i)))
            if not accepted:
                session.execute(insert(T["notification"]).values(
                    id=uuid4(), recipient_user_id=target_id, type="contact_request",
                    actor_user_id=uid, subject_type="user_contact", subject_id=contact_id,
                    read_at=None, created_at=now - timedelta(days=3, hours=i)))
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--delete", action="store_true", help="더미 계정과 딸린 기록을 전부 지운다")
    ap.add_argument("--contacts-to", help="더미를 지인·지인 신청으로 붙일 계정 이메일")
    ap.add_argument("--manifest", help="(샘플 파일, 저장소 키) 목록을 쓸 경로")
    ap.add_argument("--allow-prod", action="store_true", help="운영(APP_ENV 가 local/dev 가 아님)에서도 돈다")
    args = ap.parse_args()

    if settings.app_env not in {"local", "dev"} and not args.allow_prod:
        print(f"APP_ENV={settings.app_env} — 운영이면 --allow-prod 를 준다.", file=sys.stderr)
        return 2
    engine = engine_or_none()
    if engine is None:
        print("DATABASE_URL 이 없다.", file=sys.stderr)
        return 2

    with Session(engine) as session:
        if args.delete:
            n = delete_all(session)
            session.commit()
            print(f"더미 {n}명과 딸린 기록을 지웠다. 저장소의 영상 파일은 따로 지운다(videos/<user_id>/{DUMMY_MARK}-*).")
            return 0
        password = os.environ.get("SHOWCASE_PASSWORD", "")
        if len(password) < 8:
            print("SHOWCASE_PASSWORD(8자 이상)를 환경변수로 준다 — 코드에 적지 않는다.", file=sys.stderr)
            return 2
        manifest = seed(session, password, args.contacts_to)
        session.commit()

    print(f"더미 {len(manifest)}명을 넣었다: " + ", ".join(m["nickname"] for m in manifest))
    if args.manifest:
        Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"영상 목록: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
