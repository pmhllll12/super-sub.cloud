---
layout: page
title: "4. Jekyll과 Bundler 설치"
permalink: /guide/04-jekyll-bundler/
---

```bash
gem install jekyll bundler
```

rbenv 환경이므로 sudo 없이도 사용자 권한으로 설치됩니다. 설치 후 명령어 경로를 갱신하고 버전을 확인합니다.

```bash
rbenv rehash
jekyll -v
```

---

[← 이전: rbenv로 Ruby 본체 설치]({{ "/guide/03-ruby-install/" | relative_url }}) · [목차]({{ "/toc/" | relative_url }}) · [다음: 새 Jekyll 사이트 생성 →]({{ "/guide/05-new-site/" | relative_url }})
