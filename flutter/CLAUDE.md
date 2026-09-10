# flutter/ — 앱

> **소유: 백성검(프론트·웹/앱).** 웹(`www/`)과 같은 얼굴을 가진 Flutter 앱이다.
> 저장소 전체 규칙(브랜치·미결 항목·공개 사이트에 인프라 식별자 금지)은 루트
> `CLAUDE.md` 에 있다 — **여기 옮겨 적지 않는다.** 이 문서는 **이 폴더에서만
> 통하는 것**만 담는다.

Flutter · Dart · Riverpod. 화면 43개 파일(`lib/`), 테스트 18개 파일(`test/`).

```bash
flutter analyze     # 0건이어야 한다
flutter test
```

---

## 🔴 이 폴더의 뼈대 — 백엔드 없이 만들고, provider 한 줄로 붙인다

화면은 **리포지토리 인터페이스만** 안다. 구현체가 Mock 인지 API 인지 모른다.

```
lib/features/<기능>/data/<이름>_repository.dart        인터페이스 — 화면이 아는 전부
                        <이름>_repository_mock.dart    백엔드 없이 도는 것
                        <이름>_repository_api.dart     진짜 FastAPI
                        <이름>_providers.dart          🔴 교체는 여기 한 줄
```

**교체 지점은 셋뿐이다** — `auth_providers.dart` · `chat_providers.dart` ·
`sport_providers.dart`. 인증은 이미 `ApiAuthRepository` 로 넘어가 있다.

🔴 **화면·컨트롤러에서 구현체를 직접 만들지 않는다.** 한 곳이라도 `Mock…()` 을
직접 부르면 그 화면만 provider 를 안 따라가고, **교체했는데 일부만 바뀌는**
상태가 된다 — 그게 이 구조가 막으려는 유일한 것이다.

### 계약 테스트(`test/contract/`)를 지우지 않는다

`test/contract/*_contract.dart` 는 **구현체가 아니라 인터페이스의 시험**이다.
같은 파일을 Mock 과 API 구현체에 **둘 다** 물려 돌린다 — 그것이 "provider 한 줄
교체"가 진짜라는 유일한 보증이다.

- **여기에는 프로토콜의 성질만 둔다.** Mock 에만 있는 의무(지연 하한)나 개발용
  편의(`loginAs`)는 구현체별 테스트 파일로 내린다 — 계약에 섞으면 API 구현체가
  통과할 수 없는 조건이 된다
- 새 리포지토리를 만들면 **계약 테스트도 같이** 만든다

### Mock 은 일부러 느리고, 일부러 실패한다

지연 · 실패 · 빈 목록을 흉내낸다. 🔴 **즉시 성공하게 고치지 말 것** — 그러면
로딩 화면과 오류 화면을 아예 안 만들게 되고, 진짜 서버에 붙는 날 그 두 화면이
없다는 것을 알게 된다.

---

## 🔴 셰이더 둘은 규칙이 **정반대**다 — 헷갈리면 화면이 통째로 사라진다

연출이 `com.sumworship` 에서 온 것이라 셰이더가 두 갈래 있고, 쓰는 법이 다르다.

| | 잉크 번짐 (`ink_bleed.dart`) | 굴절 유리 (`glass_shader.dart`) |
|---|---|---|
| 어떻게 | `Paint()..shader` | `ui.ImageFilter.shader` |
| 좌표 | **논리 픽셀** | **물리 픽셀** |
| 가드 | **필요 없다** | 🔴 **`ImageFilter.isShaderFilterSupported` 필수** |

`ImageFilter.shader` 는 **Impeller 에서만** 동작하고 아니면 `UnsupportedError`
를 던진다. 잉크 쪽에 그 가드를 따라 붙이면 **지원하지 않는 기기에서 잉크까지
안 그려진다** — 안 그래도 되는 것을 막는 것이라, 두 파일의 주석이 서로를
가리켜 두었다.

### 유리 안에 유리를 넣지 않는다

