# Super-Sub 백엔드 API

생활체육 용병 스카우팅 & RAG 검증 플랫폼(Super-Sub)의 백엔드 API 서버.

저장소 루트는 제안서 Jekyll 사이트이고 이 폴더가 백엔드다.
데이터 모델의 정본은 **부록 D — 데이터베이스 ERD**(33테이블·6도메인,
`jekyll/chapters/부록D-데이터베이스ERD.markdown`)다.

> **상태:** 진행중 — 엔드포인트 5개가 열려 있으나 **전부 스텁(고정 응답)이고
> DB에 붙지 않는다** · 2026-08-25 확인
> **확인:** `bash smoke.sh` → `통과 18 · 실패 0`
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
.venv/bin/pip install -r requirements.txt

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
bash smoke.sh
```

계약 문서의 모든 경로를 **성공·실패 양쪽으로** 눌러본다(18건). 서버를 직접 띄웠다
내리므로 사전 준비가 필요 없다. 이미 8000을 쓰고 있으면 `BASE=... bash smoke.sh`.

부록 D.5의 설계 원칙(카드에 수치 없음, 호칭 미부여 표식 없음)도 응답을 훑어 확인한다.

## 구조

```
app/
  main.py       앱 조립과 /health
  config.py     환경변수 (키 이름은 저장소 루트의 .env.example 을 따른다)
  errors.py     에러 응답 봉투 — {"error": {"code", "message"}}
  schemas.py    요청·응답 모델 (필드는 부록 D 의 실제 컬럼에서 왔다)
  deps.py       Authorization 헤더 검사
  stubs.py      고정 응답 데이터 — DB 가 붙으면 통째로 사라진다
  routers/
    auth.py     POST /auth/signup, POST /auth/login
    users.py    GET /me
    cards.py    GET /me/card, GET /cards/{public_slug}
docs/
  api-contract.md   API 계약 (명세 확정)
smoke.sh            계약 검증 스크립트
```

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
   아직 코드가 아니다. 실제 PostgreSQL에 올려서 성립하는지 확인한다.
3. **스텁 → 실제 조회 교체** — `app/stubs.py`를 지우고 리포지터리 계층을 넣는다.
   응답 형태는 그대로라 Flutter 쪽은 고칠 것이 없어야 한다.
4. **비밀번호 해싱(bcrypt)과 JWT 발급** — 지금은 고정 문자열이다.
5. **영상 업로드(SFR-001)와 analysis_job 큐** — 데이터 파이프라인과의 접점.
