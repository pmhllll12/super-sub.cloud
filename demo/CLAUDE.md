# CLAUDE.md

이 저장소는 "Demo" 사업의 진행사항 및 요구사항을 문서화하는 Jekyll 사이트입니다. 아래 규칙을 따라 페이지를 작성/수정합니다.

## 환경

- Ruby는 rbenv로 관리 (전역 버전 3.3.12). 새 셸에서 `ruby`/`jekyll`/`bundle`을 쓰려면 먼저:
  ```
  export PATH="$HOME/.rbenv/bin:$PATH"
  eval "$(rbenv init - bash)"
  ```
- 로컬 미리보기는 systemd 서비스 `jekyll-preview.service`가 `--host 0.0.0.0 --port 4000`으로 상시 구동 중 (부팅 시 자동 시작).
- 페이지/포스트 내용만 바꾼 경우 `listen`이 자동 재빌드하므로 별도 조치 불요. **`_config.yml`을 바꾼 경우에만** 서비스 재시작 필요:
  ```
  sudo systemctl restart jekyll-preview.service
  ```
  (이 저장소를 다루는 세션에 sudo 권한이 없다면, 사용자에게 위 명령 실행을 요청할 것.)
- `_site/`, `.jekyll-cache/`는 빌드 산출물이므로 커밋하지 않음 (`.gitignore`에 포함됨).

## 페이지 구조 (정적 보고서 챕터)

- 표지: `index.markdown` (`permalink: /`)
- 목차: `toc.markdown` (`permalink: /toc/`)
- 목차의 각 장은 별도 페이지 파일로 만든다. 파일명은 `장번호-장제목.markdown` (예: `01-사업개요.markdown`, `02-제안요청내용.markdown`), permalink은 `/장번호-장제목/`.
- 모든 정적 챕터 페이지의 front matter:
  ```yaml
  ---
  layout: page
  title: <장 제목>
  permalink: /<slug>/
  ---
  ```
- 각 챕터 페이지 하단에는 `[← 목차로](/toc/)` 링크를 넣어 목차와 서로 이동 가능하게 한다.
- 목차(`toc.markdown`)에 새 장을 추가할 때는 해당 항목을 실제 챕터 페이지로 링크한다 (`[1. 영상자료 디지털화 사업개요](/01-사업개요/)` 형태).

## 진행사항(진행 로그) 작성 규칙

- "진행사항"처럼 날짜가 있는 업데이트는 정적 페이지가 아니라 **Jekyll 포스트(`_posts/`)로 남긴다.** 파일명은 `YYYY-MM-DD-짧은-제목.markdown`.
- front matter 예시:
  ```yaml
  ---
  layout: post
  title: "<이번 업데이트 한 줄 요약>"
  date: YYYY-MM-DD
  ---
  ```
- 기본 생성된 `_posts/2026-08-20-welcome-to-jekyll.markdown` 예시 글은 실제 진행사항 기록을 쓰기 시작하면 지운다.
- 진행사항 글에는 그날 한 일, 결정한 사항, 다음 할 일을 간단히 기록한다. 코드/설정 변경 이력은 git log로 확인 가능하므로 반복하지 않는다.

## 마크다운 작성 시 주의사항

- kramdown은 리스트 항목 텍스트가 `1. `, `2. ` 처럼 시작하면 이를 **중첩 순서 리스트로 잘못 해석**한다. 원본 문서의 "1. 제목" 같은 번호를 항목 텍스트로 그대로 쓰고 싶을 때는 마침표를 `\.`로 이스케이프한다 (예: `- 1\. 사업개요`). `1)` 형식은 이 문제가 없다.
- 사업명/개발자/개발기간 등 표지 정보가 바뀌면 `index.markdown`과 `_config.yml`의 `title`을 함께 갱신한다.
