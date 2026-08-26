"""외부 제공자가 확인해 준 신원.

포트를 넘나드는 값이라 값 객체로 둔다(출력 포트는 엔티티·값 객체로 말한다).

🔴 **`subject` 가 사람의 식별자다. `email` 이 아니다.** 이메일은 사용자가 바꿀 수
있고 조직 계정은 회수 후 재발급되기도 한다. 이메일로 사람을 찾으면 그 순간 남의
계정이 넘어간다. 이메일은 **가입할 때 채워 넣는 부수 정보**로만 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalIdentity:
    provider: str
    subject: str
    email: str
    # 제공자가 이메일 소유를 확인했는가. 확인되지 않은 이메일로는 기존 계정에
    # 연결하지 않는다 — 아무 이메일이나 적어 남의 계정을 가져갈 수 있게 된다.
    email_verified: bool
    display_name: str
