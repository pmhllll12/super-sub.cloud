---
layout: page
title: "5. 새 Jekyll 사이트 생성"
permalink: /guide/05-new-site/
---

원하는 경로(예: `~/projects/fin.ragtaylor.com`)에서 아래 명령으로 기본 사이트를 생성합니다.

```bash
jekyll new fin-site --force
```

이미 clone된 리포 안에서라면 다음과 같이 실행합니다.

```bash
jekyll new . --force
```

생성 직후 해당 디렉토리로 이동해 Gemfile의 의존성을 설치합니다.

```bash
bundle install
```

---

[← 이전: Jekyll과 Bundler 설치]({{ "/guide/04-jekyll-bundler/" | relative_url }}) · [목차]({{ "/toc/" | relative_url }}) · [다음: 서버에서 외부 접근 가능하게 실행 →]({{ "/guide/06-serve-external/" | relative_url }})
