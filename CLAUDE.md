# CLAUDE.md

이 저장소는 **Super-Sub(멀티모달 용병 스카우팅 & RAG 검증 플랫폼)** 개발 제안서를 문서화하는 Jekyll 정적 사이트입니다. 아래 규칙을 따라 페이지를 작성/수정합니다.

## 팀 구성

(2026.08.26 재배정)

- **박민호** — PM (요구사항/일정 관리, 스프린트 진행, QA 총괄)
- **백성검** — 프론트·웹 (Flutter 앱 UI/UX, 화면 구현, 웹 페이지)
- **정어진** — 백엔드·파이프라인 (DB·API, 영상 수집·전처리, 분석 파이프라인, 배포)
- **정상호** — AI 에이전트 개발 (RAG 검증, 실력 판단 로직)

개발 기간: 2026.08.20 ~ 2026.10.27 (10주)

## 환경 및 로컬 미리보기

- Ruby는 rbenv로 관리 (전역 버전 3.3.12). 새 셸에서 `ruby`/`jekyll`/`bundle`을 쓰려면 먼저:
  ```
  export PATH="$HOME/.rbenv/bin:$PATH"
  eval "$(rbenv init - bash)"
  ```
- 로컬 미리보기는 systemd 서비스 `supersub-preview.service`가 이 저장소 루트를 `WorkingDirectory`로, `--host 0.0.0.0 --port 4000 --baseurl ""`로 상시 구동 중입니다. (참고: 포트 4001은 `demo/` 연습 사이트가 별도 로컬 경로 `/home/hi/projects/demo`에서 자체 서비스로 구동 중이며, 이 저장소와는 무관합니다.)
- `_config.yml`을 바꾼 경우에만 서비스 재시작이 필요합니다:
  ```
  sudo systemctl restart supersub-preview.service
  ```
  (세션에 sudo 권한이 없으면 사용자에게 위 명령 실행을 요청할 것.)
- 페이지 내용만 바꾼 경우 `listen`이 자동 재빌드하므로 별도 조치 불요.
- `_site/`, `.jekyll-cache/`는 빌드 산출물이므로 커밋하지 않습니다 (`.gitignore`에 포함).
- `.env`, `.env.local`도 `.gitignore`에 포함되어 있습니다 — 이 프로젝트 문서화 작업과 무관한 별도 파일이니 건드리지 않습니다.

## 저장소 구조

Jekyll 소스 루트는 **저장소 루트 자체**입니다 (`_config.yml`이 여기 있음). 사이트 인프라와 콘텐츠를 아래처럼 분리합니다.

- **루트**: `_config.yml`, `Gemfile`, `Gemfile.lock`, `404.html`, `_layouts/`, `assets/main.scss`, `.github/workflows/pages.yml`, `supersub-preview.service`
- **`guide/`**: 개발환경 셋업 가이드 (7단계, 기존 자료 — 목차에는 연결되어 있지 않음)
- **`demo/`**: 완전히 별개의 연습용 Jekyll 사이트(영상자료 디지털화 사업 RFP 템플릿). 자체 `_config.yml`/`Gemfile`/레이아웃을 가진 독립 사이트라 루트 `_config.yml`의 `exclude:`에 등록되어 이 사이트 빌드에 포함되지 않습니다. **이 프로젝트 작업 중에는 건드리지 않습니다.**
- **`jekyll/`**: 계속 늘어나는 이 프로젝트의 콘텐츠 `.md` 파일 전용 폴더 (depth-2: `jekyll/<분류>/<파일>`)
  - `jekyll/pages/` — `index.markdown`(표지, `permalink: /`), `toc.markdown`(구 목차, 지금은 사이드바 대신 쓰이지 않는 레거시 링크용 — 아래 "목차" 절 참고), `devlog.markdown`(개발 로그 목록), `pending.markdown`(미결 항목), `1부-제안개요.markdown`/`2부-개발수행계획.markdown`/`부록.markdown`(사이드바 상위 그룹 랜딩 페이지, `has_children: true`)
  - `jekyll/chapters/` — 9개 챕터 + 부록 A~D 페이지 (`01-사업개요.markdown` ~ `09-산출물및향후계획.markdown`, `부록A-용어정의.markdown` ~ `부록D-데이터베이스ERD.markdown`)
  - `jekyll/sprints/` — 스프린트별 일자별 진행 로그 페이지 (`스프린트1.markdown`, `스프린트2.markdown`, …)

새로운 종류의 콘텐츠가 생기면 `jekyll/` 아래 알맞은 하위 폴더를 만들어 넣습니다. **콘텐츠 md 파일을 저장소 루트나 `jekyll/` 최상단에 바로 만들지 않습니다.**

파일 위치는 `permalink` front matter와 무관합니다 (Jekyll은 permalink 기준으로 URL을 생성하므로 파일을 옮겨도 링크는 안 깨집니다).

