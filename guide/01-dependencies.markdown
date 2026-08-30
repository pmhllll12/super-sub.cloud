---
layout: default
title: "1. 빌드 의존성 패키지 설치"
permalink: /guide/01-dependencies/
nav_exclude: true
---

```bash
sudo apt update && sudo apt install -y git build-essential libssl-dev libreadline-dev zlib1g-dev autoconf bison libyaml-dev libncurses5-dev libffi-dev libgdbm-dev
```

Ruby 빌드에 필요한 패키지를 먼저 깔아둡니다. 이게 없으면 rbenv가 Ruby를 소스로 빌드할 때 실패합니다.

---

[← 목차]({{ "/toc/" | relative_url }}) · [다음: rbenv 설치 및 셀 초기화 →]({{ "/guide/02-rbenv/" | relative_url }})
