# fastapi/ — 백엔드

> **소유: 정어진(백엔드·파이프라인).** 스키마·API 계약은 여기서 정한다.
> 고쳐야 할 일이 생기면 **미결 항목(`jekyll/pages/pending.markdown`)에 올려 주세요** —
> 급하면 직접 고쳐도 되지만 아래 관례는 지켜야 CI가 통과합니다.

## 🔴 2026-09-03 부터 여기서 셋이 일합니다 — 먼저 볼 것

미구현 도메인 둘을 나눴습니다. **자기 몫이 있는지부터 보십시오.**

| 패킷 | 도메인 | 담당 |
|---|---|---|
| A | 과금 (`analysis_credit` · `coach` · `coach_referral`) | **백성검** |
| B | 평가·신뢰 (`review` · `review_option` · `review_selection` · `report` · `no_show`) | **박민호** |

**지시서는 `docs/backend-work-split.md` 입니다** — 만족해야 할 성질, 확인 명령,
하지 말아야 할 것이 패킷마다 붙어 있습니다.

🔴 **공유 파일 5곳은 건드리지 마십시오.** `app/main.py` · `alembic/env.py` ·
`tests/conftest.py` · `tests/user/adapter/test_auth_router.py` ·
`alembic/versions/` 의 `down_revision`. **배선은 정어진이 합니다** — 특히
마이그레이션 체인은 동시에 만들면 head 가 둘이 되어 자동 병합이 안 됩니다.
다 만드셨으면 브랜치에 푸시하고 알려 주십시오.

Python 3.14 · FastAPI · SQLAlchemy(동기) · PostgreSQL 18 + pgvector · Alembic.

```bash
.venv/bin/pytest -q          # 204 passed (DB 없으면 통합 테스트가 skip 된다)
.venv/bin/alembic upgrade head && .venv/bin/alembic check
```

DB가 필요하다. WSL은 자동 기동이 아니다 — `pg_ctlcluster 18 main start`(root).

---

## 구조 — 기술 계층이 아니라 **바운디드 컨텍스트**

`app/<컨텍스트>/{domain,application,adapter,dependencies}`. 컨텍스트는
`user` · `card` · `analysis` 셋이고 공용은 `app/core/`다.

🔴 **컨텍스트끼리 임포트하지 않는다.** 남의 테이블이 필요하면 **문자열 참조**로 건다.

```python
ForeignKey("sport.code")                      # 임포트 없이
table("player_card", column("user_id"))       # 조회도 원시 SQL 로
```

`tests/test_architecture.py`가 계층·경계·등록을 **실제로 검사한다.** 주석으로 적어
둔 규칙은 반드시 무너지므로 거기서 막는다.

---

## 🔴 검사가 막는 것 넷 — 왜 있는지 모르면 지우고 싶어진다

| 검사 | 어기면 | 이유 |
|---|---|---|
| `TestOrmRegistration` | `alembic --autogenerate`가 **`DROP TABLE`을 만든다** | `env.py`에 등록 안 된 ORM은 "DB에만 있는 것"으로 보인다 |
| `TestForeignKeyTargets` | 앱이 그 모델을 쓰는 순간 `NoReferencedTableError` | `env.py` 등록은 **마이그레이션 때만** 쓰인다. 리포지토리가 없는 모델은 그 컨텍스트의 `orm/__init__.py`에서 끌어와야 런타임 metadata에 들어간다 |
| `TestMigrationPrivileges` | **배포에서만** 권한 오류로 마이그레이션이 멈춘다 | `CREATE EXTENSION`은 확장이 `trusted`가 아니면 슈퍼유저가 필요하다. **컨테이너 PostgreSQL은 초기 사용자가 슈퍼유저라 CI에서는 조용히 통과한다** — 그래서 권한이 아니라 글자로 막는다 (`docs/deployment.md` 1절) |
| `TestDocPaths` | 문서가 없는 파일을 가리킨다 | 받는 쪽이 그대로 실행하면 엉뚱한 곳을 만든다 |

**새 ORM을 만들면 `alembic/env.py`에 임포트를 추가한다.** 참조만 되고 아무도
임포트하지 않는 모델(`sport` 같은)은 `orm/__init__.py`에도 넣는다 — 둘은 다른 축이다.

---

## 테스트는 두 층이다

| 층 | 무엇을 | 저장소 |
|---|---|---|
| 계약 테스트 | 상태 코드·에러 `code`·응답 형태 | 스텁 |
| **DB 통합 테스트** (`@pytest.mark.db`) | 실제로 저장·조회·삭제되는가 | 진짜 PostgreSQL |

🔴 **원시 SQL로 남의 테이블을 읽는 자리가 셋 있다**(`card`→`user.nickname`,
`core/deps.py`→`user.token_version`·`email`, `user`→`player_card.user_id`).
컨텍스트 경계를 지키려는 의도지만 **컬럼 이름을 바꾸면 파이썬이 잡아 주지 않는다.**
`test_card_db.py`·`test_token_revocation_db.py`·`test_admin_db.py`가 유일한 방어선이다 —
**지우거나 `@pytest.mark.db`를 떼지 말 것.**

DB가 없으면 통합 테스트는 **실패가 아니라 skip**이다. 초록색으로 끝나 놓치기 쉬우니
**개수가 아니라 `skipped`가 0인지** 본다. CI는 skip이 있으면 exit 1을 낸다.

### 테스트를 새로 쓸 때 — 전역 상태 셋

요청 제한(`conftest.py`의 autouse `reset()`이 없으면 순서에 따라 429로 깨진다) ·
로그 검사(`r.name == "supersub.auth"`로 걸러야 남의 로거가 안 섞인다) ·
`settings.admin_emails`(바꿨으면 `try/finally`로 되돌린다).

---

## 로그·에러에 남기면 안 되는 것

비밀번호 · 토큰 · `Authorization` 헤더 · 본문 · 쿼리 문자열, 그리고 **실패 로그의
이메일**(공격자가 값을 정하는 자리라 로그가 오염된다). `tests/test_auth_logging.py`의
`TestNoSecrets`가 지킨다 — **완화하지 말 것.**

에러는 전부 `ApiError(status, code, message)`로 낸다. 계약 형태는
`{"error": {"code": ..., "message": ...}}` 하나뿐이고 **클라이언트는 `code`로
분기**하므로 `message`만 바꿔도 되지만 `code`는 계약이다.

---

## 계약을 바꿨으면 두 곳을 함께

1. `docs/api-contract.md` — 규격의 정본
2. `docs/client-contract-changes.md` — **클라이언트가 반영할 것.** 받는 쪽 Claude가
   그대로 실행하므로 **"이 파일을 고쳐라"가 아니라 "이 성질을 만족하라"로** 쓰고
   확인 방법을 함께 적는다 (루트 `CLAUDE.md`의 「미결 항목」 절)

배포 절차는 `docs/deployment.md`. 🔴 확장(`pgvector`)은 **마이그레이션보다 먼저,
슈퍼유저가** 만든다.