## 테마 (Just the Docs)

이 사이트는 `dev.life-tutorial.com`을 참고해 **Just the Docs** Jekyll 테마(`_config.yml`의
`theme: just-the-docs`)를 씁니다. 좌측 사이드바 트리·검색·"위로" 버튼 등 UI는 테마가
기본 제공하며, 이 저장소 쪽에서 직접 만든 레이아웃은 없습니다 (`_layouts/`도 없음).
이 프로젝트 전용 커스텀 CSS(ERD 이미지, 칸반 보드)는 `assets/main.scss`에 있고
`_includes/head_custom.html`이 그걸 테마 `<head>`에 끼워 넣습니다. 테마 기본 폰트·톤은
그대로 두고 손대지 않습니다.

사이드바 트리는 프론트매터의 `nav_order`(형제 간 정렬)와 `parent`/`grand_parent`(최대
3단계 중첩), `has_children: true`(하위 페이지를 거느리는 상위 페이지)로 자동 생성됩니다.
사이드바에 안 보이게 하려면 `nav_exclude: true`를 씁니다 (`index.markdown`, 구 `toc.markdown`,
`_posts/`의 모든 글, `404.html`이 이렇게 되어 있음).

## 페이지 작성 규칙

### 상위 그룹 랜딩 페이지 (`jekyll/pages/1부-제안개요.markdown`, `2부-개발수행계획.markdown`, `부록.markdown`)
사이드바 트리의 1단계 그룹(`I 부`/`II 부`/`부록`)을 만들기 위한 페이지입니다. `has_children: true`로
선언해두면 Just the Docs가 이 페이지 본문 아래에 자식 페이지 목록을 자동으로 붙여줍니다. 새 그룹이
필요할 때만 추가하고, 그 외엔 건드릴 필요 없습니다.

### 챕터 페이지 (`jekyll/chapters/`)
```yaml
---
layout: default
title: <챕터 제목>
permalink: /<번호>-<슬러그>/   # 부록은 /부록A-<슬러그>/
parent: I 부. 제안 개요        # 또는 "II 부. 개발 수행 계획" / "부록" — 위 랜딩 페이지의 title과 정확히 일치해야 함
nav_order: <부 안에서의 순서>
---
```
- 하위 세부항목은 `## N) 세부항목명` 헤딩으로 구분합니다.
- 아직 안 쓴 내용은 `*(내용 작성 예정)*`로 표시합니다.
- 페이지 맨 아래에 `[← 목차로](/toc/)`를 넣어 구 목차 페이지와 서로 이동 가능하게 합니다 (사이드바가
  주 내비게이션이라 필수는 아니지만 기존 관례상 유지).
- 챕터 7("개발 구현 계획")처럼 하위에 스프린트 로그를 거느리는 페이지는 `has_children: true`도 함께 씁니다.

### 구 목차 (`jekyll/pages/toc.markdown`)
Just the Docs 사이드바가 목차 역할을 대신하므로, 이 페이지는 `nav_exclude: true`로 사이드바에서
숨긴 **레거시 페이지**입니다. 표지(`index.markdown`)의 "목차 →" 링크와 각 챕터 하단 "← 목차로"
링크가 아직 이 페이지(`/toc/`)를 가리키므로 삭제하지 않고 내용만 유지합니다. 새 챕터를 추가해도
이 페이지를 갱신할 필요는 없습니다 — 사이드바 트리(`parent`/`nav_order`)만 맞으면 자동으로 반영됩니다.

### 스프린트 로드맵 & 칸반 (챕터 7 "개발 구현 계획" 전용 규칙)
- `07-개발구현계획.markdown`의 "4) 단계별 개발 일정"에 스프린트 로드맵 표(전체 5개 스프린트 × 담당자별 태스크)와 **현재 진행 중인 스프린트**의 칸반 보드를 유지합니다.
- 칸반 보드는 `<div class="kanban-board">` > `<div class="kanban-column">`(Backlog/To Do/In Progress/Done) > `<div class="kanban-card"><span class="role-tag role-{pm|front|backend|agent}">이름·역할</span>태스크</div>` 구조를 사용합니다 (스타일은 `assets/main.scss`에 정의됨).
- 칸반 보드는 **항상 현재 스프린트 상태만** 반영합니다. 스프린트가 끝나면: (1) 로드맵 표의 해당 Sprint 번호를 `jekyll/sprints/스프린트N.markdown` 링크로 연결 (2) 그 스프린트의 일자별 진행 내역을 `jekyll/sprints/스프린트N.markdown`에 표로 기록 (3) 칸반 보드를 다음 스프린트 내용으로 교체.
- 스프린트 로그 페이지 형식: `permalink: /스프린트N/`, `parent: 개발 구현 계획`, `grand_parent: II 부. 개발 수행 계획`, `nav_order: N`(사이드바에서 챕터 7 하위에 중첩), 날짜별 표(담당자 4명을 컬럼으로), 하단에 `[← 개발 구현 계획으로](/07-개발구현계획/)`.

