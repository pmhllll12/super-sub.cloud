# 웹을 앱과 같은 화면으로 — 디자인 이식 설계

> **상태:** 설계 승인됨, 구현 전 · 2026-08-28
> **담당:** 백성검 (프론트·웹)
> **선행:** `www/docs/2026-08-28-www-webapp-design.md` (웹앱 뼈대 — 이미 구현·배포됨)
> **원본:** `flutter/lib/` — 값은 전부 여기서 그대로 가져온다

## 0. 정해진 것

| | |
|---|---|
| 목표 | 웹 화면을 **Flutter 앱과 같은 화면 구성**으로 만든다 |
| 배치 | 데스크톱 재배치 — 앱의 재질과 구성을 쓰되 넓은 화면에 맞춘다 |
| 하단 내비바 | **유지한다** (아래 2절) |
| 셰이더 | 이식하지 않는다 (아래 6절) |

## 1. 디자인 토큰 — 앱에서 그대로 가져온다

추측하지 않는다. 아래 값은 전부 `flutter/lib/` 에 있는 것을 옮긴 것이다.

| 토큰 | 값 | 출처 |
|---|---|---|
| 배경 | `#000000` | `home_screen.dart` `_kHomeBg` |
| 전경 | `#FFFFFF` | `home_screen.dart` `_kOnDark` |
| 강조(시드) | `#70ED88` | `app_theme.dart` `AppTheme.seed` |
| 에러 | `#FF8A80` | `login_screen.dart` |
| 사진 스크림 | `#00000026` (15%) | `login_screen.dart` `_kPhotoScrim` |
| 시트 반경 | `28px` | `login_screen.dart` `_kSheetRadius` |
| 버튼 높이 | `54px` | `_kButtonHeight` |
| 버튼 반경 | `27px` (알약) | `_kButtonRadius` |
| 버튼 라벨 | `16px` | `_kButtonLabel` |
| 워드마크 크기 | `34px` | `brand_mark.dart` `kBrandLandedSize` |
| 워드마크 자간 | `크기 × 1.2 / 44` | `BrandMark.letterSpacingFor` |

**폰트 세 벌:**

- **Rubik** — 본문·UI. `next/font/google`
- **RubikGlitch** — 워드마크 `SUPERSUB` 전용. 다른 데 쓰지 않는다
- **Material Symbols Outlined** — 내비 아이콘. 앱이 구형 Material Icons 가 아니라 **Material Symbols** 를 쓰는 이유가 `floating_nav_bar.dart` 주석에 적혀 있다(획 두께·글리프 유무). 웹도 같은 글리프를 써야 줄이 같아 보인다. `material-symbols` npm 패키지로 **자체 호스팅**한다 — 외부 요청을 늘리지 않는다

## 2. 하단 플로팅 내비바 — 유지한다

처음에는 "데스크톱이면 상단 내비"라는 관습을 따라 없애려 했으나 되돌렸다. 근거가 없었고, 잃는 것이 컸다:

- **이 제품에서 가장 알아보기 쉬운 형태다.** 로고 모양으로 파인 노치가 있는 알약형 바는 다른 데 없다
- **로고 비행의 도착지가 여기다.** 바를 없애면 앱의 대표 연출이 성립하지 않는다
- 데스크톱에서도 문제없다 — 가운데 정렬하고 최대폭만 잡으면 된다

**구성은 앱과 같다** (`floating_nav_bar.dart`):

| 자리 | 앱 | 웹에서 가는 곳 |
|---|---|---|
| 0 (로고 알약) | 홈 | `/home` |
| 1 | `Symbols.videocam` | `/analysis` |
| 2 | `Symbols.sports_soccer` | 용병 매칭 — 준비 중 |
| 3 | `Symbols.id_card` | `/me/card` |
| 4 (메뉴) | `Symbols.format_list_bulleted_add` | 프로필·로그아웃 |

**로그인하지 않은 화면(`/`, `/login`, `/signup`, `/c/{slug}`)에서는 바를 숨긴다.** 갈 데가 없는 바를 띄우면 누를 곳 없는 버튼만 보여주는 셈이다.

## 3. 화면

앱에 있는 `/home` 을 웹에도 만든다. 지금 웹에는 없어서, 로그인 후 갈 곳이 프로필뿐이다.

