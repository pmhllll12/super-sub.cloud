# Super-Sub 백엔드 API

생활체육 용병 스카우팅 & RAG 검증 플랫폼(Super-Sub)의 백엔드 API 서버.

저장소 루트는 제안서 Jekyll 사이트이고 이 폴더가 백엔드다.
데이터 모델의 정본은 **부록 D — 데이터베이스 ERD**(32테이블·6도메인,
`jekyll/chapters/부록D-데이터베이스ERD.markdown`)다.

> **상태:** 진행중 — 뼈대만 있다 (기동 확인됨) · 2026-08-25 확인
> **확인:** `.venv/bin/uvicorn app.main:app` 후
> `curl -s localhost:8000/health` → `{"status":"ok","env":"local","db_configured":false}`
> **메모:** 엔드포인트는 `/health` 하나뿐이다. 실제 API는 계약을 팀과 맞춘 뒤 붙인다.
> DB 연결 코드는 아직 없다 — 붙을 RDS 인스턴스가 없다.

## 스택

| | |
|---|---|
| 언어 | Python 3.14 |
| 프레임워크 | FastAPI |
| DB | Aurora PostgreSQL + pgvector (미구축) |

## 실행

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env          # 값은 각자 채운다

.venv/bin/uvicorn app.main:app --reload
```

기동되면 `http://localhost:8000/docs` 에서 OpenAPI 문서를 볼 수 있다.

## 구조

```
app/
  main.py     FastAPI 앱과 라우트
  config.py   환경변수 (키 이름은 super-sub.cloud 의 .env.example 을 따른다)
```

## 다음 할 일

1. **API 계약 확정** — 인증(SEC-003)과 선수 카드 조회(player_card).
   스프린트 2(09.01~)에 Flutter 쪽에서 로그인·선수 카드 화면을 구현하므로
   그 전에 엔드포인트 형태가 정해져 있어야 한다.
2. **부록 D ERD → 실제 DDL 검증** — D.6 삭제 연쇄와 D.7 유일 제약 17건이
   아직 문서에만 있다. 로컬 PostgreSQL 에 올려서 성립하는지 확인한다.
3. **영상 업로드(SFR-001)와 analysis_job 큐** — 데이터 파이프라인과의 접점.