안쪽 유리가 **아직 안 끝난 바깥**을 읽어 내용이 프레임째로 사라진다. 층을
쌓아야 하면 흐림 없이 **색만** 얹는다 — 로그인 버튼과 채팅 말풍선이 그 방식이다.

---

## 위젯 테스트에서 데인 것 둘

- 🔴 **무한 애니메이션이 있는 화면에서 `pumpAndSettle` 을 쓰지 않는다.** 도는
  테두리 빛 · 로딩 인디케이터가 안 멎어서 **10분 타임아웃까지 간다.**
  `pumpWidget` → 트리거 → `pump(500ms)` 관용구를 쓴다.
  (무한 애니메이션이 없는 화면은 써도 된다 — `profile_screen_test.dart` 가 그렇다.
  **화면마다 다르므로 옆 파일을 보고 따라 쓰지 말고 그 화면을 보고 정한다.**)
- 🔴 **`pumpWidget` 전에 Mock 의 `Future` 를 `await` 하지 않는다.** 가짜 시계가
  안 흘러 그대로 멈춘다.

---

## 백엔드 주소

`lib/core/network/api_config.dart` 의 `apiBaseUrl` 하나다. 기본값은
`127.0.0.1:8000` 이고 **실행 시 덮는다.**

```bash
flutter run --dart-define=API_BASE_URL=http://<PC 주소>:8000/api/v1
```

실기기를 USB 로 붙였으면 `adb reverse tcp:8000 tcp:8000` 로 기기의 localhost 를
이 PC 로 이어 주면 기본값 그대로 된다.

🔴 **주소를 코드에 박지 않는다** — 이 저장소는 공개이고, 루트 `CLAUDE.md` 의
「공개 사이트에 인프라 식별자를 쓰지 않습니다」가 그대로 적용된다.

---

## 🔴 알려진 구멍 — `AuthException` 이 `code` 를 버린다

`AuthException` 이 `message` 만 갖고 있어서 **에러 `code` 로 분기할 수단이
없다.** 그래서 429 `TOO_MANY_REQUESTS` 를 다른 실패와 가를 수가 없다 — 미결
항목 `jin` 2·4번이 이것을 **선행 조건**으로 걸어 두었다.

고칠 때는 `code` 와 `retryAfter` 를 함께 싣는다. **웹(`www/`)이 같은 일을 이미
했다**(`src/lib/api/client.ts` 의 `ApiCallError` · `retryAfterSeconds`) — 그쪽
모양을 따라가면 두 클라이언트의 동작이 갈리지 않는다.

---

## 웹과 앱은 서로를 베끼지 않는다 — 값의 출처가 한쪽이다

색·크기 토큰의 **원본은 이 폴더다.** `www/src/app/globals.css` 의 `--ss-*` 는
여기서 옮겨 간 것이고 주석에 줄 번호까지 적혀 있다.

🔴 **그래서 여기 값을 바꾸면 웹이 조용히 갈린다.** 토큰을 손볼 때는
`www/` 쪽도 같이 보고, 웹만 다르게 갈 값이면 **그 이유를 웹 주석에 남긴다**
(인트로 구간 길이가 그런 경우다 — `www/docs/2026-08-28-작업-현황.md` §5).

새 화면을 만들기 전에 **`www/docs/2026-08-31-앱-이식-지침.md`** 를 읽는다 —
웹을 먼저 만들고 앱으로 옮기는 순서라, 그때 재설계할 일을 지금 안 만들기 위한
규칙 여섯이 거기 있다.

---

## 관련 문서

- `docs/작업일지.md` — 회차별로 **무엇을 왜 그렇게 했는지**. 위 함정들의 출처다
- `docs/2026-08-25-flutter-app-design.md` — 설계
- `docs/plans/` — 구현 계획
- `fastapi/docs/api-contract.md` — **백엔드 계약. 화면을 만들기 전에 여기부터**
- `fastapi/docs/client-contract-changes.md` — 🔴 **반영할 변경 목록.**
  고치기 전에 그 문서의 「먼저 확인」을 실제로 돌린다. 이미 됐으면 손대지 않는다
