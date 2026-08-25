# Super-Sub 백엔드 API

생활체육 용병 스카우팅 & RAG 검증 플랫폼(Super-Sub)의 백엔드 API 서버.

저장소 루트는 제안서 Jekyll 사이트이고 이 폴더가 백엔드다.
데이터 모델의 정본은 **부록 D — 데이터베이스 ERD**(33테이블·6도메인,
`jekyll/chapters/부록D-데이터베이스ERD.markdown`)다.

> **상태:** 진행중 — 엔드포인트 5개가 열려 있으나 **전부 스텁(고정 응답)이고
> DB에 붙지 않는다** · 2026-08-25 확인
> **확인:** `.venv/bin/pytest` → `39 passed`
> **메모:** 응답 **형태**는 계약대로 확정이고 **값만 고정**이다. 스프린트 2에서
> Flutter가 화면을 붙일 수 있게 먼저 열어둔 것이다. 실제 조회는 DB가 생긴 뒤.

## 스택

| | |
|---|---|
| 언어 | Python 3.14 |
| 프레임워크 | FastAPI |
| DB | Aurora PostgreSQL + pgvector (**미구축**) |

## 실행

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # 배포만 할 때는 requirements.txt

cp .env.example .env          # 값은 각자 채운다 (지금은 비어 있어도 뜬다)

.venv/bin/uvicorn app.main:app --reload
```

`http://localhost:8000/docs` 에서 OpenAPI 문서를 볼 수 있다.

### 스텁이 받아주는 값

지금은 아래만 성공하고 나머지는 계약대로 실패한다. **에러 경로도 눌러볼 수 있게**
일부러 좁게 잡았다.

| | |
|---|---|
| 이메일 | `demo@super-sub.example` |
| 비밀번호 | `supersub2026` |
| 공개 카드 슬러그 | `hong-gildong-4f2a` |

```bash
curl -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@super-sub.example","password":"supersub2026"}'
```

## 검증

```bash
.venv/bin/pytest
```

- `tests/test_*_domain.py` — 도메인 규칙. **서버도 DB도 띄우지 않는다.**
- `tests/test_api_contract.py` — 계약 문서의 모든 경로를 **성공·실패 양쪽으로** 누른다.

**엔드포인트를 추가하면 성공 1건 + 실패 최소 1건을 같이 넣는다.** 이 규칙이 실제로
버그를 잡았다 — 에러 핸들러가 통째로 깨져 모든 실패가 500 이 된 적이 있다.

## 구조

컨텍스트(세로)로 자르고 그 안에서 계층(가로)을 나눈다. **기술 계층이 최상위가 아니다** —
`routers/`·`schemas/`로 자르면 기능 하나가 폴더 네 곳에 흩어진다.

컨텍스트 이름은 부록 D의 도메인 구분을 따른다. 지금은 ①·③ 둘뿐이고, 영상·분석(②),
매칭(④), 평가·신뢰(⑤), 과금(⑥)이 같은 모양으로 늘어난다.

```
app/
  main.py                   앱 조립과 /health
  config.py                 환경변수 (키 이름은 저장소 루트의 .env.example 을 따른다)
  errors.py                 에러 응답 봉투 — {"error": {"code", "message"}}
  deps.py                   의존성 주입 + 인증 (컨텍스트에 걸치는 관심사)
  shared.py                 어느 컨텍스트에도 속하지 않는 것 (RFC 3339 직렬화)

  identity/                 부록 D 도메인 ① 사용자·팀
    domain.py               규칙 — 이메일 정규화, 탈퇴 소속 필터, 비밀번호 정책
    service.py              유스케이스 + 출력 포트(Protocol)
    stub_repository.py      고정 데이터 (DB 붙으면 삭제)
    schemas.py              HTTP 모델
    router.py               HTTP 경계

  cards/                    부록 D 도메인 ③ 카드·호칭
    domain.py               규칙 — 공개 변환, 호칭 노출, D.5 금지 필드
    service.py  stub_repository.py  schemas.py  router.py

tests/
docs/api-contract.md        API 계약
```

### 계층 규칙

| 계층 | 아는 것 | 모르는 것 |
|---|---|---|
| `domain.py` | 아무것도 (순수 함수) | HTTP · DB · 프레임워크 |
| `service.py` | 도메인, 출력 포트 | 저장소 **구현**, HTTP |
| `router.py` | 서비스, HTTP 모델 | 저장소 |
| `stub_repository.py` | 도메인 | 서비스 · HTTP |

**저장소 구현을 고르는 곳은 `deps.py` 한 곳뿐이다.** DB가 붙으면 거기서
`Stub*Repository`를 `Pg*Repository`로 바꾸면 되고 나머지는 고치지 않는다.

부록 D.5의 설계 원칙(수치 비노출·호칭 미부여·순위표 없음)은 `cards/domain.py`에
살고 `tests/test_cards_domain.py`가 지킨다.

## 엔드포인트

전부 `/api/v1` 아래. 자세한 것은 [`docs/api-contract.md`](docs/api-contract.md).

| | | 인증 |
|---|---|---|
| `POST` | `/auth/signup` | |
| `POST` | `/auth/login` | |
| `GET` | `/me` | 필요 |
| `GET` | `/me/card` | 필요 |
| `GET` | `/cards/{public_slug}` | 불필요 (공유용) |

## 다음 할 일

1. **정어진에게 `/docs` 공유** — `titles`가 빈 배열인 화면 처리와
   401 두 종류(`UNAUTHORIZED`/`INVALID_TOKEN`) 분기를 확인해야 한다.
2. **DDL 작성과 검증** — 부록 D는 문서일 뿐이라 D.6 삭제 연쇄와 D.7 유일제약 18건이
   아직 코드가 아니다. 실제 PostgreSQL에 올려서 성립하는지 확인한다. alembic 도 이때.
3. **스텁 → 실제 조회 교체** — `stub_repository.py` 둘을 `pg_repository.py`로 바꾸고
   `deps.py`만 고친다. **응답 형태는 그대로라 Flutter 쪽은 고칠 것이 없어야 한다.**
4. **비밀번호 해싱(bcrypt)과 JWT 발급** — 지금은 고정 문자열이다.
5. **영상 업로드(SFR-001)와 analysis_job 큐** — 데이터 파이프라인과의 접점.
   `app/analysis/`가 같은 모양으로 붙는다.
