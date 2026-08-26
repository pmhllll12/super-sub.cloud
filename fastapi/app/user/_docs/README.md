# user — 부록 D 도메인 ① 사용자·팀

가입·로그인·내 정보·팀 소속을 담당한다.

> **로그인을 별도 컨텍스트로 빼지 않는 이유:** 로그인은 `user`와 `user_credential`을
> 함께 읽는다. 폴더를 나누면 로그인 쪽이 이쪽 저장소를 임포트해야 하고, 그게 곧
> 컨텍스트끼리 직접 얽히는 것이다. **같은 것을 다루면 같은 폴더에 둔다.**

## 대응 테이블

| 테이블 | 여기서 |
|---|---|
| `user` | `domain/entities/user_entity.py` |
| `user_credential` | 아직 없음 — DB가 붙을 때 `adapter/outbound/`로 |
| `team_member` | `domain/entities/membership_entity.py` |
| `team` | `MembershipEntity`에 이름·지역으로 펼쳐 담는다 |

`sport`·`position`은 아직 안 쓴다. 매칭(도메인 ④)이 들어올 때 필요해진다.

## 인바운드 → 아웃바운드

```
auth_router.py          SignupSchema (HTTP)
  ↓ SignupCommand (DTO)
signup_use_case.py      입력 포트 (ABC) — 라우터는 이 타입만 안다
  ↓
signup_interactor.py    규칙 적용, 엔티티 ↔ DTO 변환
  ↓
user_port.py            출력 포트 (ABC) — 엔티티·값 객체로 말한다
  ↓
user_stub_repository.py 구현. DB 가 붙으면 user_pg_repository.py 로 바뀐다
  ↑ SignupResult (DTO)
auth_schema.py          from_attributes 로 DTO → 응답 스키마
```

**라우터는 엔티티를 모르고 도메인은 HTTP를 모른다.** DTO 가 그 경계다.
`tests/test_architecture.py` 가 이 규칙을 실제로 검사한다.

## 규칙이 있는 곳

| 규칙 | 위치 | 근거 |
|---|---|---|
| 이메일 정규화 (대소문자·공백) | `domain/value_objects/email_vo.py` | `user.email` 유일 제약 (D.7) |
| 탈퇴한 소속 거르기 | `domain/rules/membership_rules.py` | `team_member.left_at` 소프트 삭제 |
| 비밀번호 8자 이상 | `domain/value_objects/password_vo.py` | 계약 문서 2장 |
| 로그인 실패를 구분하지 않기 | `application/use_cases/login_interactor.py` | 가입 여부 노출 방지 |

## 아직 안 한 것

- 비밀번호 해싱(bcrypt) — 저장할 곳이 없다
- 진짜 JWT — 토큰은 `app/security.py`가 스텁으로 발급한다
- `adapter/outbound/orm/` 과 `mappers/` — ORM 이 생길 때 함께 만든다
- 소셜 로그인 — `user_identity` 테이블만 추가하면 붙도록 잡아 두었다
