# Super-Sub 백엔드 API

생활체육 용병 스카우팅 & RAG 검증 플랫폼(Super-Sub)의 백엔드 API 서버.

저장소 루트는 제안서 Jekyll 사이트이고 이 폴더가 백엔드다.
데이터 모델의 정본은 **부록 D — 데이터베이스 ERD**(33테이블·6도메인,
`jekyll/chapters/부록D-데이터베이스ERD.markdown`)다.

> **상태:** 진행중 — 엔드포인트 5개가 열려 있으나 **전부 스텁(고정 응답)이고
> DB에 붙지 않는다** · 2026-08-25 확인
> **확인:** `.venv/bin/pytest` → `60 passed`
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

## 구조

**컨텍스트(세로)로 먼저 자르고 그 안에서 계층(가로)을 나눈다.** 기술 계층이 최상위면
기능 하나가 폴더 네 곳에 흩어진다.

**폴더 이름은 부록 D의 도메인을 그대로 따른다.** ERD 문서에서 "도메인 ③"을 보면
`app/card/`를 열면 된다.

```
app/
  main.py             앱 조립과 /health
  config.py           환경변수 (키 이름은 저장소 루트의 .env.example 을 따른다)
  errors.py           에러 응답 봉투 — {"error": {"code", "message"}}
  security.py         토큰 발급·검증 (어느 컨텍스트에도 속하지 않는다)
  deps.py             인증 의존성 — 컨텍스트가 공유한다
  shared.py           RFC 3339 직렬화

  user/               부록 D ① 사용자·팀 — 가입·로그인·내 정보·소속
    domain/
      entities.py       User, Membership
      value_objects.py  Email, Nickname, Password
      rules.py          탈퇴 소속 거르기
    application/
      ports.py          UserRepository (Protocol) — 출력 포트
      use_cases.py      SignupUseCase, LoginUseCase, MeUseCase
    adapter/
      inbound/          schemas.py, router.py
      outbound/         stub_repository.py  (pg_repository.py 는 DB 때)
    dependencies.py     저장소 구현을 고르는 곳
    _docs/README.md     이 컨텍스트 설명

  card/               부록 D ③ 카드·호칭 — 같은 모양

tests/
  conftest.py         client · auth 픽스처
  user/               test_value_objects · test_rules · test_use_cases · test_api
  card/               test_rules · test_use_cases · test_api
docs/api-contract.md  API 계약
```

앞으로 `video`(②) · `match`(④) · `review`(⑤) · `billing`(⑥)이 같은 모양으로 붙는다.

### 계층 규칙

| 계층 | 아는 것 | 모르는 것 |
|---|---|---|
| `domain/` | 아무것도 (순수 함수·데이터) | HTTP · DB · 프레임워크 |
| `application/` | 도메인, 출력 포트 | 저장소 **구현**, HTTP |
| `adapter/inbound/` | 유스케이스, HTTP 모델 | 저장소 |
| `adapter/outbound/` | 도메인 | 유스케이스 · HTTP |
| `dependencies.py` | 위 전부 | — 여기서만 구현을 고른다 |

**컨텍스트끼리 직접 임포트하지 않는다.** 인증처럼 걸치는 것은 `app/security.py`로
빼서 양쪽이 그것만 보게 한다.

> 지금 딱 한 곳이 예외다 — `card/adapter/outbound/stub_repository.py`가 데모 카드의
> 주인을 맞추려고 `user`의 스텁 상수를 임포트한다. **스텁끼리라 DB가 붙으면 둘 다
> 사라진다.** 도메인·유스케이스·라우터에는 이 의존이 없다.

### 왜 `login`과 `user_card`가 아닌가

- **`login`을 따로 빼지 않는다.** 로그인은 `user`와 `user_credential`을 함께 읽는다.
  나누면 로그인 쪽이 `user`의 저장소를 임포트해야 한다. 같은 것을 다루면 같은 폴더다.
- **`user_card`가 아니라 `card`다.** "누구의 데이터가 필요한가"로 이름을 지으면 결국
  전부 `user_`가 붙는다 — 매칭도 평가도 과금도 사용자를 참조한다. 부록 D는 **무엇인가**로
  잘라 놨다.

## 검증

```bash
.venv/bin/pytest
```

- `tests/*/test_value_objects.py`, `test_rules.py` — 도메인. **아무것도 안 띄운다.**
- `tests/*/test_use_cases.py` — 가짜 저장소를 끼워서 유스케이스만. **DB도 HTTP도 없다.**
- `tests/*/test_api.py` — 계약의 모든 경로를 **성공·실패 양쪽으로** 누른다.

**엔드포인트를 추가하면 성공 1건 + 실패 최소 1건을 같이 넣는다.** 이 규칙이 실제로
버그를 잡았다 — 에러 핸들러가 통째로 깨져 모든 실패가 500 이 된 적이 있다.

부록 D.5의 설계 원칙(수치 비노출·호칭 미부여·순위표 없음)은 `card/domain/rules.py`에
살고 `tests/card/test_rules.py`가 지킨다.

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
   각 컨텍스트의 `dependencies.py`만 고친다. **응답 형태는 그대로라 Flutter 쪽은
   고칠 것이 없어야 한다.**
4. **비밀번호 해싱(bcrypt)과 진짜 JWT** — 지금은 `app/security.py`가 스텁으로 발급한다.
5. **영상 업로드(SFR-001)와 analysis_job 큐** — `app/video/`가 같은 모양으로 붙는다.
