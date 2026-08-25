# user — 부록 D 도메인 ① 사용자·팀

가입·로그인·내 정보·팀 소속을 담당한다.

> **로그인을 별도 컨텍스트로 빼지 않는 이유:** 로그인은 `user`와 `user_credential`을
> 함께 읽는다. 폴더를 나누면 로그인 쪽이 이쪽 저장소를 임포트해야 하고, 그게 곧
> 컨텍스트끼리 직접 얽히는 것이다. **같은 것을 다루면 같은 폴더에 둔다.**

## 대응 테이블

| 테이블 | 여기서 |
|---|---|
| `user` | `domain/entities.py` → `User` |
| `user_credential` | 아직 없음 — DB가 붙을 때 `adapter/outbound/`로 |
| `team_member` | `domain/entities.py` → `Membership` |
| `team` | `Membership`에 이름·지역으로 펼쳐 담는다 |

`sport`·`position`은 아직 안 쓴다. 매칭(도메인 ④)이 들어올 때 필요해진다.

## 규칙이 있는 곳

| 규칙 | 위치 | 근거 |
|---|---|---|
| 이메일 정규화 (대소문자·공백) | `domain/value_objects.py` → `Email.of` | `user.email` 유일 제약 (D.7) |
| 탈퇴한 소속 거르기 | `domain/rules.py` → `active_memberships` | `team_member.left_at` 소프트 삭제 |
| 비밀번호 8자 이상 | `domain/value_objects.py` → `Password` | 계약 문서 2장 |
| 로그인 실패를 구분하지 않기 | `application/use_cases.py` → `LoginUseCase` | 가입 여부 노출 방지 |

## 아직 안 한 것

- 비밀번호 해싱(bcrypt) — 저장할 곳이 없다
- 진짜 JWT — 토큰은 `app/security.py`가 스텁으로 발급한다
- 소셜 로그인 — `user_identity` 테이블만 추가하면 붙도록 잡아 두었다
