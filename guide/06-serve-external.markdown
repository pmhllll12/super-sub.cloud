---
layout: page
title: "6. 서버에서 외부 접근 가능하게 실행"
permalink: /guide/06-serve-external/
---

헤드리스 서버라면 외부에서 접근해야 하므로 아래와 같이 실행하세요.

```bash
bundle exec jekyll serve --host 0.0.0.0 --port 4000
```

`--host 0.0.0.0`을 빠뜨리면 localhost에만 바인딩되어 Tailscale이나 다른 기기에서 접속이 안 됩니다.

Tailscale 매쉬에 연결된 다른 기기에서 아래 주소로 접속해 미리보기할 수 있습니다.

```
http://<odyssey-tailscale-ip>:4000
```

---

[← 이전: 새 Jekyll 사이트 생성]({{ "/guide/05-new-site/" | relative_url }}) · [목차]({{ "/toc/" | relative_url }}) · [다음: (선택) systemd 등록 →]({{ "/guide/07-systemd/" | relative_url }})
