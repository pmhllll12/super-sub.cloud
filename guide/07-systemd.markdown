---
layout: default
title: "7. (선택) 지속적 미리보기가 필요하면 systemd 등록"
permalink: /guide/07-systemd/
nav_exclude: true
---

Odyssey가 항상 켜져있는 홈서버라는 건, 개발 중에는 Jekyll을 systemd(또는 Docker 컨테이너로 dreamscape 네트워크에 포함)로 띄워 지속적으로 미리보기 서버를 띄울 수도 있다는 뜻입니다.

다만 실제 배포는 GitHub Pages가 빌드를 맡으므로, 서버에서의 `jekyll serve`는 어디까지나 로컬 미리보기용입니다.

---

[← 이전: 서버에서 외부 접근 가능하게 실행]({{ "/guide/06-serve-external/" | relative_url }}) · [목차]({{ "/toc/" | relative_url }})
