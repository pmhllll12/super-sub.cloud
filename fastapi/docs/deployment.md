# 백엔드 배포 준비

> **상태:** 진행 전 (**서버는 생겼다**) · 2026-09-02 확인
> **확인:** `ssh supersub 'command -v psql python3.14'` → 둘 다 비면 미착수다. 서버 자체는 `ssh supersub 'uptime'` 으로 확인한다.
> **메모:** 여기 적힌 것은 **배포 환경이 생겼을 때 순서대로 밟는 절차**다. 로컬
> 개발에 필요한 것은 `.env.example` 이 안내한다.

아래 순서에는 이유가 있다. **1번은 마이그레이션보다 먼저**여야 하고, 2번이 빠지면
조용히 잘못 동작한다. **0번은 2026-09-02 에 서버가 생기면서 앞에 붙었다** — 거기 적힌 셋이 정해지기 전에는 1번을 시작할 수 없다.

---

## 0. 배포 대상 서버 — 무엇이 있고 무엇이 없나 (2026-09-02 확인)

EC2 인스턴스 하나가 생겼다(`ssh supersub` · 서울 리전 · t3.large · vCPU 2 · 메모리
7.8GB · 디스크 8GB 중 6.4GB 여유). **접속 정보는 저장소에 두지 않는다** — 개인
`~/.ssh/config` 의 `supersub` 별칭으로 가리킨다.

**확인 명령** (읽기만 한다):

```bash
ssh supersub 'cat /etc/os-release | head -2; nproc; free -m | head -2; df -h /'
```

### 지금 상태 — 빈 서버다

| 항목 | 실제 |
|---|---|
| OS | Amazon Linux 2023 (커널 6.18) |
| 파이썬 | **3.9.25 하나뿐.** `dnf` 로 받을 수 있는 최신이 **3.11** 이다 |
| PostgreSQL | 없다 (`psql`·`postgres` 둘 다) |
| 그 외 | `git`·`nginx`·`docker`·`gcc`·`make` **전부 없다** |
| 열린 포트 | **22 만.** 80·443 은 닫혀 있다 |

### 🔴 먼저 정해야 하는 것 셋

**⑴ 파이썬 3.14 를 어떻게 넣는가.** 이 프로젝트는 3.14 다(`fastapi/CLAUDE.md`).
배포판 저장소에 없으므로 셋 중 하나를 골라야 한다.

| 방법 | 대가 |
|---|---|
| `uv` 로 독립 실행형 3.14 설치 | 가장 빠르다(빌드 없음). 도구 하나가 배포 경로에 는다 |
| 소스 빌드 | `gcc`·`make`·헤더를 깔고 10분 내외 빌드. 재현이 느리다 |
| 3.11 로 낮춘다 | **코드를 봐야 한다.** 지금 3.14 문법을 쓰는지 확인 전에는 고를 수 없다 |

**⑵ DB 를 어디에 두는가.** RDS(관리형·`pgvector` 는 `rds_superuser` 로 생성)와
같은 인스턴스에 설치하는 방법이 있다. **디스크가 8GB 뿐이라** 같은 인스턴스에 두면
영상·분석 데이터가 늘 때 먼저 막힌다. 비용이 걸린 결정이라 혼자 정하지 않는다.

**⑶ 80·443 을 열 것인가.** 보안 그룹 변경은 AWS 콘솔 권한이 필요하다. 열기 전에
1절(확장)·2절(환경변수)이 끝나 있어야 한다 — **설정이 빈 채로 노출되면 503 이 아니라
잘못 도는 상태가 될 수 있다**(2절 참고).

> ⚠️ **아직 아무것도 설치하지 않았다.** 위 셋이 정해지기 전에는 서버를 건드리지
> 않는다. 지금까지 한 일은 읽기 전용 확인뿐이다.

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