| 경로 | 내용 | 앱 대응 | 인증 |
|---|---|---|---|
| `/` | 랜딩 — 워드마크(글리치) + 사진 + CTA | 웹 전용 | – |
| `/login` | 중앙 글래스 시트, 배경 사진 | `login_screen.dart` | – |
| `/signup` | 로그인과 같은 시트 | 웹 전용 | – |
| `/home` | **글래스 카드 6개 런처** | `home_screen.dart` | 필요 |
| `/analysis` | 영상 분석 — 준비 중 | `video_analysis_screen.dart` | 필요 |
| `/me` | 내 프로필 | `profile_screen.dart` | 필요 |
| `/me/card` | 내 선수 카드 | – | 필요 |
| `/c/[slug]` | 공개 선수 카드 | 웹 전용 | – |

**`/home` 의 카드 6개** — `home_screen.dart` 의 `_kDestinations` 를 그대로 옮긴다:

1. 영상 분석 (`videocam`) → `/analysis`
2. 용병 매칭 (`sports_soccer`) → 준비 중
3. 내 선수 카드 (`id_card`) → `/me/card`
4. 내 팀 (`groups`) → 준비 중
5. 레슨 · 코치 (`school`) → 준비 중
6. 내 프로필 (`person`) → `/me`

앱은 준비 중인 항목에 스낵바를 띄운다. 웹도 같은 문구(`… — 준비 중입니다`)를 쓰되, 스낵바 대신 카드에 표시를 둔다 — 눌러야 알 수 있는 것보다 낫다.

## 4. 컴포넌트

```
www/src/components/ui/
  BrandMark.tsx      # SUPERSUB — RubikGlitch, 자간 공식 그대로
  GlassPanel.tsx     # backdrop-filter + 테두리 + 상단 하이라이트 밴드
  PillButton.tsx     # 높이 54 / 반경 27, primary(민트) · ghost(테두리)
  Field.tsx          # 라벨 + 입력
  FloatingNavBar.tsx # 로고 노치 + 아이콘 3 + 메뉴
```

**글래스 패널**은 앱의 `glass_panel.dart` 를 CSS 로 옮긴다 — `backdrop-filter: blur()`, 흰색 낮은 불투명도 바탕, 흰색 테두리, 그리고 위쪽에 앱의 `0xE6FFFFFF` 하이라이트 밴드에 해당하는 그라디언트.

**🔴 접근성 계약을 깨뜨리지 않는다.** Task 7·8 의 테스트가 `getByLabelText('이메일')`, `getByLabelText('비밀번호')`, `getByLabelText('닉네임')`, `getByRole('button', { name: '로그인' })`, `role="alert"`, `role="status"` 로 요소를 집는다. 마크업을 바꾸되 이 접점은 그대로 둔다. `Field.tsx` 가 `<label>` 로 감싸는 형태를 유지하면 된다.

## 5. 자산

`flutter/assets/images/` 의 세 장을 `www/public/` 로 **복사**한다 (심볼릭 링크가 아니라 복사 — Vercel 빌드가 `www/` 밖을 안 본다):

| 파일 | 쓰는 곳 |
|---|---|
| `home_figure.jpg` | 랜딩 우측 |
| `player_mono.jpg` | 카드 화면 배경 |
| `ink_field.png` | 전역 배경 질감 (낮은 불투명도) |

폰트는 복사하지 않는다 — Rubik 과 Rubik Glitch 는 Google Fonts 에 있어 `next/font/google` 로 가져온다.

## 6. 이 범위에 넣지 않은 것

- **프래그먼트 셰이더 2개** (`liquid_glass.frag`, `ink_bleed.frag`) — GLSL 이라 WebGL 이식이 필요하다. 별도 작업
- **로그인 → 홈 잉크 전환** — 위 셰이더에 의존한다
- **2.5초 인트로 게이트** — 랜딩은 공유 링크로 열리는 자리다. 첫 화면을 2.5초 막으면 안 된다
- **로고 비행 연출** — 하단 바를 유지했으므로 도착지는 살아 있다. 다만 View Transitions API 는 브라우저 지원이 고르지 않아 이번에는 넣지 않는다. 나중에 "되는 브라우저에서만" 붙이는 편이 낫다
- **`design_scale` 의 1080px 환산** — 데스크톱 재배치라 옮기지 않는다. CSS 로 다시 잡는다

## 7. 다음 단계

1. 구현 계획 → `www/docs/plans/`
2. 토큰·폰트·자산 → 컴포넌트 → 셸(내비바) → 화면 순으로 쌓는다
3. 기존 테스트 40개가 계속 통과해야 한다
