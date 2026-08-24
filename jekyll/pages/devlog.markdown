---
layout: page
title: 개발 로그
permalink: /devlog/
---

{% if site.posts.size > 0 %}
<ul class="post-list">
  {% for post in site.posts %}
  <li>
    <span class="post-meta">{{ post.date | date: "%Y-%m-%d" }}</span>
    <h3>
      <a class="post-link" href="{{ post.url | relative_url }}">{{ post.title | escape }}</a>
    </h3>
  </li>
  {% endfor %}
</ul>
{% else %}
*(아직 등록된 개발 로그가 없습니다.)*
{% endif %}

[← 표지]({{ "/" | relative_url }})
