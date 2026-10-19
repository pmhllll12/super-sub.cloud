# Super-Sub 백엔드 API

생활체육 용병 스카우팅 & RAG 검증 플랫폼(Super-Sub)의 백엔드 API 서버.

저장소 루트는 제안서 Jekyll 사이트이고 이 폴더가 백엔드다.
데이터 모델의 정본은 **부록 D — 데이터베이스 ERD**(33테이블·6도메인,
`jekyll/chapters/부록D-데이터베이스ERD.markdown`)다.

> **상태:** 🔴 **위 "전부 스텁이고 DB에 안 붙는다"는 2026-08-25 스냅샷이고
> 지금은 낡았다 — 정정한다 (2026-09-20 확인).** 컨텍스트 일곱(`user`·`card`·
> `analysis`·`match`·`review`·`billing`·`notification`) 대부분이 실물
> `*_pg_repository.py`로 DB에 붙어 있고, `alembic/versions/`에 마이그레이션
> 48개가 쌓여 있다. 스텁(`*_stub_repository.py`)은 이제 **계약 테스트 전용**으로
> 남은 자리이지 서비스 경로가 아니다(허용된 예외 하나는 위 「계층 규칙」 절 참고).
> **확인:** 이 저장소(DB 없이) `pytest -q` → `810 passed, 324 skipped`(skip은
> DB 필요한 통합 테스트). 🔴 **엔드포인트 5개도 낡은 숫자다** — 지금은 훨씬 많다,
> 정본은 [`docs/api-contract.md`](docs/api-contract.md)
> **메모:** 위 상태 줄을 새로 확인할 때는 날짜를 반드시 같이 남긴다 — 이 줄이
> 3주 넘게 안 고쳐져 있던 것이 이번 정정의 이유다.

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

## 구조

**컨텍스트(세로)로 먼저 자르고 그 안에서 계층(가로)을 나눈다.**
폴더 이름은 부록 D의 도메인을 그대로 따른다 — ERD에서 "도메인 ③"을 보면 `app/card/`다.

```
app/
  main.py             앱 조립과 /health
  config.py           환경변수
  errors.py           에러 응답 봉투 — {"error": {"code", "message"}}
  security.py         토큰 발급·검증 (어느 컨텍스트에도 속하지 않는다)
  deps.py             인증 의존성 — 컨텍스트가 공유한다
  shared.py           RFC 3339 직렬화

  user/                                   부록 D ① 사용자·팀
    domain/
      entities/       user_entity.py · membership_entity.py
      value_objects/  email_vo.py · nickname_vo.py · password_vo.py
      rules/          membership_rules.py
    application/
      dtos/           signup_dto.py · login_dto.py · me_dto.py
      ports/input/    signup_use_case.py · login_use_case.py · me_use_case.py
      ports/output/   user_port.py
      use_cases/      signup_interactor.py · login_interactor.py · me_interactor.py
    adapter/
      inbound/api/schemas/  auth_schema.py · me_schema.py
      inbound/api/v1/       auth_router.py · me_router.py
      outbound/orm/         *_orm.py (SQLAlchemy 모델)
      outbound/pg/          *_pg_repository.py (실물)
      outbound/stub/        *_stub_repository.py (계약 테스트용)
    dependencies/     user_repository_provider.py · *_provider.py
    _docs/README.md

  card/                                   부록 D ③ 카드·호칭 — 같은 모양
```

**컨텍스트는 일곱이고 전부 붙어 있다**(2026-09-16 기준) — `user`(①) ·
`analysis`(②, 부록 D 의 "영상·분석") · `card`(③) · `match`(④) · `review`(⑤) ·
`billing`(⑥) · `notification`. 목록의 정본은 `tests/test_architecture.py` 의
`CONTEXTS` 이고, 실제 디렉터리와 어긋나면 같은 파일의 검사가 잡는다.

### 파일 이름 접미사

| 접미사 | 무엇 |
|---|---|
| `*_entity.py` | 도메인 엔티티 |
| `*_vo.py` | 값 객체 |
| `*_rules.py` | 도메인 규칙 (순수 함수) |
| `*_dto.py` | 계층을 건너는 데이터 (`Command`·`Query`·`Result`) |
| `*_use_case.py` | 입력 포트 (ABC) |
| `*_interactor.py` | 입력 포트의 구현 |
| `*_port.py` | 출력 포트 (ABC) |
| `*_schema.py` | HTTP 요청·응답 모델 |
| `*_router.py` | FastAPI 라우터 |
| `*_repository.py` | 출력 포트의 구현 |
| `*_provider.py` | FastAPI Depends 프로바이더 |

ORM이 생기면 `*_orm.py`(SQLAlchemy 모델)와 `*_mapper.py`(ORM ↔ 엔티티)가 붙는다.

### 인바운드 → 아웃바운드

```
router ──Command/Query DTO──▶ 입력 포트(ABC) ──▶ 인터랙터
                                                    │
                                          도메인 규칙·엔티티
                                                    │
                                              출력 포트(ABC)
                                                    │
                                              리포지터리 구현
router ◀──Result DTO── 인터랙터 ◀───────────────────┘
   │
   └─ response_model(from_attributes) 이 DTO → 응답 스키마
```

