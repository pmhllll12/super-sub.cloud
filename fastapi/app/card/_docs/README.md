# card — 부록 D 도메인 ③ 카드·호칭

선수 카드와 호칭을 담당한다.

> **`user_card`가 아니라 `card`인 이유:** "누구의 데이터가 필요한가"로 이름을 지으면
> 결국 전부 `user_`가 붙는다 — 매칭도 평가도 과금도 사용자를 참조한다.
> 부록 D는 **무엇인가**로 잘라 놨고, 그 묶음의 이름이 카드·호칭이다.

## 대응 테이블

| 테이블 | 여기서 |
|---|---|
| `player_card` | `domain/entities/card_entity.py` |
| `user_title` + `title_definition` | `domain/entities/title_entity.py` |
| `squad` · `squad_member` | `domain/entities/squad_entity.py` (2026-09-03) |

## 인바운드 → 아웃바운드

```
card_router.py            경로 파라미터
  ↓ MyCardQuery / PublicCardQuery (DTO)
my_card_use_case.py       입력 포트 (ABC)
  ↓
my_card_interactor.py     visible_titles / to_public 적용 → card_assembler 로 DTO 변환
  ↓
card_port.py              출력 포트 (ABC) — user_id 를 인자로 받는다
  ↓
card_stub_repository.py   구현. DB 가 붙으면 card_pg_repository.py 로 바뀐다
  ↑ MyCardResult / PublicCardResult (DTO)
card_schema.py            from_attributes 로 DTO → 응답 스키마
```

**`PublicCardResult` 에는 `id` 가 없다.** 공개 카드가 내부 식별자를 싣지 않는 것이
DTO 단계에서 이미 강제된다 — 응답 스키마에서 빼는 것에만 의존하지 않는다.

스쿼드(2026-09-03)도 같은 줄기다 — `squad_router.py` → `squad_use_cases.py` →
`squad_interactors.py` → `squad_port.py` → `squad_pg_repository.py`. 다른 점은
**`user` 컨텍스트의 테이블 넷**(`team`·`team_member`·`position`·`user`)을 원시
쿼리로 읽는다는 것이고, 그래서 `tests/card/adapter/test_squad_db.py` 가 컬럼 이름의
유일한 방어선이다.

## 🔴 이 컨텍스트가 지키는 설계 원칙 (부록 D.5)

스키마로 막아 놨어도 **응답에서 되살아나면 무의미하다.** 그래서 여기서 한 번 더 막고
`tests/card/domain/test_card_rules.py`가 엔티티·DTO·응답 모델 **셋 다** 검사한다.

| 원칙 | 출처 | 어떻게 |
|---|---|---|
| 카드에 수치 능력치를 노출하지 않는다 | 3.5 | `CardEntity`에 점수 필드 없음. `FORBIDDEN_CARD_FIELDS`가 세 계층을 검사 |
| 호칭은 미부여 방식으로만 작동한다 | 3.5 | `TitleEntity`는 부여된 것만. `earned: false` 같은 필드를 두지 않는다 |
| 전체 순위표를 두지 않는다 | 3.4 | 사용자 간 비교·정렬 유스케이스가 없다 |
| 공유는 슬러그로만 | SFR-009 | `to_public`이 내부 카드 id를 떨어뜨린다 |

**`titles`가 빈 배열인 것은 정상 상태다.** 화면에서 이것을 부정적으로 표시하면
미부여 방식 설계가 깨진다 — 백성검 쪽에서 확인이 필요하다.

## 아직 안 한 것

- 카드 생성·수정 — 카드가 어느 시점에 생기는지 미정
- 호칭 판정 (`title_criteria` 기반) — 지표(도메인 ②)가 나온 뒤
- `adapter/outbound/orm/` 과 `mappers/` — ORM 이 생길 때 함께 만든다
- 스쿼드 — 팀 단위 카드 묶음
