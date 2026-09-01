# 백엔드 배포 준비

> **상태:** 진행 전 · 2026-09-01 작성
> **확인:** 배포 환경이 아직 없다. `RDS_HOST`·`DATABASE_URL` 이 비어 있으면 미착수다.
> **메모:** 여기 적힌 것은 **배포 환경이 생겼을 때 순서대로 밟는 절차**다. 로컬
> 개발에 필요한 것은 `.env.example` 이 안내한다.

아래 순서에는 이유가 있다. **1번은 마이그레이션보다 먼저**여야 하고, 2번이 빠지면
조용히 잘못 동작한다.

---

## 1. DB 확장을 먼저 만든다 — 마이그레이션 전에

🔴 **`CREATE EXTENSION vector` 는 슈퍼유저만 할 수 있다.** 앱 계정으로는 안 된다.

`pgvector` 는 SFR-005(유사 선수 검색)가 쓸 확장이다. 확장이 없으면 `vector` 타입을
참조하는 마이그레이션이 `type "vector" does not exist` 로 **도중에** 멈춘다 —
스키마가 반쯤 올라간 상태가 된다.

```sql
-- 슈퍼유저로 (로컬: postgres · Aurora/RDS: rds_superuser)
CREATE EXTENSION IF NOT EXISTS vector;
```

로컬(WSL)에서는 이렇게 한다.

```bash
wsl.exe -d Ubuntu-26.04 -u root -- su - postgres -c "psql -d supersub -c 'CREATE EXTENSION IF NOT EXISTS vector'"
```

**확인** — 앱 계정으로 접속해 `installed_version` 이 나오면 된 것이다.

```sql
select name, default_version, installed_version
from pg_available_extensions where name = 'vector';
-- installed_version 이 NULL 이면 아직 안 만들어진 것이다
```

### 왜 마이그레이션에 넣지 않는가

**확장마다 필요한 권한이 다르다.** `trusted = true` 로 표시된 확장은 DB 소유자면
만들 수 있지만, **`vector` 는 trusted 가 아니라 슈퍼유저여야 한다.** 2026-09-01 에
로컬 PostgreSQL 18 에서 실측한 결과다 (`supersub` 는 DB 소유자, 슈퍼유저 아님).

| 시도 | 결과 |
|---|---|
| `CREATE EXTENSION hstore` (trusted) | 만들어졌다 |
| `CREATE EXTENSION postgres_fdw` (trusted 아님) | `permission denied to create extension` |

⚠️ **컨테이너로 띄운 PostgreSQL 에서 통과한 것은 근거가 못 된다.** 초기 사용자가
슈퍼유저인 경우가 많아 거기서는 조용히 성공한다. 그래서 권한이 아니라 **글자로**
막는다 — `tests/test_architecture.py` 의 `TestMigrationPrivileges` 가 마이그레이션
파일에 `CREATE EXTENSION` 이 들어가면 실패시킨다. **그 검사를 지우지 말 것.**

> `alembic check` 는 확장을 보지 않는다. 확장이 빠져도 거기서는 경고가 안 나온다.

---

## 2. 환경변수 — 빠뜨리면 조용히 잘못 도는 것들

`fastapi/.env.example` 이 전체 목록이다. 여기서는 **배포에서 특히 주의할 것**만 적는다.

| 키 | 안 넣으면 | 방향 |
|---|---|---|
| `APP_ENV` | 🔴 기본값이 `local` 이라 **`/docs`·`/openapi.json` 이 열린다** | fail-**open** |
| `ADMIN_EMAILS` | 회원 관리 admin 이 통째로 403 | fail-**closed** |
| `JWT_SECRET` | 로그인이 503(`AUTH_NOT_CONFIGURED`). 조용한 기본값은 두지 않았다 | fail-closed |
| `GOOGLE_CLIENT_IDS` | 구글 로그인이 503. **플랫폼마다 클라이언트 ID 가 다르니 쉼표로 전부** | fail-closed |

🔴 **`APP_ENV` 만 방향이 반대다.** 다른 것은 빠지면 기능이 멈춰서 바로 드러나는데,
이것은 빠지면 **문서가 공개된 채로 정상 동작한다.** 배포 직후 확인한다.

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<배포주소>/docs   # 404 여야 한다
```

---

## 3. 마이그레이션

```bash
alembic upgrade head
alembic check        # "No new upgrade operations detected." 여야 한다
```

`create_all` 을 쓰지 않는다 — 마이그레이션이 스키마의 정본이다.

---

## 4. 리버스 프록시·로드밸런서 뒤에 둘 때

🔴 **`X-Forwarded-For` 를 신뢰하도록 설정하지 않으면** 인증 로그의 `client` 와
**요청 제한(SEC-009)의 키가 전부 LB 주소가 된다.** 즉 모든 사용자가 한 덩어리로
묶여 서로의 제한에 걸린다.

같은 이유로 DB 접속은 `sslmode=verify-full` 을 쓴다. 기본값으로 둔 `require` 는
**암호화만 하고 인증서를 검증하지 않아** 중간자 공격을 막지 못한다.

```
DATABASE_URL=postgresql://<user>:<pw>@<host>:5432/<db>?sslmode=verify-full
```

---

## 5. 알고 넘어가는 한계

배포를 막지는 않지만 **모르고 있으면 나중에 원인을 못 찾는 것들**이다.

| 무엇 | 내용 |
|---|---|
| 요청 제한이 **프로세스 안에서만** 센다 | 워커가 여럿이면 워커마다 따로 센다. 실효 한도가 워커 수만큼 늘어난다 (5장 SEC-009) |
| 삭제 연쇄가 **DB 까지만** | 객체 저장소가 정해지지 않아 원본·썸네일·추출 프레임이 남는다 (5장 SEC-006 · ASM-003) |
| `Retry-After` 헤더가 없다 | 429 응답에 재시도 시점을 싣지 않는다. 클라이언트가 즉시 재시도하지 않도록 별도 합의가 필요하다 |