**라우터는 엔티티를 모르고 도메인은 HTTP를 모른다.** DTO 가 그 경계다.

### 계층 규칙 — 주석이 아니라 테스트로 강제한다

| 계층 | 아는 것 | 모르는 것 |
|---|---|---|
| `domain/` | 아무것도 | HTTP · DB · 프레임워크 · 바깥 계층 |
| `application/` | 도메인, 포트 | 어댑터, HTTP |
| `adapter/inbound/` | 유스케이스, DTO, HTTP 스키마 | **도메인 엔티티·규칙** |
| `adapter/outbound/` | 도메인, 출력 포트 | 유스케이스 · HTTP |
| `dependencies/` | 위 전부 | — 여기서만 구현을 고른다 |

`tests/test_architecture.py`가 임포트를 직접 읽어서 검사한다. 규칙 네 개:
인바운드→도메인 금지, 도메인→바깥 금지, 애플리케이션→어댑터 금지, 컨텍스트끼리 금지.
**일부러 위반을 넣어 네 규칙이 전부 실패하는 것을 확인했다** — 적어만 두고 안 도는
규칙은 없느니만 못하다.

> 허용된 예외 하나 — `card/adapter/outbound/repositories/card_stub_repository.py`가
> 데모 카드 주인을 맞추려고 `user`의 스텁 상수를 임포트한다. **스텁끼리라 DB가 붙으면
> 둘 다 사라진다.** 예외가 늘어나면 테스트가 알려준다.

### 왜 `login`과 `user_card`가 아닌가

- **`login`을 따로 빼지 않는다.** 로그인은 `user`와 `user_credential`을 함께 읽는다.
  나누면 로그인 쪽이 `user`의 저장소를 임포트해야 한다. 같은 것을 다루면 같은 폴더다.
- **`user_card`가 아니라 `card`다.** "누구의 데이터가 필요한가"로 이름을 지으면 결국
  전부 `user_`가 붙는다. 부록 D는 **무엇인가**로 잘라 놨다.

## 검증

```bash
.venv/bin/pytest
```

| 테스트 | 무엇을 띄우나 |
|---|---|
| `tests/*/domain/` | 아무것도 |
| `tests/*/application/` | 가짜 저장소만 (DB·HTTP 없음) |
| `tests/*/adapter/` | 앱 전체 (TestClient) |
| `tests/test_architecture.py` | 소스 임포트를 읽기만 |

**엔드포인트를 추가하면 성공 1건 + 실패 최소 1건을 같이 넣는다.** 이 규칙이 실제로
버그를 잡았다 — 에러 핸들러가 통째로 깨져 모든 실패가 500 이 된 적이 있다.

## 엔드포인트

전부 `/api/v1` 아래. 자세한 것은 [`docs/api-contract.md`](docs/api-contract.md).

🔴 **아래 표도 위 상태 줄과 같은 시점(2026-08-25)의 스냅샷이라 낡았다** —
지금은 컨텍스트 일곱에 걸쳐 이보다 훨씬 많은 엔드포인트가 있다(빌드 시점
라우트 목록에 영상·매칭·리뷰·과금·알림·관리자 경로가 수십 개 잡힌다).
**정본은 [`docs/api-contract.md`](docs/api-contract.md)** — 이 표는 갱신하지
않고 링크로 대신한다(같은 정보를 두 곳에 두면 한쪽만 고쳐져 어긋난다).

## 다음 할 일

🔴 **아래 다섯 항목도 2026-08-25 스냅샷이다.** 이번 확인(2026-09-20)에서
1(비밀번호 해싱 bcrypt)은 `requirements.txt`에 실제로 있는 것을 봤고,
2(DDL)·3(스텁→실제 교체)은 위 상태 줄대로 대체로 끝나 있는 것으로 보이며,
5(영상 업로드)도 `app/analysis/`로 이미 존재한다 — 다만 **하나하나 다시
확인한 것은 아니라 지우지 않고 남겨 둔다.** 실제로 뭐가 남았는지는 이 목록이
아니라 `jekyll/pages/pending.markdown`의 `jin` 구역이 정본이다.

1. **백성검에게 `/docs` 공유** — `titles`가 빈 배열인 화면 처리와
   401 두 종류(`UNAUTHORIZED`/`INVALID_TOKEN`) 분기를 확인해야 한다.
2. **DDL 작성과 검증** — 부록 D는 문서일 뿐이라 D.6 삭제 연쇄와 D.7 유일제약 18건이
   아직 코드가 아니다. 실제 PostgreSQL에 올려서 확인한다. alembic 도 이때.
3. **스텁 → 실제 조회 교체** — `*_stub_repository.py` 옆에 `*_pg_repository.py`를 만들고
   `*_repository_provider.py` 한 줄만 바꾼다. `*_orm.py`·`*_mapper.py`가 이때 생긴다.
   **응답 형태는 그대로라 Flutter 쪽은 고칠 것이 없어야 한다.**
4. **비밀번호 해싱(bcrypt)과 진짜 JWT** — 지금은 `app/security.py`가 스텁으로 발급한다.
5. **영상 업로드(SFR-001)와 analysis_job 큐** — `app/video/`가 같은 모양으로 붙는다.
