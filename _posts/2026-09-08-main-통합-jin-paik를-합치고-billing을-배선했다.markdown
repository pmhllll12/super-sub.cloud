---
layout: default
title: "main 통합 — jin·paik를 합치고 billing 배선을 마쳤다"
date: 2026-09-08
nav_exclude: true
---

`ho` 병합에 이어 나머지 브랜치도 `main`에 합쳤다. `min`은 이미 `main`에
전부 포함돼 있어 병합할 것이 없었고(`origin/main..origin/min` 0건),
`jin`은 충돌 없이 그대로 합쳐졌다.

`paik`는 두 곳이 충돌했다.

- `fastapi/docs/client-contract-changes.md` — `paik`가 갈라져 나온 시점 이후
  `main`(정어진)이 이미 「19번」을 두 개(19·20) 더 채웠는데, `paik`도 자기
  브랜치에서 새 항목을 「19번」으로 붙여 번호가 겹쳤다. `main` 쪽 19·20·21은
  그대로 두고 `paik`의 과금 항목을 **22번**으로 이어 붙였다.
- `jekyll/pages/pending.markdown` 5번(공개 여부) — 정어진이 "네 조각 다
  됐다"고 처리 기록을 남긴 지점에 백성검도 같은 날 "재생 주소는 12번으로
  뗐다"는 메모를 붙여 두 편집이 겹쳤다. 어느 쪽이 맞는지 내가 판단할 수
  없어서(배포 확인이 필요한 사안) **둘 다 남기고**, 12번이 아직 `✅ 해소`로
  안 닫혀 있다는 점을 인용구로 덧붙여 정어진·백성검이 직접 정리하도록
  했다.

병합 뒤 `alembic heads`가 둘로 갈라져 있었다 — `paik`의
`20260908_billing_tables.py`가 `down_revision = None`(주석: "🔴 정어진이
채운다")인 채였다. `jin`이 이미 만든 `10f68718757d`(video_kept) 뒤로
체인했다.

이어서 `fastapi/CLAUDE.md`가 경고하는 배선 누락 셋을 실제로 만났다 —
`app/billing`이 `app/main.py` 라우터·`alembic/env.py` ORM 등록·
`tests/test_architecture.py`의 `CONTEXTS`에 하나도 안 걸려 있었고,
`tests/user/adapter/test_auth_router.py`의 OpenAPI 경로 화이트리스트도
갱신이 안 돼 있었다. 넷 다 채워 넣었다(`fix(fastapi): billing 패킷(paik)을
main에 배선한다`).

병합·배선 뒤 `pytest`는 435 통과 · DB 통합 테스트만 이 환경의 Postgres
인증 실패(`password authentication failed for user "supersub"`)로
실패/에러 — 이 merge 전부터 있던 환경 문제라 손대지 않았다. `alembic
heads`는 하나, `jekyll build`도 정상, 인프라 식별자 grep도 0건 확인 뒤
`origin/main`에 push했다.

**다음에 할 일**: `main`이 `paik`·`jin`보다 여러 커밋 앞서 있다 — 각
브랜치로 되병합(sync)할지는 아직 안 물어봤다. `jekyll/pages/pending.markdown`
5번의 정어진·백성검 메모 상충은 당사자 확인이 필요하다.

[← 목차로](/toc/)
