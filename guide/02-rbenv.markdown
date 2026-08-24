---
layout: page
title: "2. rbenv 설치 및 셀 초기화"
permalink: /guide/02-rbenv/
---

```bash
curl -fsSL https://github.com/rbenv/rbenv-installer/raw/HEAD/bin/rbenv-installer | bash
```

rbenv와 ruby-build 플러그인을 함께 설치합니다. 설치 후 안내 문구대로 `~/.bashrc`에 아래 줄을 추가하고 적용합니다.

```bash
eval "$(rbenv init - bash)"
```

```bash
source ~/.bashrc
```

헤드리스에서 SSH로 접속해서 작업하신다면 이 설정이 그대로 유지됩니다.

---

[← 이전: 빌드 의존성 패키지 설치]({{ "/guide/01-dependencies/" | relative_url }}) · [목차]({{ "/toc/" | relative_url }}) · [다음: rbenv로 Ruby 본체 설치 →]({{ "/guide/03-ruby-install/" | relative_url }})