## 진행사항(개발 로그) 작성 규칙

- **그날그날의 의사결정/이슈/변경사항**처럼 날짜가 있는 업데이트는 정적 페이지가 아니라 **Jekyll 포스트(`_posts/`, 저장소 루트)로 남깁니다.** 파일명은 `YYYY-MM-DD-짧은-제목.markdown`.
- front matter 예시 (Just the Docs엔 `post` 레이아웃이 없으므로 `default` + `nav_exclude` 사용):
  ```yaml
  ---
  layout: default
  title: "<이번 업데이트 한 줄 요약>"
  date: YYYY-MM-DD
  nav_exclude: true
  ---
  ```
- `jekyll/pages/devlog.markdown`(`/devlog/`)이 `_posts/`의 글을 자동으로 나열하므로 별도로 목록을 관리할 필요는 없습니다.
- 코드/설정 변경 이력은 git log로 확인 가능하므로 반복하지 않고, 그날 한 일·결정한 사항·다음 할 일을 간단히 기록합니다.
- **스프린트 로그(`jekyll/sprints/`)와의 구분**: 스프린트 로그는 "담당자별 계획된 일정" 표이고, 개발 로그(`_posts/`)는 "실제 있었던 일에 대한 자유 서술"입니다. 스프린트 진행 상황을 표로 갱신하는 것과 별개로, 특기할 만한 결정/이슈가 있으면 개발 로그에도 남깁니다.

## 미결 항목 (`jekyll/pages/pending.markdown`)

아직 해결되지 않은 이슈나 결정할 사항이 생기면 이 페이지에 목록으로 추가합니다. 해결되면 지우거나 완료 표시합니다.

**여기가 팀원 사이 요청·결정의 공통 입구입니다.** 다른 사람이 판단하거나 조치해야 하는 것은 자기 폴더 문서에만 두지 말고 여기에 한 항목으로 올립니다. 항목 끝에 담당·제기·기한을 답니다 — 담당과 제기가 다르면 담당자가 물어볼 상대가 문서에 있어야 합니다.

```
- **담당**: 이름 · **제기**: 이름 · **기한**: 시점
```

**항목에는 요약과 링크만 두고 상세는 원래 문서에 둡니다.** 같은 내용을 두 곳에 복사하면 한쪽만 고쳐져 어느 쪽이 맞는지 모르게 됩니다.

### 받은 요청을 처리할 때

1. **고치기 전에 이미 됐는지 확인합니다.** 요청은 쓰인 시점의 코드를 보고 쓴 것이라 그 사이 다른 방식으로 해결됐을 수 있습니다. **이미 만족하면 손대지 않고 무엇이 되어 있는지 알려줍니다** — 형태가 요청의 예시와 달라도 목적이 달성됐으면 그대로 둡니다.
2. **요청은 "이 파일을 고쳐라"가 아니라 "이 성질을 만족하라"로 씁니다.** 파일·함수 이름은 예시지 규격이 아니라고 밝히고, 확인 방법과 **하지 말아야 할 것**을 함께 적습니다.
3. **이미 보낸 것을 정정할 때는 드러냅니다** — "앞서 X라고 한 것을 정정합니다". 값만 조용히 바꾸면 받은 쪽은 자기가 잘못 읽은 줄 압니다.

### 남의 영역 문서와 어긋날 때

**고치지 말고 자기 쪽에 근거를 남기고 미결 항목으로 올립니다.** 남의 문서를 직접 고치면 머지 충돌이 되고, 그냥 두면 다음 사람이 또 밟습니다. 진단이 틀렸던 항목은 지우지 말고 **무엇이 어떻게 바뀌었는지 남깁니다** — 닫힌 경로를 적어 두면 같은 조사를 반복하지 않습니다.

## 마크다운 작성 시 주의사항

- kramdown은 `- ` 불릿 항목 텍스트가 `1. `, `2. `처럼 시작하면 이를 **중첩 순서 리스트로 잘못 해석**할 수 있습니다. 불릿 안에 번호 텍스트를 그대로 쓰고 싶다면 `1\.`처럼 이스케이프하거나 `1)` 형식을 씁니다. (단, `toc.markdown`의 하위 목록처럼 **의도적으로 실제 순서 리스트**를 쓰는 곳은 이스케이프하지 않습니다 — 위 "목차" 규칙 참고.)
- 표지(`index.markdown`)의 개발기간/팀명/링크 등이 바뀌면 `_config.yml`의 `title`도 함께 갱신합니다.
