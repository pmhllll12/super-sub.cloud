---
layout: page
title: "3. rbenv로 Ruby 본체 설치"
permalink: /guide/03-ruby-install/
---

```bash
rbenv install 3.3.5
```

최신 3.x 안정 버전을 확인한 후 지정할 수 있습니다. 이 과정은 CPU를 사용해서 소스를 빌드하므로 수 분 걸릴 수 있습니다.

완료되면 전역 버전을 지정하고 확인합니다.

```bash
rbenv global 3.3.5
ruby -v
```

---

[← 이전: rbenv 설치 및 셀 초기화]({{ "/guide/02-rbenv/" | relative_url }}) · [목차]({{ "/toc/" | relative_url }}) · [다음: Jekyll과 Bundler 설치 →]({{ "/guide/04-jekyll-bundler/" | relative_url }})
