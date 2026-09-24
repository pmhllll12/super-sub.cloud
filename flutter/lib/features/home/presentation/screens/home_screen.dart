import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../intro/presentation/brand_mark.dart';
import '../../../../core/widgets/glass_pill.dart';
import '../../../../core/widgets/aurora_background.dart';
import '../../../../core/widgets/bar_menu.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../../core/widgets/glass_panel.dart';
import '../../../../core/widgets/silver_edge.dart';
import '../../../../core/widgets/screen_tint.dart';
import '../../../../core/widgets/silver_sweep_border.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../../core/network/api_client.dart';
import '../../../card/data/card_providers.dart';
import '../../../card/data/models/player_card.dart';
import '../../../card/presentation/mate_cards_controller.dart';
import '../../../profile/presentation/widgets/player_card_view.dart';
import '../../../team/auto_seat.dart';
import '../../../team/data/models/squad.dart';
import '../../../team/data/squad_providers.dart';
import '../../../team/data/squad_repository.dart';
import '../../../team/optimistic_squad.dart';
import '../../../team/seats_from_squad.dart';
import '../../../team/presentation/widgets/squad_board.dart';
import '../widgets/home_video_strip.dart';

/// 홈의 바탕 — **완전한 검정**이다(2026-09-22 사용자 요청: 「홈페이지의 전체
/// 배경 색상 완전 검정으로」).
///
/// 🔴 **옅은 초록을 섞어 두던 것을 되돌렸다.** 2026-09-21 에 빛무리
/// (`AuroraBackground`)를 깔면서 `0xFF07100B` 로 바꿨었는데, 이유는
/// **완전한 검정 위에 빛을 얹으면 글로우 가장자리가 띠로 드러나기**(밴딩)
/// 때문이었다. 🔴 **그 이유가 지금은 없다** — `kAuroraGlow` 가 `false` 라
/// 빛무리가 아무것도 안 그리고 이 색만 칠한다.
///
/// ⚠️ **빛무리를 다시 켜는 날 이 값을 같이 봐야 한다** — 켜는 순간 밴딩이
/// 돌아온다. 그때는 여기에 같은 계열의 아주 옅은 색을 도로 섞는다.
///
/// ⚠️ **판·하단 바를 밝기로 가르던 것은 2026-09-21 에 끝났다** — 이제 둘 다
/// 거의 투명하고 **은빛 테두리**로 갈린다(`SilverEdge`).
///
/// 🔴 **더 이상 검정이 아니다 (2026-09-23 정정).** 위 「완전한 검정」은
/// 2026-09-22 사용자 요청이었는데, 이번에 바탕을 통째로 **밝은 크림 →
/// 살구빛**으로 뒤집었다(`ScreenTint.warm`). 이 값은 [AuroraBackground] 가
/// **하단 바 뒤까지** 칠하는 바탕이라, 여기만 검정으로 두면 화면 아래에
/// **검은 띠**가 남는다 — 그래서 같은 값을 쓴다.
const Color _kHomeBg = ScreenTint.mintBase;

/// 검은 바탕 위의 글자.
const Color _kOnDark = Color(0xFFFFFFFF);

/// 유리 조각 모서리.
const double _kCardRadius = 18;

/// 오른쪽 위 「내 프로필」 단추의 카드 폭. 웹 헤더의 작은 카드(`.ss-pcard-mini`)
/// 자리다 — 글자는 안 읽혀도 초록 카드와 인물로 「내 카드」임을 알아본다.
///
/// 🔴 **두 번에 걸쳐 키웠다**(2026-09-22 사용자 요청) — 48 → 72(1.5배) →
/// **94**(거기서 다시 1.3배). 스쿼드 판 밖 화면 맨 위로 나오면서 **옆에
/// 견줄 것이 없어져** 작아 보였다.
/// 아래 글자도 **같은 배수**로 키운다 — 카드만 키우면 글자가 상대적으로
/// 쪼그라들어 균형이 깨진다.
const double _kProfileCardWidth = 94;

/* ⛔ **`_kSheetCollapsedFactor`(0.5) · `_kCollapsedBoardShrink`(0.82) 를
   지웠다**(2026-09-22). 둘은 「위에서 내려오는 시트」가 **접혔을 때 화면의
   몇 할까지 오는가」를 정하던 값이다. 판이 영상 분석 판 위에 뜬 카드가
   되면서 접힌 높이는 [_kSquadPhotoH] 하나로 정해진다 — 되살리지 말 것. */

/// 판 손잡이 줄의 높이. 판을 끄는 자리라는 표식이다.
const double _kSheetHandleH = 28;

/// 스쿼드 판 · 영상 분석 판의 면 — **거의 투명하다**(2026-09-21).
///
/// 🔴 **면 색을 뺐다**(사용자 요청 「판 자체의 검정 색을 없애면 안 돼?」).
/// 판 둘이 화면의 95%를 덮어서, 면이 조금만 불투명해도 뒤의 빛무리
/// (`AuroraBackground`)가 통째로 가려졌다. 이제 **경계는 은빛 테두리**
/// (`SilverEdge`)가 맡고, 면은 글자가 읽힐 만큼만 깐다.
///
/// 🔴 **흐림(blur)은 안 쓴다.** 판을 유리로 만들면 판 **안에 든 알약**
/// (팀장·팀원·AI)과 겹쳐 「유리 안에 유리」가 되고, 그러면 알약이 **프레임째
/// 사라진다**(`flutter/CLAUDE.md`). 같은 문서가 적어 둔 방법이 「층을 쌓아야
/// 하면 흐림 없이 색만 얹는다」이고, 여기에 테두리를 더한 것이다.
const Color _kSheetColor = Color(0x2E1C1C1E);

/// 🔴 **판을 다 펼쳤을 때의 면 — 흰 서리 유리다**(2026-09-23 사용자 요청:
/// 「스쿼드판 열었을때 기본값을 흰색 블러로」). 접힌 [_kSheetColor] 에서
/// 판이 열리는 만큼 이 값으로 건너간다.
///
/// ⚠️ 70%(`0xB3`) → **30%**(`0x4D`) 로 내렸다(2026-09-23 사용자 요청:
/// 「흰색 30퍼로 줄여봐」). 흐림([_kSheetBlur])은 그대로다.
const Color _kSheetColorOpen = Color(0x4DFFFFFF);

/// 펼친 판의 흐림 세기.
///
/// 🔴 **판이 거의 다 펼쳐진 뒤에만 켠다**([_kSheetBlurFrom]). 접혔을 때
/// 판 안에 있는 **안내 알약이 제 흐림을 갖고 있어서**, 둘이 겹치면
/// 「유리 안에 유리」가 되어 알약이 **프레임째 사라진다**(`flutter/CLAUDE.md`).
/// 안내 알약은 진행도 0.4 에 이미 다 걷히므로 그 뒤에서 켜면 겹치지 않는다.
const double _kSheetBlur = 14;

/// 흐림이 들기 시작하는 판 진행도 — 위 주석의 그 까닭이다.
const double _kSheetBlurFrom = 0.45;

/// 판 아래 모서리. 음악 앱의 앨범 판처럼 아래만 둥글다.
const double _kSheetRadius = 28;

/// 접혔을 때 판 아래 안내(「아래로 내려 내 팀 만들기」) 줄의 높이. 흔들리는
/// 화살표(26, 위아래 -5 ~ +7)가 잘리지 않을 만큼이다.
const double _kSheetHintH = 40;

/// 펼쳤을 때 알약 줄(팀장 · 팀원 · AI)의 높이 — 알약 38 그대로. 「내 프로필」
/// 이 빠진 뒤라 그 단추 높이(92)만큼 비워 둘 까닭이 없다.
const double _kPillsRowH = 38;

/// 판을 다 펼쳤을 때 「영상 분석」이 접혀 드는 납작한 띠의 높이.
const double _kVideoFlatH = 56;

/// 「영상 분석」 판과 위아래 이웃(스쿼드 판 · 하단 바) 사이 틈.
const double _kVideoGap = 12;

/// 「영상 분석」 판이 화면 **양옆 끝에서** 떨어진 거리(2026-09-22 사용자 요청).
const double _kVideoSideInset = 6;

/// 알약이 제 판의 변에서 떨어지는 거리 — 🔴 **스쿼드 판의 안내 알약과
/// 「영상 분석 시작하기」 알약이 나눠 쓴다**(2026-09-22 사용자 요청:
/// 「영상 분석 시작하기 버튼과 같이 판과의 거리 똑같이」).
/// 한쪽만 고치면 둘이 어긋나므로 값은 **여기 하나**다.
const double _kPillInset = 12;

/// 인사말 줄의 글꼴 — 눈누의 **펴진고딕**, 번들한 것은 제일 굵은 Black 뿐이다.
///
/// ⚠️ **굵기를 `w900` 외의 값으로 주지 말 것** — 한 벌만 번들해서, 다른 굵기를
/// 부르면 엔진이 **가짜로 굵게/가늘게** 그려 획이 뭉갠다(YatraOne 에서 겪었다).
const String _kKoFont = 'PyeojinGothic';

/// 인사말이 화면 왼쪽에서 떨어진 거리.
const double _kGreetLeft = 20;

/// 🔴 **인사말 칸이 오른쪽에서 끊기는 자리** (2026-09-24). 「내 프로필」 단추가
/// 거기 서 있어서, 칸을 그 앞에서 끊어야 **긴 닉네임이 카드 위로 올라타지
/// 않는다** — 끊어 두면 넘치는 대신 줄이 바뀐다.
///
/// 단추 폭([_kProfileCardWidth] + 둘레 4×2) + 화면 오른쪽 여백 16 + 틈 8.
const double _kGreetRight = _kProfileCardWidth + 8 + 16 + 8;

/// 「내 프로필」 단추가 차지하는 높이 — 둘레 4 + 카드 + 틈 5 + 글자 18 + 둘레 4.
///
/// 🔴 **카드 비율 4.1:3 은 `player_card_view.dart` 의 `_kBaseH / _kBaseW`
/// 와 같은 값이다** — 거기가 정본이고 여기는 옮겨 적은 것이라, 그쪽이 바뀌면
/// 같이 고친다. 이 값은 다크 판의 **최소 높이**를 정하는 데만 쓴다.
const double _kProfileButtonH = 4 + _kProfileCardWidth * 4.1 / 3 + 5 + 18 + 4;

/// 영상 줄이 다크 판·흰 판과 각각 띄우는 틈.
const double _kVideoStripGap = 10;

/// 워드마크(`SUPERSUB`)가 **화면 맨 위에서** 떨어진 거리.
///
/// 🔴 **스쿼드 판 아랫변에 붙여 두던 것을 뗐다**(2026-09-22 정정, 사용자 요청:
/// 「처음 SUPERSUB 글자를 맨 위에 두고」). 판이 맨 위에 매달린 시트가 아니게
/// 되면서 「판 아래」라는 자리 자체가 없어졌다.
const double _kWordmarkTop = 6;

/// 「영상 분석」 판이 펼쳐져 있을 때의 높이.
///
/// 🔴 **고정값이 됐다**(2026-09-22). 전에는 스쿼드 판의 아랫변에서 거꾸로
/// 재서 「남는 자리의 절반」이었는데, 이제 **스쿼드 판이 이 판을 기준으로**
/// 자리를 잡는다 — 서로를 기준 삼으면 순환이 된다. 둘 중 **아래쪽이 기준**이다.
const double _kVideoOpenH = 190;

/// 접혀 있을 때 스쿼드 판(사진 판)의 높이.
const double _kSquadPhotoH = 180;

/// 스쿼드 판 안에서 손잡이 아래 · 스쿼드 그림 위로 비워 두는 높이
/// (손잡이 + 알약 줄 + 틈).
const double _kBoardTopInset = _kSheetHandleH + 4 + _kPillsRowH + 12;

/// 판 둘과 지름길 알약 줄을 한 덩이로 받치는 **흰 판**(2026-09-23 사용자 요청:
/// 「스쿼드판이랑 영상분석 판 아래에 흰색 판 하나」).
///
/// 🔴 **판 둘 안이 비치지는 않는다.** 판 면([_kSheetColor])은 거의 투명하지만
/// 그 위에 사진(`squad_cover.jpg` · `analysis_cover.jpg`)이 `BoxFit.cover` 로
/// 꽉 차 있어서, 이 흰색은 **판을 두르는 테와 판 사이 틈**으로만 보인다.
///
/// ⚠️ **한 자리만 예외다** — 스쿼드 판을 펼치면 그 사진이 걷히고 스쿼드 그림이
/// 드는데, 그때는 판 면 너머로 이 흰색이 비친다.
const Color _kWhiteSheetColor = Color(0xFFFFFFFF);

/// 흰 판의 모서리.
const double _kWhiteSheetRadius = 28;

/// 흰 판이 **화면 양끝에서** 떨어진 거리 — 0, 즉 끝까지 편다. 판 둘이
/// [_kVideoSideInset] 만큼 안쪽이라 그 차이가 그대로 흰 테가 된다.
const double _kWhiteSheetSideInset = 0;

/// 흰 판이 판 둘 바깥으로 남기는 테의 두께 — 🔴 **판 둘의 옆 여백
/// ([_kVideoSideInset])과 같은 값이다.** 다르면 테가 옆과 아래에서 어긋난다.
const double _kWhiteSheetPad = _kVideoSideInset;

/// 지름길 알약 줄(레슨 · 상점 · 경기장 예약 · 알림)의 높이.
const double _kShortcutRowH = 62;

/// 알약 줄과 스쿼드 판 사이 틈.
const double _kShortcutGap = 12;

/// 알약 줄 위로 흰 판이 더 남기는 자리.
const double _kShortcutTopPad = 14;

/// 알약 셋 사이 틈.
const double _kShortcutSpacing = 10;

/// 지름길 알약의 면 — 🔴 **맨 위 다크 판과 같은 값이다**(2026-09-24).
///
/// ⚠️ **바탕을 따라가던 것을 끊었다.** 2026-09-23 에는 「화면 바탕과 같은
/// 딥그린」이라 [ScreenTint.mintBase] 를 그대로 썼는데, 바탕이 **밝은
/// 회색으로 뒤집히면서** 그 규칙이 알약을 **흰 판 위의 밝은 회색 + 흰 글자**
/// 로 만들어 통째로 사라지게 했다.
///
/// 🔴 **이제 「어두운 면」이 짝이다** — 화면에 어두운 것이 다크 판과 이 알약
/// 둘뿐이라 같은 상수를 쓴다. 알약 색을 갈려면 [_kTopPanelColor] 를 본다.
const Color _kPillFill = _kTopPanelColor;

/// 화면 맨 위 **다크 헤더 판**의 면 (2026-09-24 사용자 요청 + 레퍼런스:
/// 「내 프로필 글자 아래로 … 이 색상으로 판 하나 주자」, 색 견본 `#222021`).
///
/// 🔴 **이 판이 담는 것은 「안녕하세요, (닉네임)」과 「내 프로필」까지다**
/// (사용자 정정: 「그 판은 거기 닉네임과 내 프로필까지만 담아야 해」).
/// 소개 두 줄(「함께 뛸 팀을 만들고,…」)은 **판 밖 아래**에 남는다 —
/// 판을 그 줄까지 내리지 말 것.
///
/// 🔴 **판 위의 글자가 흰색인 근거다.** 바탕이 밝은 회색으로 뒤집혔어도
/// 인사말·「내 프로필」·로고가 흰색으로 남을 수 있는 것은 이 판 덕분이다.
/// 이 판을 걷으면 그 셋의 색도 함께 정해야 한다.
const Color _kTopPanelColor = Color(0xFF222021);

/// 다크 판의 **아래 모서리** — 🔴 흰 판([_kWhiteSheetRadius])과 같은 값이다.
/// 위는 화면 끝에 붙으므로 안 둥글린다. 둘이 화면 위아래에서 짝을 이룬다.
const double _kTopPanelRadius = _kWhiteSheetRadius;

/// 다크 판이 **「내 프로필」 글자 밑으로** 더 남기는 자리.
///
/// ⚠️ **20 → 6** (2026-09-24 사용자 요청: 「그 위에 판을 내 프로필 글자 바로
/// 아래까지 좀 위치 올려」). 그 아래 **영상 줄**이 설 자리를 벌기 위한 것이다 —
/// 판 아랫변이 225.9 → 212 로 올라가 영상 줄이 111 → 125px 을 갖는다.
const double _kTopPanelPadBottom = 6;


/// 알약 안의 글자·아이콘 — 🔴 **순백이다**(같은 요청). 면이 어두워졌으므로
/// 검정에서 뒤집혔다.
///
/// ⚠️ **알약이 흰 판 위에 있다는 것과는 무관하다** — 판이 아니라 **알약 제
/// 면**을 기준으로 정한다. 앞서 판이 희다는 이유로 검정(`#111114`)이었다.
const Color _kOnWhite = Color(0xFFFFFFFF);

/// 알약의 테 — 🔴 **하단 바·영상 분석 판과 같은 값**([SilverEdge.onWhite])
/// 이다. 셋이 같은 흰 판 위에 놓인 조각이라 테가 갈리면 한 화면에 두 굵기·
/// 두 색이 보인다.
const Color _kPillLineOnWhite = SilverEdge.onWhite;

/// 흰 판 위에서 영상 분석 판을 가르는 **가장 얇은 은빛 선**(2026-09-23 사용자
/// 요청: 「제일 얇은 세련된 실버 색상」).
///
/// 🔴 **하단 바와 나눠 쓴다** — 값은 [SilverEdge.onWhite] 한 곳에 있고 왜
/// 그 값인지도 거기 적혀 있다. 여기서 숫자를 다시 쓰면 둘이 갈린다.
const Color _kSilverOnWhite = SilverEdge.onWhite;
const double _kSilverOnWhiteWidth = SilverEdge.onWhiteWidth;

/// 흰 판 맨 위 줄에 서는 지름길 셋(2026-09-23 사용자 요청).
///
/// 🔴 **아직 갈 곳이 없다** — 세 화면은 **웹에만** 있다(`www` 의 `/market` ·
/// `/venues` · 알림함). 이번 회차는 사용자 판단으로 **자리와 모양만** 잡았고,
/// 누르면 「준비 중입니다」다. 화면을 붙이는 날 `onTap` 만 갈면 된다.
const List<({Key key, IconData icon, String label})> _kShortcuts = [
  (
    key: Key('home-shortcut-market'),
    icon: Symbols.storefront,
    label: '레슨 · 상점',
  ),
  (key: Key('home-shortcut-venue'), icon: Symbols.stadium, label: '경기장 예약'),
  (
    key: Key('home-shortcut-alarm'),
    icon: Symbols.notifications,
    label: '알림',
  ),
];

/// 스쿼드 판 자리에 무엇을 세우는가 — 웹의 알약 「팀장」 · 「팀원」.
enum _Role { captain, member }

/// 앱의 첫 화면.
///
/// 🔴 **2026-09-15 에 짜임을 갈았다**(사용자 결정). 전에는 여섯 갈래 카드
/// 격자였다. 지금은 위에서부터:
/// - **위에서 내려오는 판** — 안에 팀장 · 팀원 · AI, 오른쪽 위 「내 프로필」(작은
///   선수 카드), **스쿼드 판**. 카드였던 「용병 매칭」 · 「내 팀」이 웹에서는 이 판
///   하나에 합쳐져 있다(웹 홈 첫 화면과 같은 판단). 접혔다 펼쳐진다(`_squadSheet`)
/// - 「영상 분석」 — 하단 바 바로 위
///
/// 빠진 것: 위쪽 SUPERSUB 로고(하단 바 알약과 겹친다) · 닉네임 · 종목 칩(한
/// 종목으로 좁혔다) · 「내 선수 카드」 · 「내 프로필」 카드(오른쪽 위 단추로) ·
/// 「레슨 · 코치」 카드(하단 바 둘째 아이콘으로). 종목 데이터 층(`sportsProvider`
/// · `currentSportProvider`)은 홈만 안 쓸 뿐 그대로다.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen>
    with TickerProviderStateMixin {
  /// 바 넷째 아이콘에서 열리는 메뉴의 진행도.
  late final AnimationController _menu = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 420),
  );

  /// 테두리를 도는 빛의 위상. 유리 조각 전부가 이 하나를 나눠 쓴다.
  late final AnimationController _sheen = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 7),
  )..repeat();

  bool _menuOpen = false;

  _Role _role = _Role.captain;

  /// 스쿼드 판이 펼쳐진 정도. 0 이면 접혀서(화면 절반까지, 판이 작다) 알약이
  /// 숨고, 1 이면 끝까지 내려와 판이 제 크기다. 🔴 **들어오면 접힌 채다**
  /// (2026-09-15 사용자 요청).
  ///
  /// **스프링으로 움직인다**(2026-09-15 사용자 요청 — 정해진 시간 · 곡선으로 가던
  /// 것이 심심했다). 놓은 손가락의 속도를 이어받아 목표를 살짝 지나쳤다가 제자리에
  /// 앉는다. 지나칠 수 있어야 해서 0~1 로 묶지 않은(unbounded) 컨트롤러다 — 값이
  /// 1 을 조금 넘으면 판이 그만큼 더 늘었다가 돌아온다.
  late final AnimationController _sheet = AnimationController.unbounded(
    vsync: this,
  )..addListener(_syncPills);

  /// 알약 셋(팀장 · 팀원 · AI)이 차례로 떠오르는 진행도. 🔴 **판이 다 펼쳐진
  /// 뒤에** 시작한다(사용자 요청) — 판과 같이 자라면 판이 커지는 동안 위가
  /// 어수선하다. 접기 시작하면 곧바로 빠르게 걷힌다.
  late final AnimationController _pills = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 560),
    reverseDuration: const Duration(milliseconds: 160),
  );

  /// 조금 통통 튀는 스프링 — 감쇠비 0.74 면 한 번 살짝 넘쳤다 앉는다. 더 낮추면
  /// 출렁이고, 1 이면 넘치지 않아 다시 심심해진다.
  static final SpringDescription _spring = SpringDescription.withDampingRatio(
    mass: 1,
    stiffness: 320,
    ratio: 0.74,
  );

  @override
  void dispose() {
    _menu.dispose();
    _sheen.dispose();
    _sheet.dispose();
    _pills.dispose();
    super.dispose();
  }

  /// 판이 거의 다 나오면 알약을 띄우고, 접히기 시작하면 걷는다.
  void _syncPills() {
    final v = _sheet.value;
    if (v >= 0.98) {
      if (_pills.status != AnimationStatus.forward &&
          _pills.status != AnimationStatus.completed) {
        _pills.forward();
      }
    } else if (v < 0.95) {
      if (_pills.status != AnimationStatus.reverse &&
          _pills.status != AnimationStatus.dismissed) {
        _pills.reverse();
      }
    }
  }

  // --- 손끝 진동(햅틱) ------------------------------------------------------
  //
  // 판을 끌 때 손에 걸리는 느낌을 준다(2026-09-15 사용자 요청). 🔴 **세 순간에만**
  // 준다 — 끄는 내내 떨리면 거슬리고 배터리만 먹는다.
  // - 절반을 넘는 순간 — 딸깍(`selectionClick`). 여기서 놓으면 반대쪽으로 붙는다
  // - 끝에 닿아 고무줄이 걸리는 순간 — 딸깍
  // - 놓아서(또는 손잡이를 눌러) 붙으러 갈 때 — 톡(`lightImpact`)
  // 기기 설정에서 터치 진동을 껐으면 운영체제가 알아서 삼킨다.

  /// 지금 판이 절반보다 펼쳐진 쪽인가 — 넘나드는 순간을 잡으려고 기억한다.
  bool _pastHalf = false;

  /// 지금 끝(0 또는 1) 너머에 걸려 있는가.
  bool _atEdge = false;

  /// 손가락을 따라 판이 자라고 줄어든다. [travel] 은 접힘 ↔ 펼침 사이 거리.
  /// 끝을 넘어 더 끌면 **고무줄처럼 뻑뻑해진다**(끄는 만큼의 3할만 따라온다).
  ///
  /// 🔴 **부호가 뒤집혔다**(2026-09-22, 판이 **위로** 자라게 바뀌면서).
  /// 화면 좌표는 아래가 `+` 인데 이제 **위로 끄는 것이 펼치는 것**이라,
  /// `primaryDelta` 에 `-` 를 붙여야 손가락과 판이 같이 간다.
  /// ⚠️ 여기만 뒤집으면 안 된다 — [_releaseSheet] 의 **속도 부호**도 같이
  /// 뒤집어야 튕겼을 때 엉뚱한 쪽으로 붙지 않는다.
  void _dragSheet(DragUpdateDetails d, double travel) {
    if (travel <= 0) return;
    _sheet.stop();
    var delta = -d.primaryDelta! / travel;
    final v = _sheet.value;
    final beyond = (v >= 1 && delta > 0) || (v <= 0 && delta < 0);
    if (beyond) delta *= 0.3;
    _sheet.value = (v + delta).clamp(-0.12, 1.12);

    final pastHalf = _sheet.value > 0.5;
    if (pastHalf != _pastHalf) {
      _pastHalf = pastHalf;
      HapticFeedback.selectionClick();
    }
    if (beyond != _atEdge) {
      _atEdge = beyond;
      if (beyond) HapticFeedback.selectionClick();
    }
  }

  /// 놓으면 가까운 쪽으로 스프링을 탄다. 빠르게 튕겼으면 튕긴 쪽으로, 그 속도로.
  ///
  /// 🔴 **부호가 뒤집혔다** — [_dragSheet] 와 같은 이유다. **위로**(음수)
  /// 튕기면 펼치는 쪽이다.
  void _releaseSheet(DragEndDetails d, double travel) {
    final pxPerSec = -(d.primaryVelocity ?? 0);
    final open = pxPerSec > 300
        ? true
        : (pxPerSec < -300 ? false : _sheet.value > 0.5);
    _settleSheet(open ? 1 : 0, travel <= 0 ? 0 : pxPerSec / travel);
  }

  void _settleSheet(double target, [double velocity = 0]) {
    HapticFeedback.lightImpact();
    _pastHalf = target > 0.5;
    _atEdge = false;
    _sheet.animateWith(
      SpringSimulation(_spring, _sheet.value, target, velocity),
    );
  }

  void _toggleSheet() => _settleSheet(_sheet.value > 0.5 ? 0 : 1);

  void _openProfile() {
    _closeMenu();
    context.push('/profile');
  }

  void _toggleMenu() {
    setState(() => _menuOpen = !_menuOpen);
    _menuOpen ? _menu.forward() : _menu.reverse();
  }

  void _closeMenu() {
    if (!_menuOpen) return;
    setState(() => _menuOpen = false);
    _menu.reverse();
  }

  void _onNavTap(int index) {
    if (index == FloatingNavBar.menuIndex) {
      _toggleMenu();
      return;
    }
    _closeMenu();
    switch (index) {
      case 0:
        return; // 이미 홈이다.
      /* 🔴 **3번은 내 프로필이다**(2026-09-22, 사용자 지적: 「아래 3번째꺼
         아이콘 누르면 똑같이 내 프로필 화면 나와야 하는거 아님?」).
         아이콘(신분증)은 처음부터 프로필이었는데 **누르면 「준비 중입니다」**
         가 떴다 — 아래 `default` 로 떨어지고 있었다. */
      case 3:
        context.go('/profile');
      // 🔴 1번은 영상이다 — 3번과 **같은 종류의 누락**이었다(2026-09-22).
      case 1:
        context.go('/videos');
      case 2:
        _notReady('레슨 · 코치');
      default:
        _notReady();
    }
  }

  void _onMenuPick(BarMenuItem item) {
    _closeMenu();
    switch (item) {
      case BarMenuItem.logout:
        ref.read(sessionControllerProvider.notifier).logout();
      case BarMenuItem.login:
        // 홈은 로그인한 뒤에만 보이는 화면이라 여기 설 일이 없다.
        break;
      case BarMenuItem.credits:
      case BarMenuItem.coach:
      case BarMenuItem.settings:
        _notReady(item.label);
    }
  }

  /* 🔴 **세션 안 한 번만.** 판이 비는 다른 길(크기 바꾸기 · 늦게 온 응답)에서
     이 효과가 다시 돌면 **같은 등재가 서버로 두 번** 나간다(웹과 같은 장치). */
  bool _autoSeated = false;

  /// 카드를 만든 사람을 **판에 먼저 앉힌다**(`flutter/lib/features/team/auto_seat.dart`).
  ///
  /// 🔴 **주장만** 한다 — 등재는 주장 전용이라 팀원이 부르면 403 이고, 판에만
  /// 섰다가 새로고침에 사라진다. 팀원의 카드는 팀장이 등재해 주었을 때 선다.
  void _autoSeatOnce(
    Squad? squad,
    String? myCardId,
    String? myCardSlug,
    String? ownedTeamId,
  ) {
    if (_autoSeated) return;
    if (squad == null || myCardId == null || ownedTeamId == null) return;
    if (squad.teamId != ownedTeamId) return;

    final choice = pickAutoSeat(
      squad: squad,
      myCardSlug: myCardSlug,
      size: squadSizeOf(squad.formation),
    );
    if (choice == null) return;

    _autoSeated = true;
    // 🔴 빌드 중에 서버를 부르지 않는다 — provider 상태를 건드려 Riverpod 이
    //    던진다. 프레임이 끝난 뒤로 미룬다(`_wantMateCards` 와 같은 이유).
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      try {
        await ref
            .read(squadRepositoryProvider)
            .enlist(
              ownedTeamId,
              playerCardId: myCardId,
              positionCode: choice.positionCode,
              gridCol: choice.col,
              gridRow: choice.row,
            );
        // 판을 다시 읽어 방금 생긴 등재를 그린다.
        ref.invalidate(squadProvider(ownedTeamId));
      } catch (_) {
        /* 🔴 **조용히 넘어간다.** 자동 착석은 사람이 시킨 일이 아니라 판을
           처음 여는 사람을 위한 편의다 — 실패했다고 오류 창을 띄우면 무엇
           때문인지 모르는 알림이 뜬다. 다음에 켤 때 다시 시도한다. */
      }
    });
  }

  /* 🔴 **화면이 먼저 보여 주는 판.** `null` 이면 서버 값을 그대로 쓴다.
     쓰기가 끝나면 서버가 준 **바뀐 스쿼드 전체**로 덮고, 실패하면 `null` 로
     되돌려 서버 값으로 복귀한다. */
  Squad? _shownSquad;

  /// 쓰기 하나를 **화면 먼저** 반영하고 서버에 보낸다.
  ///
  /// 🔴 `invalidate` 로 다시 읽지 않는다 — 다시 읽는 동안 값이 비면 판이
  /// 통째로 깜빡인다. 계약이 **바뀐 스쿼드 전체**를 주므로 그것으로 덮는다.
  Future<void> _write(
    Squad shown,
    Future<Squad> Function(SquadRepository repo) call,
  ) async {
    setState(() => _shownSquad = shown);
    try {
      final next = await call(ref.read(squadRepositoryProvider));
      if (!mounted) return;
      setState(() => _shownSquad = next);
      /* 🔴 **provider 도 새로 읽게 둔다.** 화면은 `_shownSquad` 로 이미
         맞지만, provider 는 한 번 읽은 값을 들고 있어서 **홈을 떠났다
         돌아오면 옛 자리**가 보인다. 깜빡임은 없다 — 보여 주는 것은
         `_shownSquad` 이고 이것은 그대로 남는다. */
      final teamId = next.teamId;
      ref.invalidate(squadProvider(teamId));
    } on ApiException catch (e) {
      /* 🔴 **되돌리고 알린다.** 사람이 시킨 일이라 조용히 넘어가면 「옮겼는데
         안 옮겨졌다」가 된다. 화면만 옮겨 두면 새로고침에 사라져 더 나쁘다. */
      if (!mounted) return;
      setState(() => _shownSquad = null);
      _notReady(e.message);
    }
  }

  /// 카드를 다른 칸으로 옮긴다 — 서버에 남겨야 새로고침해도 그 자리다.
  Future<void> _moveSeat(
    String teamId,
    Squad squad,
    String memberId,
    String positionCode,
    int col,
    int row,
  ) => _write(
    squadWithSeatMoved(
      squad,
      memberId: memberId,
      positionCode: positionCode,
      gridCol: col,
      gridRow: row,
    ),
    (repo) => repo.moveSeat(
      teamId,
      memberId: memberId,
      positionCode: positionCode,
      gridCol: col,
      gridRow: row,
    ),
  );

  /// 그 사람을 판에서 빼고 **팀에서도 내보낸다**.
  ///
  /// 🔴 **둘 다 해야 한다**(웹, 2026-09-18 사용자 결정: 「x 가 팀에서도
  /// 빠지는 것」). 판에서 내리는 것만으로는 그 사람이 여전히 팀원이라
  /// **AI 추천 후보에서 계속 빠진다**(추천은 그 팀 소속을 뺀다) — 웹 운영에서
  /// 그렇게 12명이 쌓여 추천 목록이 말랐다.
  Future<void> _removeSeat(
    String teamId,
    Squad squad,
    String memberId,
    String? cardSlug,
    String? mySlug,
  ) async {
    final repo = ref.read(squadRepositoryProvider);
    await _write(
      squadWithSeatRemoved(squad, memberId: memberId),
      (r) => r.removeSeat(teamId, memberId: memberId),
    );

    // 여기서부터는 **덤**이다 — 판에서는 이미 빠졌으므로 실패해도 안 알린다.
    if (cardSlug == null || cardSlug == mySlug) return;
    try {
      /* 🔴 **카드를 한 번 읽어 주인을 알아낸다.** 판이 들고 있는 것은 카드
         슬러그뿐인데, 팀에서 내보내는 경로는 **사용자 id** 를 받는다. */
      final owner = await ref.read(cardRepositoryProvider).cardBySlug(cardSlug);
      final userId = owner?.userId;
      // 🔴 나는 안 내보낸다 — 주장이 스스로 나가면 팀이 주인을 잃는다.
      if (userId == null) return;
      await repo.removeTeamMember(teamId, userId: userId);
    } catch (_) {
      // 못 내보내도 판에서는 이미 빠졌다 — 화면을 멈추지 않는다.
    }
  }

  /// 판에 앉은 팀원들의 카드를 **보이는 것만** 받아 둔다.
  ///
  /// 🔴 **빌드 중에 상태를 바꾸지 않는다** — `want()` 가 provider 상태를 건드려
  /// 빌드 도중에 부르면 Riverpod 이 던진다. 프레임이 끝난 뒤로 미룬다.
  void _wantMateCards(Squad? squad, String? mySlug) {
    if (squad == null) return;
    final slugs = <String>[];
    for (final m in squad.members) {
      final slug = m.cardPublicSlug;
      // 내 카드는 내가 이미 들고 있다 — 다시 받지 않는다.
      if (slug == null || slug == mySlug) continue;
      slugs.add(slug);
    }
    if (slugs.isEmpty) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(mateCardsProvider.notifier).want(slugs);
    });
  }

  /// 그 슬러그의 카드가 **이미 와 있으면** 그린다. 아직이면 `null` —
  /// 판이 이름표로 물러난다.
  Widget? _mateCard(String slug, double width) {
    final card = ref.watch(mateCardsProvider)[slug];
    if (card == null) return null;
    // 🔴 팀원 카드도 꾸민 대로 그린다 — 웹에서 꾸민 카드가 앱에서 기본
    //    모습으로 나오면 같은 카드로 안 보인다.
    return PlayerCardView(
      width: width,
      seed: card.publicSlug,
      alias: aliasOf(card),
      style: card.style,
      photoUrl: card.photoUrl,
    );
  }

  void _notReady([String? what]) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('${what ?? '이 기능'} — 준비 중입니다')));
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider);
    final user = session is SessionLoggedIn ? session.user : null;
    // 🔴 붓자국 씨앗은 **카드의 공개 슬러그**다 — 이래야 웹과 같은 무늬가
    //    나온다. 카드가 아직 없으면 `null` 이고 판은 빈 자리만 그린다.
    /* ⚠️ **여기는 `.value` 로 둔다 — 조사하고 내린 결론이다**(2026-09-23).
       프로필은 같은 `.value` 때문에 「못 읽음」에 「카드 만들기」를 내밀어
       고쳤는데(`profile_screen.dart` 의 `_cardAction`), **홈은 그 자리에
       누를 것이 없다.** 실패하면 일어나는 일 셋을 전부 짚어 봤다:

       | 쓰는 자리 | `null` 일 때 | 위험 |
       |---|---|---|
       | `ScreenTint`(587·992) | 사선 색을 안 칠한다 | 없음 — 보기만 밋밋 |
       | `_ProfileButton`(1962) | 빈 카드를 그린다 | 없음 — **단추는 프로필로 갈 뿐** 만들지 않는다 |
       | `_autoSeatOnce`(554) | `myCardId == null` 이라 **그냥 빠져나간다**(366) | 없음 — 서버를 안 부른다 |

       🔴 **다시 조사하지 말 것.** 여기를 `AsyncValue` 로 바꾸면 홈 전체가
       로딩·오류 두 그림을 더 갖게 되는데, 그 값을 치를 이유가 위 표에 없다. */
    final card = ref.watch(myCardProvider).value;
    final cardSeed = card?.publicSlug;
    // 주장인 팀이 우선, 없으면 속한 첫 팀. 팀이 없으면 판을 안 부른다.
    final teamId = user?.primaryTeamId;
    /* 🔴 **낙관적 판이 서버 값을 이긴다** (2026-09-21, 사용자가 실기기에서
       잡은 것). 옮긴 뒤 서버 왕복 300ms 동안 옛 자리로 되돌아가 **「제자리로
       갔다가 옮겨진다」**가 됐고, 다시 읽는 사이 값이 비면 **카드가 사라져**
       보였다. 이제 화면이 그 자리에서 바뀌고, 서버 응답이 오면 덮는다. */
    final serverSquad = teamId == null
        ? null
        : ref.watch(squadProvider(teamId)).value;
    final squad = _shownSquad ?? serverSquad;
    _wantMateCards(squad, cardSeed);
    _autoSeatOnce(squad, card?.id, cardSeed, user?.ownedTeamId);

    // 🔴 **Scaffold 를 감싼다** — 하단 바·메뉴 뒤까지 같은 빛이 이어져야 한다.
    return AuroraBackground(
      base: _kHomeBg,
      child: Scaffold(
        /* 🔴 **바탕은 투명으로 두고 빛무리가 칠한다**(`AuroraBackground`).
         Scaffold 가 색을 칠하면 그 위에 빛무리를 깔아도 **판·바 뒤로는 안
         비친다** — 층을 하나로 만들어야 화면 전체가 같은 빛을 받는다. */
        backgroundColor: Colors.transparent,
        // 바는 SafeArea 밖에 떠 있다 — 안에 넣으면 홈 인디케이터 위에서 잘린다.
        // 메뉴는 바 바로 위에 선다. 닫혀 있어도 자리를 잡아 두어 열릴 때
        // 바가 밀리지 않는다.
        bottomNavigationBar: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            BarMenu(
              open: _menu,
              loggedIn: session is SessionLoggedIn,
              step: FloatingNavBar.iconStep(context),
              onPick: _onMenuPick,
            ),
            FloatingNavBar(currentIndex: 0, onTap: _onNavTap),
          ],
        ),
        extendBody: true,
        body: Stack(
          fit: StackFit.expand,
          children: [
            /* 🔴 **카드의 두 색을 안 쓴다**(2026-09-23 정정, 사용자 요청:
               「그냥 홈페이지는 카드에서 뽑아낸 2가지 색상 말고 저
               레퍼런스처럼」). 2026-09-22 에는 `card.style` 의 바탕색·자국색을
               넘겼는데, 이제 **고정된 크림→살구빛 한 벌**이다.

               🔴 **`if (card?.style != null)` 도 같이 걷혔다** — 카드가 없거나
               아직 안 온 사람에게 **바탕이 통째로 검정으로 보이던** 자리다.
               이제 누구에게나 같은 바탕이 깔린다. */
            /* 🔴 **상태 바 아이콘은 바탕이 아니라 다크 판이 정한다**
               (2026-09-24). [ScreenTint] 는 `base` 의 광도로 아이콘 밝기를
               스스로 고르는데, 바탕이 밝은 회색이 되면서 **어두운 아이콘**을
               골랐다 — 그런데 상태 바가 실제로 얹히는 것은 그 바탕이 아니라
               **맨 위의 다크 판**이라 시계·배터리가 안 보였다. */
            const Positioned.fill(
              child: IgnorePointer(
                child: ScreenTint.mint(topColor: _kTopPanelColor),
              ),
            ),
            // 판을 펼칠수록 뒤가 조금 눌린다 — 시선이 판으로 모인다.
            Positioned.fill(
              child: IgnorePointer(
                child: AnimatedBuilder(
                  animation: _sheet,
                  builder: (context, _) => ColoredBox(
                    color: Colors.black.withValues(alpha: 0.18 * _sheetT),
                  ),
                ),
              ),
            ),
            /* 🔴 **판 둘보다 뒤다.** 받치는 것이지 덮는 것이 아니라서,
               이 자리(영상 분석 판 **앞**)를 지켜야 한다. */
            _whiteSheet(context),
            _videoPanel(context),
            _shortcutPills(context),
            /* 🔴 **로고·「내 프로필」보다 뒤, 스쿼드 판보다 앞이다.** 뒤라서
               그 셋이 판 위에 얹히고, 앞이라서 판을 펼치면 **인사말과 똑같이
               덮인다** — 따로 걷는 연출을 안 만들어도 되는 자리다. */
            _topPanel(context, user?.nickname),
            // 로고는 화면 맨 위 가운데 — 판을 펼치면 그 판이 덮는다.
            _brandMark(context),
            _videoStrip(context),
            _squadSheet(context, card, squad, user?.ownedTeamId),
            // 「내 프로필」 — 화면 맨 위 오른쪽. 판보다 **뒤에 두지 않는다**.
            _profileButton(context, card),
          ],
        ),
      ),
    );
  }

  /// 위에서 내려오는 스쿼드 판(2026-09-15 사용자 요청 — 음악 앱의 앨범 판처럼).
  ///
  /// - **접힘(0)**: 스쿼드 판이 **작게** 줄어 「내 프로필」 윗변 높이까지 올라가고,
  ///   판 면은 그 아래 손잡이까지만 온다(화면 절반쯤). 팀장 · 팀원 · AI 는 숨는다.
  ///   「내 프로필」만 늘 보인다.
  /// - **펼침(1)**: 영상 분석 바로 위까지 내려오고 판이 제 크기가 되며 알약이
  ///   나타난다. 둘 사이는 손가락을 따라 이어진다.
  ///
  /// 판을 **줄이는 방법**: 제 크기로 짠 판을 위 가운데 기준으로 통째로 축소한다
  /// (`Transform.scale`). 카드를 다시 배치하는 게 아니라 같은 그림이 작아지므로,
  /// 끌어내리는 동안 자리가 튀지 않고 자연스럽게 커진다.
  ///
  /// 🔴 판 면은 **유리가 아니다**(흐림 · 굴절 없이 어두운 면만). 안에 유리 알약
  /// (팀장 · 팀원 · AI)이 들어가서, 판까지 유리면 「유리 안에 유리」가 되어 알약이
  /// 프레임째 사라진다(flutter/CLAUDE.md).
  /// 판 진행도를 0~1 로 묶은 값 — 스프링이 넘친 만큼까지 따라가면 이상한 것들
  /// (어두운 막 · 영상 분석 흐림 · 모서리)에 쓴다.
  double get _sheetT => _sheet.value.clamp(0.0, 1.0);

  /// 「영상 분석」 판이 화면 **아래 끝에서** 떨어진 거리 — 하단 바 바로 위.
  double _videoBottomInset(BuildContext context) =>
      FloatingNavBar.heightOf(context) + 8;

  /// 판 둘과 지름길 알약 줄을 받치는 **흰 판**(2026-09-23 사용자 요청).
  ///
  /// 🔴 **[IgnorePointer] 다.** 판 둘보다 뒤에 있어도 겹치는 넓이가 커서,
  /// 손짓을 받으면 판 가장자리와 알약이 여기서 먹힌다.
  Widget _whiteSheet(BuildContext context) {
    final geo = _sheetGeometry(context);
    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        /* 🔴 **묶은 값으로 잰다.** 스프링이 넘친 값을 그대로 쓰면 흰 판
           윗변이 화면 위로 튀어 나갔다 돌아온다 — 판 둘과 달리 이쪽은
           그 출렁임이 **테 두께의 흔들림**으로 보여서 지저분하다. */
        final top =
            geo.whiteTopCollapsed +
            (geo.whiteTopExpanded - geo.whiteTopCollapsed) * _sheetT;
        return Positioned(
          top: top,
          left: _kWhiteSheetSideInset,
          right: _kWhiteSheetSideInset,
          height: (geo.whiteBottom - top).clamp(0.0, double.infinity),
          child: const IgnorePointer(
            key: Key('home-white-sheet'),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: _kWhiteSheetColor,
                borderRadius: BorderRadius.all(
                  Radius.circular(_kWhiteSheetRadius),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  /// 흰 판 맨 위의 지름길 알약 셋 — 가로로 나란히.
  ///
  /// 🔴 **「내 프로필」과 같은 방식으로 걷힌다**(앞 4할 안에). 스쿼드 판이
  /// 위로 자라면서 이 줄 자리를 통째로 덮기 때문이다. 같은 식을 쓰므로
  /// 한쪽만 고치면 둘이 어긋난다.
  Widget _shortcutPills(BuildContext context) {
    final geo = _sheetGeometry(context);
    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        final tc = _sheetT;
        return Positioned(
          top: geo.shortcutTop,
          left: _kVideoSideInset + _kWhiteSheetPad,
          right: _kVideoSideInset + _kWhiteSheetPad,
          height: _kShortcutRowH,
          /* 나가기 시작하면 더 안 눌린다 — 화면 밖으로 미끄러지는 단추를
             누를 수 있으면 손가락이 판을 끌다 엉뚱한 곳으로 간다. */
          child: IgnorePointer(
            ignoring: tc > 0.02,
            child: Row(
              children: [
                for (final (i, s) in _kShortcuts.indexed) ...[
                  if (i > 0) const SizedBox(width: _kShortcutSpacing),
                  Expanded(
                    /* 🔴 **제자리에서 걷힌다**(2026-09-23 정정, 사용자:
                       「오른쪽으로 나가지 말고 그냥 제자리에서 … 사라지는 게
                       스쿼드판 올라갈 때 다 보이니까 눈아프다」).
                       ⛔ **옆으로 미는 것을 되살리지 말 것** — 판이 올라오는
                       내내 알약이 화면을 가로질러서 시선이 그쪽으로 끌린다. */
                    child: Opacity(
                      opacity: 1 - _shortcutExit(tc, i),
                      child: _ShortcutPill(
                        key: s.key,
                        icon: s.icon,
                        label: s.label,
                        onTap: () => _notReady(s.label),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  /// 알약 [i](왼쪽부터 0)가 **걷힌 정도** 0~1. 1 이면 안 보인다.
  ///
  /// 🔴 **오른쪽 것부터 걷힌다**(2026-09-23 사용자 요청: 「오른쪽 꺼부터
  /// 차례대로」). 그래서 시작 시각을 오른쪽일수록 이르게 준다.
  ///
  /// 🔴 **판이 올라오기 전에 다 걷힌다** — 구간을 앞쪽 절반 안에 몰아넣었다.
  /// 늦게까지 남으면 올라오는 판과 겹쳐 보여 지저분하다.
  ///
  /// 🔴 **돌아오는 순서를 따로 두지 않는다.** 이 값이 판 진행도 하나의
  /// **함수**라, 판을 접으면 시간이 되감기면서 **저절로 왼쪽(레슨 · 상점)
  /// 부터** 돌아온다 — 사용자가 요청한 그 순서다. 🔴 나가는 길과 들어오는
  /// 길을 나누면 손가락을 도중에 되돌렸을 때 알약이 제자리로 안 돌아온다
  /// (워드마크가 같은 이유로 한 함수다).
  ///
  /// ⚠️ **걷어 내지(`Opacity`) 않는다** — 옆으로 나가면서 흐려지기까지 하면
  /// 화면 밖에 닿기 전에 사라져 **나가는 것이 안 보인다.**
  static double _shortcutExit(double tc, int i) {
    /// 한 알약이 걷히는 데 쓰는 구간, 그리고 이웃과의 시차.
    const span = 0.30;
    const step = 0.10;
    final start = (_kShortcuts.length - 1 - i) * step;
    final p = ((tc - start) / span).clamp(0.0, 1.0);
    /* 🔴 [Curves.easeInCubic] 에서 갈았다 — 그쪽은 **미는 데** 맞는 곡선이라
       (처음엔 느리고 끝에 빠르다) 걷는 데 쓰면 마지막에 툭 사라진다. */
    return Curves.easeInOut.transform(p);
  }

  /// 「내 프로필」 — **화면 맨 위 오른쪽**(2026-09-22 사용자 요청).
  ///
  /// 🔴 **스쿼드 판 밖으로 나왔다.** 판이 사진 얼굴을 갖게 되면서 카드가
  /// 사진 위에서 부딪혔다 — 「내 프로필」 글자가 판 밖으로 삐져나가고 사진 속
  /// 선수와 겹쳤다. 워드마크와 **같은 줄**에 선다(워드마크는 가운데, 이건
  /// 오른쪽 끝이라 안 부딪힌다).
  ///
  /// 🔴 **판을 펼치면 오른쪽으로 빠져나간다** — 그 자리를 판 맨 위의 `AI`
  /// 알약이 쓴다. 옛 동작 그대로다.
  Widget _profileButton(BuildContext context, PlayerCard? card) {
    final geo = _sheetGeometry(context);
    const profileW = _kProfileCardWidth + 8;
    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        final fadeOut = (1 - _sheetT / 0.4).clamp(0.0, 1.0);
        return Positioned(
          top: geo.rowTop,
          right: 16,
          child: IgnorePointer(
            ignoring: fadeOut < 0.5,
            child: Opacity(
              opacity: fadeOut,
              child: Transform.translate(
                offset: Offset((profileW + 24) * (1 - fadeOut), 0),
                child: _ProfileButton(card: card, onTap: _openProfile),
              ),
            ),
          ),
        );
      },
    );
  }

  /// 화면 맨 위 가운데의 `SUPERSUB` — 🔴 **아무 단추도 아니다.**
  ///
  /// 🔴 **하단 바에 있던 그 로고를 여기로 옮겼다 (2026-09-23 사용자 요청:
  /// 「supersub 의 로고는 그냥 화면 위쪽 가운데에 그냥 두고, 그거는 아무런
  /// 버튼이 아니게」).** 그래서 **로그인에서 날아오는 로고가 여기 착지한다**
  /// (`brandHero`) — 글꼴·색이 비행 글자와 같아서 착지가 안 튄다.
  ///
  /// ⛔ **되살리지 말 것 — 여기 있던 순백 `SUPER`/`SUB` 두 쪽.** YatraOne 로
  /// 쓴 다른 워드마크였고, 판을 펼치면 양옆 화면 밖으로 갈라져 나갔다
  /// (`_WordmarkHalf`). 사용자가 **그 글자는 없애고** 하단 바의 로고를
  /// 올리라고 정했다 — 같은 화면에 `SUPERSUB` 가 둘이던 것이 정리된 것이다.
  /// 2026-09-23 이전 커밋에서 꺼낸다.
  ///
  /// 🔴 **나가는 연출이 없어도 된다** — 판을 펼치면 스쿼드 판이 이 글자를
  /// **덮는다**([Stack] 에서 판이 뒤에 온다). 갈라져 나가던 것은 그 시절
  /// 판이 위에서 내려오는 시트라 덮지 못해서 필요했던 것이다.
  Widget _brandMark(BuildContext context) {
    final geo = _sheetGeometry(context);
    final size = MediaQuery.sizeOf(context);
    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        /* 🔴 **묶은 값으로 잰다.** 넘친 값으로 재면 글자가 화면 밖에서 한 번
           더 튀는데, 안 보이는 곳에서 나는 일이라 계산만 버린다. */
        final exit = Curves.easeInCubic.transform(_sheetT);
        return Positioned(
          left: 0,
          right: 0,
          top: geo.rowTop + _kWordmarkTop,
          child: IgnorePointer(
            child: Center(
              /* 🔴 **화면 위 바깥으로 나간다**(2026-09-23 사용자 요청).
                 판을 펼치면 스쿼드 판이 이 자리를 덮지만, 덮이는 것과
                 **나가는 것은 다르게 보인다** — 사용자가 나가는 쪽을 골랐다.

                 🔴 **넉넉히 민다.** 글자 높이를 재서 「딱 맞게」 밀면 기기마다
                 글꼴 렌더링이 달라 한 획이 남는다(워드마크에서 겪었다).
                 [Stack] 이 화면 밖을 잘라 내므로 넉넉한 쪽이 안전하다. */
              child: Transform.translate(
                offset: Offset(0, -size.height * 0.25 * exit),
                /* 🔴 **키로 찾는다** — 글자로 찾으면 판 위의 선수 카드마다
                   박힌 `SUPERSUB` 워터마크까지 걸린다(시험이 7개를 찾았다). */
                child: const KeyedSubtree(
                  key: Key('home-brand'),
                  child: _BrandFade(),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  /// 화면 맨 위의 **다크 헤더 판**과 그 안의 인사말 (2026-09-24 사용자 요청 +
  /// 레퍼런스: 「내 프로필 글자 아래로 … 이 색상으로 판 하나 주자」).
  ///
  /// 🔴 **판이 인사말을 「담는다」 — 나란히 두지 않는다.** 판 높이를 따로
  /// 계산해서 맞추는 방법도 있었지만, **닉네임이 길어 줄이 하나 더 늘면**
  /// 그 계산이 조용히 어긋나 글자가 판 밖으로 비어져 나온다. 자식으로 넣으면
  /// 판이 **글자를 잰 만큼** 커지므로 그런 경우가 아예 없다.
  ///
  /// 🔴 **담는 것은 인사말과 「내 프로필」까지다** (사용자 정정: 「그 판은
  /// 거기 닉네임과 내 프로필까지만 담아야 해」). 소개 두 줄은 판 **밖 아래**다
  /// — 아랫변을 그 줄까지 내리지 말 것.
  ///
  /// 🔴 **로고·「내 프로필」은 이 판의 자식이 아니다.** [Stack] 에서 이 판
  /// **뒤에** 그려져 판 위에 얹힐 뿐이다. 둘 다 `rowTop` 에서 시작해 판 안에
  /// 들어오는데, 인사말이 없는 사람(로그인 전)에게도 그 둘은 덮여야 하므로
  /// 판에 **최소 높이**를 준다.
  ///
  /// 🔴 **닉네임이 아직 없으면 줄을 안 세운다.** 세션이 오기 전에 「안녕하세요,
  /// 님」처럼 이름만 빠진 줄이 한 번 떴다 바뀌면 그것이 더 눈에 띈다.
  Widget _topPanel(BuildContext context, String? nickname) {
    final geo = _sheetGeometry(context);
    final hasName = nickname != null && nickname.isNotEmpty;
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: IgnorePointer(
        child: ConstrainedBox(
          // 인사말이 없어도 로고와 「내 프로필」은 덮는다.
          /* 🔴 **「내 프로필」 바로 아래에서 끊는다** — 소개 두 줄은 판 밖이다
             (2026-09-24 사용자 확정: 「그 판을 함께 내 프로필 아래쪽으로 해줘.
             함께 뛸 팀을 만들고 여기까지 하지 말고」).

             🔴 **아랫변을 정하는 것은 인사말이 아니라 「내 프로필」 카드다**
             (94폭 → 128 높이). 인사말을 줄여도 판이 안 줄어드는 이유이고,
             판을 낮추려면 [_kProfileCardWidth] 를 봐야 한다.

             ⚠️ **같은 날 「흰 판 바로 위까지 늘렸다」가 되돌아왔다.** 그때는
             판이 소개 두 줄을 침범하는 줄 알았는데, **시험 화면에 상태 바
             자리가 없어서** 나온 착시였다 — 실기기(411×891, 상태 바 33)에서
             재면 판 아랫변 220.5, 소개 두 줄 윗변 238.9 로 **18px 남는다.**
             🔴 그래서 시험도 상태 바 자리를 넣고 잰다(`_kDeviceTopInset`). */
          constraints: BoxConstraints(
            minHeight: geo.rowTop + _kProfileButtonH + _kTopPanelPadBottom,
          ),
          child: DecoratedBox(
            key: const Key('home-top-panel'),
            decoration: const BoxDecoration(
              color: _kTopPanelColor,
              // 위는 화면 끝에 붙으므로 안 둥글린다.
              borderRadius: BorderRadius.vertical(
                bottom: Radius.circular(_kTopPanelRadius),
              ),
            ),
            child: Padding(
              padding: EdgeInsets.only(
                // 로고 줄 아래 — 인사말이 앉던 그 자리 그대로다.
                top: geo.rowTop + _kWordmarkTop + kBrandHomeSize + 18,
                left: _kGreetLeft,
                right: _kGreetRight,
                bottom: _kTopPanelPadBottom,
              ),
              child: SizedBox(
                width: double.infinity,
                child: hasName
                    ? KeyedSubtree(
                        key: const Key('home-greeting'),
                        child: _Greeting(nickname: nickname),
                      )
                    : const SizedBox.shrink(key: Key('home-greeting')),
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// 다크 판과 흰 판 **사이**에 서는 공개 영상 줄 (2026-09-24 사용자 요청 +
  /// 레퍼런스: 「그 글자를 없애고, 거기에 우리 실제로 업로드된 영상들 나오게」).
  ///
  /// ⛔ **여기 있던 소개 두 줄(「함께 뛸 팀을 만들고,…」)을 되살리지 말 것** —
  /// 사용자가 **그 글자를 없애고** 이 줄로 바꾸라고 정했다. 그 두 줄은
  /// 35pt 라 411 폭에 간신히 들어갔고, 좁은 폰에서는 각 줄이 접혀 네 줄이
  /// 되는 문제도 안고 있었다(이번에 같이 없어졌다).
  ///
  /// 🔴 **자리를 재서 넘긴다.** 위는 다크 판 아랫변, 아래는 **접힌** 흰 판
  /// 윗변이다. 판을 펼치면 스쿼드 판이 이 줄을 덮으므로 따라 올라갈 까닭이
  /// 없다(소개 두 줄이 쓰던 규칙 그대로다).
  Widget _videoStrip(BuildContext context) {
    final geo = _sheetGeometry(context);
    final top = geo.rowTop + _kProfileButtonH + _kTopPanelPadBottom;
    final room = geo.whiteTopCollapsed - top;
    final height = (room - _kVideoStripGap * 2).clamp(0.0, 240.0);
    return Positioned(
      top: top + _kVideoStripGap,
      left: 0,
      right: 0,
      height: height,
      child: HomeVideoStrip(height: height),
    );
  }

  /// 「영상 분석」 — 접혔을 때는 스쿼드 판 **아래에서 하단 바 위까지의 절반**을
  /// 차지하는 네모 판이고 안에 사진이 깔린다. 스쿼드 판을 펼치면 그만큼 밀려
  /// 내려가 **하단 바 바로 위의 납작한 띠**가 되고, 사진은 걷히고 글자만 남는다
  /// (2026-09-15 사용자 요청). 둘 사이는 판을 끄는 손가락을 그대로 따라간다.
  Widget _videoPanel(BuildContext context) {
    final bottomInset = _videoBottomInset(context);
    final geo = _sheetGeometry(context);
    /* 🔴 **이 판이 이제 레이아웃의 기준이다**(2026-09-22, 사용자 요청:
       「영상 분석 판 위에 바로 스쿼드판」). 화면 바닥에 붙어 제 높이
       (`_kVideoOpenH`)를 가지고, **스쿼드 판이 이 판 위에** 자리를 잡는다.
       전에는 반대로 스쿼드 판이 먼저였다 — 둘 다 상대를 기준 삼으면 순환이다. */
    final openTop = geo.videoOpenTop;
    final flatTop = geo.videoFlatTop;
    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        final t = _sheetT;
        /* 🔴 **양옆을 6 띄운다**(2026-09-22 정정, 사용자 요청: 「판의 양옆
           화면 끝이랑 6픽셀 거리」). 2026-09-15 에는 스쿼드 판처럼 화면
           양끝까지 폈었는데, 사진이 들어오면서 판이 **화면에 붙은 띠**가
           아니라 **얹힌 카드**로 읽혀야 해서 갈랐다. */
        return Positioned(
          left: _kVideoSideInset,
          right: _kVideoSideInset,
          bottom: bottomInset,
          top: openTop + (flatTop - openTop) * t,
          child: _VideoAnalysisPanel(
            flat: t,
            onTap: () {
              _closeMenu();
              context.push('/videos');
            },
          ),
        );
      },
    );
  }

  /// 판 · 영상 분석이 함께 쓰는 자리 계산. 둘이 따로 재면 틈이 어긋난다.
  ///
  /// 🔴 **기준이 뒤집혔다**(2026-09-22, 사용자 요청: 「스쿼드판 자체를 맨
  /// 위에서부터 이어지게 하지 말고 … 영상 분석 판 위에 바로」).
  ///
  /// | | 전 | 지금 |
  /// |---|---|---|
  /// | 스쿼드 판 | 화면 **맨 위에 매달린 시트**. 아래로 끌어 펼친다 | 영상 분석 판 **바로 위에 뜬 카드**. **위로** 끌어 펼친다 |
  /// | 기준 | 스쿼드 판이 먼저, 영상 분석이 그 아래 남은 자리 | **영상 분석이 먼저**, 스쿼드 판이 그 위 |
  ///
  /// 🔴 **서로를 기준 삼지 않는다.** 둘 다 상대에게서 자리를 재면 순환이
  /// 된다 — 아래쪽(영상 분석)이 화면 바닥에 붙어 있으므로 **그쪽이 기준**이다.
  ({
    double rowTop,
    double videoOpenTop,
    double videoFlatTop,
    double squadTopCollapsed,
    double squadTopExpanded,
    double shortcutTop,
    double whiteTopCollapsed,
    double whiteTopExpanded,
    double whiteBottom,
    double boardW,
    double boardH,
    double minScale,
    double travel,
  })
  _sheetGeometry(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final safeTop = MediaQuery.paddingOf(context).top;
    final rowTop = safeTop + 8;
    final bottom = size.height - _videoBottomInset(context);

    // 「영상 분석」 — 펼쳤을 때 제 높이, 접으면 납작한 띠. 바닥은 늘 같다.
    final videoOpenTop = bottom - _kVideoOpenH;
    final videoFlatTop = bottom - _kVideoFlatH;

    /* 🔴 **스쿼드 판의 아랫변은 늘 「영상 분석」 판 윗변 바로 위다.** 그래서
       스쿼드 판을 펼치면 영상 분석이 띠로 내려가고 그만큼 스쿼드 판의 아랫변도
       따라 내려간다 — 둘 사이 틈이 **한 번도 안 벌어진다.** */
    final squadBottomCollapsed = videoOpenTop - _kVideoGap;
    final squadBottomExpanded = videoFlatTop - _kVideoGap;

    // 접히면 사진 한 장 높이, 펼치면 워드마크 아래부터 꽉.
    final squadTopCollapsed = squadBottomCollapsed - _kSquadPhotoH;
    final squadTopExpanded = rowTop;

    /* 지름길 알약 줄 — 스쿼드 판 **바로 위**다. 흰 판은 그 줄까지 감싸므로
       윗변이 여기서 한 번 더 올라간다(사용자가 고른 배치).

       🔴 **펼치면 윗변이 스쿼드 판을 따라간다.** 스쿼드 판은 위로 자라
       화면 맨 위([rowTop])까지 가는데, 흰 판이 접힌 자리에 그대로 있으면
       **판이 흰 판 위로 삐져나온다.** 알약은 그 전에 걷힌다. */
    final shortcutTop = squadTopCollapsed - _kShortcutGap - _kShortcutRowH;
    final whiteTopCollapsed = shortcutTop - _kShortcutTopPad;
    final whiteTopExpanded = squadTopExpanded - _kWhiteSheetPad;
    /* 🔴 **아랫변은 영상 분석 판의 바닥 + 테다** — 그 판은 여닫이와 무관하게
       바닥이 늘 같으므로([bottom]) 이 값도 고정이다. */
    final whiteBottom = bottom + _kWhiteSheetPad;

    final panelW = size.width - _kVideoSideInset * 2;
    final boardW = panelW - 20;
    final boardH =
        (squadBottomExpanded -
                squadTopExpanded -
                _kBoardTopInset -
                _kSheetHintH)
            .clamp(0.0, double.infinity);

    /* 스쿼드 그림이 **접힌 사진 판만 한 크기**에서 자라난다 — 사진이 그대로
       판으로 바뀌는 것처럼 보이게 하려는 것이다(사용자: 「늘리면 스쿼드판으로
       자연스럽게 변하게」). 🔴 접혀 있을 때 그림은 **안 보이므로**(투명도 0)
       이 값이 정확할 필요는 없고, **자라나는 출발점**만 정한다. */
    final minScale = boardH <= 0
        ? 1.0
        : (_kSquadPhotoH / boardH).clamp(0.25, 1.0);

    /* 🔴 **끄는 거리는 판 윗변이 움직이는 거리다.** 전에는 아랫변이 움직여서
       그쪽으로 쟀다 — 지금 그 식을 쓰면 손가락보다 판이 느리거나 빠르다. */
    final travel = squadTopCollapsed - squadTopExpanded;

    return (
      rowTop: rowTop,
      videoOpenTop: videoOpenTop,
      videoFlatTop: videoFlatTop,
      squadTopCollapsed: squadTopCollapsed,
      squadTopExpanded: squadTopExpanded,
      shortcutTop: shortcutTop,
      whiteTopCollapsed: whiteTopCollapsed,
      whiteTopExpanded: whiteTopExpanded,
      whiteBottom: whiteBottom,
      boardW: boardW,
      boardH: boardH,
      minScale: minScale,
      travel: travel,
    );
  }

  Widget _squadSheet(
    BuildContext context,
    PlayerCard? card,
    Squad? squad,
    String? ownedTeamId,
  ) {
    final geo = _sheetGeometry(context);

    final board = _role == _Role.captain
        ? SquadBoard(
            myCard: card,
            squad: squad,
            mateCardBuilder: _mateCard,
            /* 🔴 **주장이 아니면 `null` 이다 — 아예 못 집는다.** 옮겨도 403 이라
               끌린 뒤 되돌아가는 것보다 못 집게 하는 편이 낫다. 판이 그 팀의
               것이 아닐 때도 마찬가지다. */
            onSeatMoved: (ownedTeamId != null && squad?.teamId == ownedTeamId)
                ? (memberId, positionCode, col, row) => _moveSeat(
                    ownedTeamId,
                    squad!,
                    memberId,
                    positionCode,
                    col,
                    row,
                  )
                : null,
            onSeatRemoved: (ownedTeamId != null && squad?.teamId == ownedTeamId)
                ? (memberId, slug) => _removeSeat(
                    ownedTeamId,
                    squad!,
                    memberId,
                    slug,
                    card?.publicSlug,
                  )
                : null,
            onSeatTap: (_) => _notReady('선수 넣기'),
          )
        : const _MemberPlaceholder();

    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        /* 판의 자리는 **넘친 값 그대로** 따라간다 — 스프링이 살짝 더 늘었다
           돌아오는 것이 이 움직임의 맛이다. 크기는 조금만 넘치게 묶는다. */
        final raw = _sheet.value;
        final t = raw.clamp(-0.04, 1.04);
        final tc = _sheetT;

        final top =
            geo.squadTopCollapsed +
            (geo.squadTopExpanded - geo.squadTopCollapsed) * raw;
        /* 🔴 **아랫변은 「영상 분석」 판 윗변을 따라간다** — 그쪽과 **같은
           식**이라 둘 사이 틈이 한 번도 안 벌어진다. */
        final bottom =
            (geo.videoOpenTop + (geo.videoFlatTop - geo.videoOpenTop) * raw) -
            _kVideoGap;
        final radius = _kSheetRadius + 8 * tc;
        // 안내 글과 「내 프로필」은 펼치기 **시작하자마자** 걷힌다(앞 4할 안에).
        final fadeOut = (1 - tc / 0.4).clamp(0.0, 1.0);
        /* 🔴 **사진 ↔ 스쿼드 그림은 합이 늘 1인 크로스디졸브다**
           (2026-09-22 정정, 사용자: 「몇 번씩 사라졌다 나타났다 왔다갔다 해」).

           처음엔 둘의 구간을 **어긋나게** 뒀다(사진 0~0.6, 그림 0.4~1.0).
           「가운데에 둘 다 옅은 구간이 있어야 바뀌는 것으로 보인다」고 봤는데
           **정반대였다** — 그 구간에서 둘 다 반투명이라 판이 **한 번 텅 비고**,
           그 뒤 그림이 들어오니 「사라졌다 나타났다」로 보였다. 여닫을 때마다
           그 골짜기를 지나므로 **오갈 때마다** 반복된다.

           🔴 **둘의 투명도를 더하면 반드시 1이어야 한다.** 한쪽이 걷히는
           만큼 다른 쪽이 정확히 차야 빈 순간이 없다.

           🔴 **[Curves.easeInOut] 을 씌운다** — 선형이면 양 끝에서 톡 시작해
           톡 멈춘다. 가운데가 빠르고 양 끝이 느려야 「바뀐다」가 한 동작으로
           읽힌다. */
        final morph = Curves.easeInOut.transform(tc);
        /* 흐림이 드는 정도 — 판이 [_kSheetBlurFrom] 을 넘긴 뒤부터 1 까지.
           🔴 **0 일 때 [BackdropFilter] 는 아무것도 안 흐린다** — 위젯을
           넣었다 뺐다 하지 않는 편이 낫다(트리가 바뀔 때마다 한 번 깜빡인다). */
        final glass = ((tc - _kSheetBlurFrom) / (1 - _kSheetBlurFrom))
            .clamp(0.0, 1.0);
        final scale = geo.minScale + (1 - geo.minScale) * t;

        return Positioned(
          top: top,
          left: _kVideoSideInset,
          right: _kVideoSideInset,
          height: (bottom - top).clamp(0.0, double.infinity),
          child: GestureDetector(
            key: const Key('home-squad-sheet'),
            behavior: HitTestBehavior.opaque,
            onVerticalDragUpdate: (d) => _dragSheet(d, geo.travel),
            onVerticalDragEnd: (d) => _releaseSheet(d, geo.travel),
            child: DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(radius),
                /* 🔴 **네 모서리가 다 둥글다.** 맨 위에 매달려 있을 때는 아래
                   두 곳만 둥글렸는데, 이제 떠 있는 카드라 위도 둥글어야 한다 —
                   윗변이 각지면 화면에 붙어 있는 것처럼 보인다. */
                border: Border.all(
                  color: SilverEdge.silver.withValues(alpha: 0.42),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.45 * tc),
                    blurRadius: 30,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(radius),
                child: Stack(
                  clipBehavior: Clip.hardEdge,
                  children: [
                    /* 판 면 — 접혔을 때는 거의 투명하고, 펼치면 **흰 서리
                       유리**로 건너간다(2026-09-23 사용자 요청).
                       🔴 흐림은 [_kSheetBlurFrom] 뒤에서만 든다 — 까닭은 그
                       상수 주석에(「유리 안에 유리」). */
                    Positioned.fill(
                      child: ClipRect(
                        child: BackdropFilter(
                          filter: ui.ImageFilter.blur(
                            sigmaX: _kSheetBlur * glass,
                            sigmaY: _kSheetBlur * glass,
                          ),
                          child: ColoredBox(
                            color: Color.lerp(
                              _kSheetColor,
                              _kSheetColorOpen,
                              morph,
                            )!,
                          ),
                        ),
                      ),
                    ),
                    /* 🔴 **접혀 있을 때의 얼굴은 사진이다**(2026-09-22 사용자
                       요청). 판을 늘리면 이 사진이 걷히고 그 자리에 스쿼드
                       그림이 자라 든다. */
                    /* 🔴 **`if` 로 넣었다 뺐다 하지 않는다**(2026-09-22
                       정정). 투명도가 0 이 되는 순간 [Image] 를 트리에서
                       빼고 있었는데, 경계를 넘나들 때마다 **다시 붙으면서 한
                       번 더 깜빡였다.** 늘 붙여 두고 투명도만 바꾼다 —
                       투명도 0 이면 어차피 안 그린다. */
                    Positioned.fill(
                      child: IgnorePointer(
                        child: Opacity(
                          opacity: 1 - morph,
                          child: Image.asset(
                            'assets/images/squad_cover.jpg',
                            fit: BoxFit.cover,
                            alignment: Alignment.center,
                          ),
                        ),
                      ),
                    ),
                    /* ⛔ **카드의 두 색을 판에 퍼뜨리던 것을 걷었다**
                       (2026-09-23 사용자 요청: 「판 카드에서 2가지 색상 추출해서
                       하는 거 그냥 빼자. 색상 없애고」).

                       2026-09-22 에 사용자 요청으로 넣었던 것이다 — 사진이
                       걷히는 만큼 `CardSideSmoke` 가 `card.style` 의 바탕색·
                       자국색으로 들었다. 되살릴 일이 있으면 그 커밋에서 꺼낸다.
                       🔴 **판 면([_kSheetColor])은 그대로 둔다** — 그것까지
                       걷으면 스쿼드 그림 뒤가 통째로 비어 글자가 안 읽힌다. */
                    /* 스쿼드 그림 — 사진이 걷힌 자리에서 자라 든다.
                       🔴 **다 펼치기 전에는 안 눌린다**(2026-09-15 사용자
                       요청). 작게 줄어 있을 때 빈 자리(+)가 눌리면 판을 끌려던
                       손가락이 엉뚱한 안내를 띄운다. */
                    Positioned(
                      top: _kBoardTopInset,
                      left: 10,
                      width: geo.boardW,
                      height: geo.boardH,
                      child: IgnorePointer(
                        key: const Key('home-squad-board-lock'),
                        ignoring: tc < 0.98,
                        child: Opacity(
                          opacity: morph,
                          child: Transform.scale(
                            scale: scale,
                            alignment: Alignment.topCenter,
                            child: board,
                          ),
                        ),
                      ),
                    ),
                    /* 접혔을 때의 안내. 펼치기 시작하면 걷힌다.
                       🔴 **판 위쪽이다** — 끄는 방향(위)과 같은 쪽에 있어야
                       「이쪽으로 올려라」가 읽힌다.

                       🔴 **판 윗변에서 정확히 [_kPillInset] 이다**(2026-09-22
                       정정, 사용자: 「영상 분석 시작하기 버튼과 같이 판과의
                       거리 똑같이」).

                       ⚠️ **높이를 주지 않는다.** 전에는 손잡이(28) 아래에
                       [_kSheetHintH](40)짜리 칸을 두고 그 안에 가운데
                       맞춤이었다 — 알약이 **칸 한가운데로 내려앉아** 윗변에서
                       48 이나 떨어져 있었고, 그게 「너무 멀다」의 정체였다.
                       자리를 안 주면 알약이 제 높이만 차지한다. */
                    Positioned(
                      left: 0,
                      right: 0,
                      top: _kPillInset,
                      /* 🔴 **[Opacity] 로 감싸지 않는다 — 알약이 제 알파를
                         받는다**(2026-09-22 정정, 사용자: 「올리거나 내릴 때
                         몇 번씩 사라졌다 나타났다 해」).

                         알약 안에 `BackdropFilter`(유리)가 있는데, 그것을
                         [Opacity] 안에 넣으면 **흐림이 읽을 뒤가 없어진다** —
                         `Opacity` 가 제 레이어를 따로 뜨고 `BackdropFilter`
                         는 그 레이어 안을 뒤로 보기 때문이다. 프레임마다
                         레이어가 생겼다 없어졌다 하면서 **알약이 깜빡인다.**

                         🔴 **유리를 쓰는 것은 [Opacity] 로 걷지 말 것.**
                         면·글자·그림자의 **알파를 직접** 움직인다. */
                      child: IgnorePointer(
                        child: _PullHint(label: '위로 올려 내 팀 만들기', show: fadeOut),
                      ),
                    ),
                    // 팀장 · 팀원 · AI — 판이 다 나온 뒤 차례로 떠오른다([_pills]).
                    // 덜 떠올랐으면 안 눌린다(보이지 않는 단추가 눌리는 것을 막는다).
                    Positioned(
                      top: _kSheetHandleH + 4,
                      left: 10,
                      right: 10,
                      height: _kPillsRowH,
                      child: AnimatedBuilder(
                        animation: _pills,
                        builder: (context, child) => IgnorePointer(
                          ignoring: _pills.value < 0.6,
                          child: child,
                        ),
                        child: _rolePills(),
                      ),
                    ),
                    /* ⛔ **「내 프로필」은 이제 여기 없다**(2026-09-22, 사용자
                       요청: 「내 프로필 맨 오른쪽 위로 옮기고」). 판이 사진
                       얼굴을 갖게 되면서 카드가 **사진 위에서 부딪혔다** —
                       글자가 판 밖으로 삐져나가고 사진 속 선수와 겹쳤다.
                       화면 맨 위 오른쪽([_profileButton])으로 나갔다. */
                    /* 손잡이 — 🔴 **판 윗변으로 옮겼다**(2026-09-22). 판이
                       위로 늘어나므로 잡는 자리도 위여야 한다. 아래에 두면
                       「아래를 잡아 위로 민다」가 되어 손이 헷갈린다. */
                    Positioned(
                      left: 0,
                      right: 0,
                      top: 0,
                      height: _kSheetHandleH,
                      child: GestureDetector(
                        key: const Key('home-squad-handle'),
                        behavior: HitTestBehavior.opaque,
                        onTap: _toggleSheet,
                        child: Center(
                          /* 🔴 **접혀 있는 동안은 안 보인다**(2026-09-22).
                             안내 알약을 판 윗변까지 올리면서 손잡이 줄과
                             **자리가 겹쳤다.** 접혔을 때 무엇을 하라는지는
                             알약이 이미 말하므로 줄은 물러나고, 펼치면
                             (알약이 걷힌 뒤) 도로 나온다.
                             ⚠️ **누르는 자리는 그대로다** — 사라지는 것은
                             줄(그림)뿐이고 바깥 `GestureDetector` 는 산다. */
                          child: Opacity(
                            opacity: tc,
                            child: Container(
                              width: 40 - 12 * tc,
                              height: 4,
                              decoration: BoxDecoration(
                                color: _kOnDark.withValues(alpha: 0.7),
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  /// 팀장 · 팀원은 **가운데**, AI 는 **맨 오른쪽**(2026-09-15 사용자 요청).
  ///
  /// 펼친 뒤에는 「내 프로필」이 오른쪽으로 빠져나가 비므로 AI 가 그 끝을 쓴다.
  /// 웹도 알약이 가운데고 AI 가 오른쪽 끝이다.
  Widget _rolePills() {
    return Stack(
      children: [
        Center(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _stagger(
                0,
                _RolePill(
                  key: const Key('home-role-captain'),
                  label: '팀장',
                  selected: _role == _Role.captain,
                  onTap: () => setState(() => _role = _Role.captain),
                ),
              ),
              const SizedBox(width: 8),
              _stagger(
                1,
                _RolePill(
                  key: const Key('home-role-member'),
                  label: '팀원',
                  selected: _role == _Role.member,
                  onTap: () => setState(() => _role = _Role.member),
                ),
              ),
            ],
          ),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: _stagger(2, _AiButton(onTap: () => _notReady('AI 용병 찾기'))),
        ),
      ],
    );
  }

  /// 알약 하나를 [index] 번째 차례로 띄운다 — 위에서 살짝 내려앉으며 커지고
  /// 선명해진다. 차례마다 0.16 씩 늦고, 끝에서 아주 조금 튀어 안착한다.
  Widget _stagger(int index, Widget child) {
    final start = index * 0.16;
    final curve = CurvedAnimation(
      parent: _pills,
      curve: Interval(
        start,
        (start + 0.62).clamp(0.0, 1.0),
        curve: Curves.easeOutBack,
      ),
      reverseCurve: Curves.easeIn,
    );
    return AnimatedBuilder(
      animation: curve,
      builder: (context, child) {
        final v = curve.value;
        return Opacity(
          opacity: v.clamp(0.0, 1.0),
          child: Transform.translate(
            offset: Offset(0, -12 * (1 - v)),
            child: Transform.scale(scale: 0.86 + 0.14 * v, child: child),
          ),
        );
      },
      child: child,
    );
  }
}

/// 접힌 스쿼드 판 위쪽의 **안내 알약** — 「위로 올려 내 팀 만들기」.
///
/// 🔴 **[_StartAnalysisPill] 과 같은 재질이다**(2026-09-22 사용자 요청:
/// 「영상 분석 시작하기 버튼처럼 똑같이 글래스랑 블러」) — 유리 + 흐림 +
/// 해그림자. 둘이 한 화면에 있으니 재질이 갈리면 따로 논다.
///
/// 🔴 **다만 외곽선은 없다**(사용자 요청). 도는 실버는 **「여기를 눌러라」는
/// 표시**라 진짜 단추 하나에만 붙인다 — 이쪽은 안 눌린다.
///
/// ⛔ **화살표를 되살리지 말 것**(사용자 요청: 「화살표 그냥 빼고」).
/// 알약이 되면서 **알약 자체가 「무엇을 하라」를 말하고** 화살표는 자리만
/// 먹었다.
///
/// 🔴 **아주 미세하게 위아래로 떠다닌다**(2026-09-22 사용자 요청).
/// ⚠️ 앞서 여기 「까닥이는 애니메이션을 없애서 `StatelessWidget` 이 됐다」고
/// 적었던 것을 **정정한다** — 다시 움직이므로 다시 상태를 갖는다. 움직이는
/// 것이 **화살표가 아니라 알약 전체**인 것이 그때와 다르다.
///
/// ⚠️ **안 눌린다.** 생김새는 단추인데 판 전체가 끄는 자리다 — 부르는 쪽이
/// [IgnorePointer] 로 감싼다.
/// 흰 판 맨 위 줄의 지름길 알약 하나 — 아이콘 위, 글자 아래
/// (2026-09-23 사용자가 준 그림 배치).
///
/// 🔴 **유리가 아니다.** 흰 판 위라 흐릴 뒤가 없고, 이 화면의 다른 알약
/// (`GlassPill`)을 그대로 가져오면 아무것도 안 보인다. 색 면 + 가는 테로
/// 간다 — `flutter/CLAUDE.md` 의 「층을 쌓아야 하면 흐림 없이 색만 얹는다」와
/// 같은 판단이다.
///
/// ⚠️ **흰 면이었다 (2026-09-23 정정)** — 사용자가 면을 화면 바탕과 같은
/// 딥그린으로, 글자·아이콘을 순백으로 뒤집었다.
class _ShortcutPill extends StatelessWidget {
  const _ShortcutPill({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      /* 알약 모양은 [StadiumBorder] 가 낸다 — 반지름을 숫자로 주면 높이를
         바꿀 때마다 같이 고쳐야 하고, 한 번 어긋나면 양 끝이 찌그러진다. */
      color: _kPillFill,
      shape: const StadiumBorder(
        side: BorderSide(
          color: _kPillLineOnWhite,
          width: _kSilverOnWhiteWidth,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 22, color: _kOnWhite),
            const SizedBox(height: 5),
            /* 🔴 한 줄로 묶는다 — 「경기장 예약」이 좁은 기기에서 두 줄로
               접히면 알약 셋의 높이가 갈린다. */
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: _kOnWhite,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 인사말 두 줄의 글자 차림 — 🔴 **다크 판 위**라 흰색이다.
const TextStyle _kGreetStyle = TextStyle(
  fontFamily: _kKoFont,
  // 🔴 번들한 굵기가 Black 하나다 — [_kKoFont] 주석 참고.
  fontWeight: FontWeight.w900,
  fontSize: _Greeting.fontSize,
  height: 1.2,
  color: _kOnDark,
);

/// 인사말 한 덩이 — **화면 왼쪽 밖에서 미끄러져 들어오고**, 로고가 내려앉으면
/// 그때 손을 흔든다 (2026-09-24 사용자 요청: 「글자랑 아이콘 supersub 도착할
/// 때까지 안 나오는 거 하지 말고 처음부터 왼쪽 밖에서 들어오게 하고, 도착하면
/// 그때 손 흔드는 애니메이션 나오게 해줘」).
///
/// ⚠️ **들어오는 것은 더 이상 [kBrandSettled] 를 안 기다린다** — 2026-09-23
/// 에는 기다렸다(「내려 앉기 전까지는 안보였다가 딱 내려 앉으면…」). 그때
/// 기다린 까닭은 **인트로가 도는 동안 홈이 이미 그 아래에 지어져 있어서**,
/// 안 기다리면 잉크가 걷히는 순간 **이미 다 나타난 채로** 드러나기 때문이었다.
/// 🔴 **지금은 그 문제가 안 생긴다** — 인트로 뒤에서 벌어지는 일이 「없던 것이
/// 나타나는 것」이 아니라 **화면 밖에서 안으로 들어오는 것**이라, 잉크가 걷힐
/// 때 이미 제자리에 있어도 어색하지 않다.
///
/// 🔴 **흔들기만 [kBrandSettled] 를 기다린다** — 로고가 앉는 순간이 신호다.
///
/// 🔴 **잦아들게 흔든다.** 같은 폭으로 흔들다 뚝 멈추면 「멈췄다」가 아니라
/// 「끊겼다」로 보인다 — 진폭을 시간에 따라 0 으로 떨어뜨리면 손이 제자리에
/// 내려앉는다.
///
/// 🔴 **회전 중심을 손목 쪽(왼쪽 아래)에 둔다.** 한가운데를 중심으로 돌리면
/// 손이 **제자리에서 빙글거려** 흔드는 것으로 안 읽힌다.
class _Greeting extends StatefulWidget {
  const _Greeting({required this.nickname});

  final String nickname;

  /// 왼쪽 밖에서 들어오는 시간.
  static const enter = Duration(milliseconds: 700);

  /// 🔴 **제 폭의 몇 배만큼 왼쪽에서 출발하는가.** 1 이면 제 상자 폭만큼
  /// 왼쪽인데, 이 덩이의 상자는 **인사말 칸 전체 폭**(판 안쪽 좌우 여백을 뺀
  /// 만큼)이라 1 만 해도 화면 밖이다. 🔴 **1.05 로 조금 더 민다** — 왼쪽
  /// 여백([_kGreetLeft])만큼은 상자 밖이라, 1 이면 **글자 왼쪽 끝이 화면
  /// 안에 걸친 채로** 출발한다.
  static const enterFrom = 1.05;

  /// 몇 번 흔드는가(왕복 기준).
  static const waves = 4;

  static const wavePeriod = Duration(milliseconds: 1800);

  /// 최대 기울기(라디안).
  static const swing = 0.30;

  /// 글자·아이콘 크기(2026-09-23 사용자 요청: 「글자 살짝 더 키우자」).
  static const fontSize = 26.0;
  static const iconSize = 38.0;

  @override
  State<_Greeting> createState() => _GreetingState();
}

class _GreetingState extends State<_Greeting> with TickerProviderStateMixin {
  /// 왼쪽 밖에서 들어오는 것 — 🔴 **화면이 지어지는 대로 곧장 돈다.**
  late final AnimationController _enter = AnimationController(
    vsync: this,
    duration: _Greeting.enter,
  );
  late final AnimationController _wave = AnimationController(
    vsync: this,
    duration: _Greeting.wavePeriod,
  );

  bool _waved = false;

  @override
  void initState() {
    super.initState();
    _enter.forward();
    kBrandSettled.addListener(_onSettled);
    _onSettled();
  }

  /// 🔴 **한 번만 흔든다.** [kBrandSettled] 는 인트로가 오갈 때 값이 여러 번
  /// 바뀔 수 있는데, 그때마다 다시 걸면 손이 계속 처음부터 흔들린다.
  void _onSettled() {
    if (!kBrandSettled.value || _waved) return;
    _waved = true;
    _wave.forward();
  }

  @override
  void dispose() {
    kBrandSettled.removeListener(_onSettled);
    _enter.dispose();
    _wave.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([_enter, _wave]),
      builder: (context, _) {
        final e = Curves.easeOutCubic.transform(_enter.value);
        final w = _wave.value;
        // 진폭이 1 에서 0 으로 잦아든다. 안 흔드는 동안은 w = 0 이라 각도도 0.
        final amp = _Greeting.swing * (1 - w);
        final angle = amp * math.sin(2 * math.pi * _Greeting.waves * w);

        /* 🔴 **제 폭을 단위로 민다**([FractionalTranslation]). 화면 폭을 읽어
           픽셀로 밀면 기기마다 「얼마나 밖인지」가 달라지는데, 이 덩이의 상자는
           **인사말 칸 전체 폭**이라 제 폭의 1배만 밀어도 화면 밖이다. */
        return FractionalTranslation(
          translation: Offset(-_Greeting.enterFrom * (1 - e), 0),
          /* 🔴 **손이 글자 위에 선다**(2026-09-24 사용자 확정). 손이 제 줄을
             따로 쓰면 인사말 덩이가 44(손 38 + 틈 6) 높아지는데, 판 높이를
             정하는 것은 **「내 프로필」 카드**(최소 225.9)라 **판은 안 커진다** —
             필요한 높이 213.9 로 12 남는다(실기기에서 계산).

             ⚠️ **같은 날 옆으로 옮겼다 돌아왔다.** 그때는 판이 흰 판 바로
             위까지 늘어나 있어 그 44 가 모자랐다. 🔴 **여유가 12뿐이니**
             카드를 줄이거나 인사말을 키우면 판이 자라 소개 두 줄과 부딪힌다. */
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Transform.rotate(
                // 🔴 시험이 이 키로 각도를 읽는다 — 흔들기가 언제 시작하는지.
                key: const Key('home-greeting-hand'),
                angle: angle,
                alignment: Alignment.bottomLeft,
                child: const Icon(
                  Symbols.waving_hand,
                  size: _Greeting.iconSize,
                  color: _kOnDark,
                  weight: 300,
                  grade: 0,
                  opticalSize: 24,
                ),
              ),
              const SizedBox(height: 6),
              /* 🔴 **닉네임은 다음 줄이다** (2026-09-24 사용자 요청:
                 「안녕하세요, 다음에 나오는 닉네임은 다음줄로 내려버리자.
                 길 수도 있으니까」).

                 🔴 **한 [Text] 에 `\n` 을 넣지 않는다** — 시험과 다음 사람이
                 글자로 집을 때 한 덩이 문자열이 되어, 어느 줄을 가리키는지
                 못 고른다(자리를 재는 시험이 실제로 아랫줄을 집어야 했다).
                 따로 두면 각 줄의 자리도 따로 잴 수 있다. */
              const Text('안녕하세요,', style: _kGreetStyle),
              Text(
                '${widget.nickname} 님',
                /* 🔴 **자르지 않고 줄을 바꾼다.** 칸이 [_kGreetRight] 에서
                   끊겨 있으므로(「내 프로필」 앞), 아주 긴 이름은 여기서 또 한
                   줄로 내려간다 — 판은 이 위젯을 **담고** 있어서 그만큼 같이
                   커진다. */
                style: _kGreetStyle,
              ),
            ],
          ),
        );
      },
    );
  }
}

/// 로고가 **앉고 2초 뒤에 초록에서 흰색으로 물든다**(2026-09-23 사용자 요청:
/// 「홈페이지에 도착하면 2초 뒤에 흰색으로 바뀌게 … 부드럽고 아주 자연스럽게」).
///
/// 🔴 **2초는 「홈이 지어진 때」가 아니라 「로고가 앉은 때」부터 잰다.**
/// 인트로가 도는 동안 홈은 **이미 그 아래에 지어져 있다**(`intro_gate` 가
/// 착지점의 화면 좌표를 읽으려고 일부러 그렇게 해 둔 것이다). 화면이 뜨는
/// 대로 재면 **로고가 날아오기도 전에 흰색이 되고**, 착지하는 순간 비행
/// 글자(초록)로 **되돌아간 것처럼** 보인다. 그래서 [kBrandSettled] 를 기다린다.
///
/// 🔴 **[BrandMark] 를 그대로 쓴다** — 색만 바깥에서 준다. 그 위젯이 비행 중에
/// 제 글자를 감추는 일([kBrandFlightInProgress])을 맡고 있어서, 맨 [Text] 로
/// 바꾸면 날아오는 글자와 여기 글자가 동시에 보인다.
class _BrandFade extends StatefulWidget {
  const _BrandFade();

  /// 앉은 뒤 기다리는 시간.
  ///
  /// ⚠️ **2초 → 1초 (2026-09-23 사용자 요청: 「1초 더 줄여도 돼? 도착하고
  /// 변하기까지 시간이 너무 길다」).** 물드는 시간([fade])은 그대로 뒀다 —
  /// 길다고 한 것은 **기다리는 쪽**이지 변하는 속도가 아니다.
  static const delay = Duration(seconds: 1);

  /// 물드는 데 걸리는 시간 — 🔴 **넉넉히 준다.** 짧으면 「툭 바뀐다」가 되어
  /// 「부드럽고 아주 자연스럽게」와 반대가 된다.
  static const fade = Duration(milliseconds: 1100);

  @override
  State<_BrandFade> createState() => _BrandFadeState();
}

class _BrandFadeState extends State<_BrandFade>
    with SingleTickerProviderStateMixin {
  late final AnimationController _fade = AnimationController(
    vsync: this,
    duration: _BrandFade.fade,
  );

  Timer? _wait;

  @override
  void initState() {
    super.initState();
    kBrandSettled.addListener(_onSettled);
    _onSettled();
  }

  /// 🔴 **한 번만 건다.** [kBrandSettled] 는 인트로가 오갈 때 값이 여러 번
  /// 바뀔 수 있는데, 그때마다 타이머를 새로 걸면 2초가 계속 미뤄진다.
  void _onSettled() {
    if (!kBrandSettled.value || _wait != null) return;
    _wait = Timer(_BrandFade.delay, () {
      if (mounted) _fade.forward();
    });
  }

  @override
  void dispose() {
    kBrandSettled.removeListener(_onSettled);
    _wait?.cancel();
    _fade.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _fade,
      builder: (context, _) => BrandMark(
        key: kBrandLandingKeyHome,
        fontSize: kBrandHomeSize,
        /* 🔴 **[Curves.easeInOut] 을 씌운다** — 선형이면 시작과 끝이 톡
           끊겨 보인다. 가운데가 빠르고 양 끝이 느려야 한 동작으로 읽힌다. */
        color: Color.lerp(
          AppTheme.seed,
          Colors.white,
          Curves.easeInOut.transform(_fade.value),
        )!,
      ),
    );
  }
}

class _PullHint extends StatefulWidget {
  const _PullHint({required this.label, required this.show});

  final String label;

  /// 0 이면 없는 것처럼, 1 이면 다 보이게.
  ///
  /// 🔴 **부르는 쪽이 [Opacity] 를 쓰지 않고 이 값을 준다** — 위 호출부 주석
  /// 참고(유리를 `Opacity` 로 걷으면 깜빡인다).
  final double show;

  @override
  State<_PullHint> createState() => _PullHintState();
}

class _PullHintState extends State<_PullHint>
    with SingleTickerProviderStateMixin {
  /// 🔴 **아주 느리고 아주 작다.** 빠르거나 크면 「떠 있다」가 아니라
  /// 「흔들린다」가 되어 사진에서 눈이 끌려간다.
  static const double _floatPx = 3;

  late final AnimationController _float = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2600),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // 「애니메이션 줄이기」를 켠 사람에게는 제자리에 선다.
    if (MediaQuery.disableAnimationsOf(context)) {
      _float
        ..stop()
        ..value = 0;
    } else if (!_float.isAnimating) {
      _float.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _float.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const r = Radius.circular(_StartAnalysisPill.radius);
    final show = widget.show.clamp(0.0, 1.0);
    return AnimatedBuilder(
      animation: _float,
      builder: (context, child) {
        final e = Curves.easeInOut.transform(_float.value);
        return Transform.translate(
          // 떠다니는 것 + 걷힐 때 위로 물러나는 것을 **한 번에** 더한다.
          offset: Offset(0, -_floatPx + 2 * _floatPx * e - 8 * (1 - show)),
          child: child,
        );
      },
      child: Center(
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: const BorderRadius.all(r),
            boxShadow: sunShadow(show),
          ),
          child: ClipRRect(
            borderRadius: const BorderRadius.all(r),
            child: BackdropFilter(
              // 🔴 흐림도 [show] 를 탄다 — 걷힐 때 흐림만 남으면 **유령 같은
              //    네모**가 보인다.
              filter: ui.ImageFilter.blur(
                sigmaX: kPillBlur * show,
                sigmaY: kPillBlur * show,
              ),
              child: ColoredBox(
                // 시작하기 알약과 **같은 값** — 둘이 한 재질로 읽힌다.
                color: Colors.white.withValues(alpha: 0.16 * show),
                child: Padding(
                  /* 🔴 **왼쪽을 줄였다**(2026-09-22 사용자 요청: 「컴팩트하게
                     왼쪽 패딩 줄이고」). 화살표가 있던 자리라 넉넉했는데
                     화살표를 빼면서 그만큼 비었다 — 좌우를 같게 맞췄다. */
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 9,
                  ),
                  child: Text(
                    widget.label,
                    style: TextStyle(
                      /* 🔴 **흰 글자다**(2026-09-22 정정). 흰 면일 때는
                         검정이었는데 면을 걷어 유리가 되면서 **뒤의 사진이
                         비친다** — 판을 끌면 어두운 자리가 올라와서 검정으로
                         두면 그때 묻힌다. 시작하기 알약과도 같은 색이 된다. */
                      color: Colors.white.withValues(alpha: show),
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 팀장 · 팀원 알약 — AI 단추와 **같은 유리 알약**이다(2026-09-15 사용자 요청,
/// 전에는 검은 면을 깔았다). 고른 것은 민트 글자에 흰 테두리를 한 겹 더 둘러
/// 갈린다 — 유리 면이 같으니 색만으로는 어느 쪽인지 안 보인다.
class _RolePill extends StatelessWidget {
  const _RolePill({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      /* 🔴 **유리에서 실버 테두리로 바꿨다**(2026-09-21, 사용자 제안). 알약이
         유리 판 **안에** 들어가면 「유리 안에 유리」가 되어 프레임째 사라진다.
         가는 은빛 선 하나로 경계를 내면 그 문제가 없고, 뒤의 빛무리도 비친다. */
      child: SizedBox(
        height: 38,
        child: SilverEdge(
          radius: 19,
          strong: selected,
          child: Material(
            type: MaterialType.transparency,
            child: InkWell(
              borderRadius: BorderRadius.circular(19),
              onTap: onTap,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                child: Center(
                  widthFactor: 1,
                  child: Text(
                    label,
                    style: TextStyle(
                      fontSize: 15,
                      color: selected ? AppTheme.seed : _kOnDark,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// AI 단추 — 웹과 같은 세리프 「AI」를 유리 알약에 얹었다.
///
/// ⚠️ 아직 아무것도 안 연다. 웹은 추천 판 · 챗봇을 여는데, 🔴 **챗봇은 Gemini
/// 키가 웹 서버에만 있어** 앱에서 부를 경로부터 정해야 한다(웹 `/api/chat` 을
/// 부를지, 백엔드로 옮길지).
class _AiButton extends StatelessWidget {
  const _AiButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 38,
      width: 54,
      child: GlassPanel(
        radius: 19,
        child: Material(
          type: MaterialType.transparency,
          child: InkWell(
            key: const Key('home-ai'),
            onTap: onTap,
            child: const Center(
              child: Text(
                'AI',
                style: TextStyle(
                  fontFamily: 'YoungSerif',
                  fontSize: 18,
                  color: _kOnDark,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 「팀원」을 골랐을 때 판 자리에 서는 것. 웹은 **사람을 구하는 팀 목록**
/// (`TeamSeek`)이 스쿼드 판을 대신 선다 — 앱은 아직 자리만 잡아 둔다.
class _MemberPlaceholder extends StatelessWidget {
  const _MemberPlaceholder();

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      radius: _kCardRadius,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.groups_outlined, size: 36, color: AppTheme.seed),
            const SizedBox(height: 10),
            const Text(
              '사람을 구하는 팀',
              style: TextStyle(color: _kOnDark, fontSize: 16),
            ),
            const SizedBox(height: 6),
            Text(
              '준비 중',
              style: TextStyle(
                color: _kOnDark.withValues(alpha: 0.55),
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 「영상 분석」 판. [flat] 이 0 이면 사진이 깔린 큰 판, 1 이면 하단 바 위의
/// 납작한 띠다(스쿼드 판을 펼친 정도 그대로).
///
/// - 큰 판: 사진이 판을 **통째로** 채우고 그 위에 웹과 같은 아이콘
///   (`camera_video`) · 「영상 분석」 · 긴 설명이 가운데 선다.
/// - 띠: 사진 · 설명은 걷히고 아이콘 · 「영상 분석」 · 화살표만 한 줄로 남는다.
/// - 사이: 앞 절반 동안 큰 판의 글이 걷히고, 뒤 절반 동안 띠의 글이 들어온다 —
///   둘이 동시에 보이면 글이 겹쳐 지저분하다.
///
/// 🔴 **소개 영상을 걷었다**(2026-09-22, 사용자 요청: 「아래 영상은 아예 빼고
/// … 사진을 원래 영상이 있던 자리에」). 전에는 판을 위아래로 갈라 **위 절반은
/// 글, 아래 절반은 되풀이되는 영상**이었다. 지금은 판 하나에 사진 한 장이다.
///
/// ⚠️ `assets/videos/analysis_showcase.mp4`(약 1MB)가 **이제 아무 데서도
/// 안 쓰인다.** `pubspec.yaml` 이 `assets/videos/` 를 통째로 싣고 있어 앱에는
/// 계속 들어간다 — 지울지는 따로 정한다.
///
/// 🔴 **누르는 자리가 둘로 갈린다**(2026-09-22 사용자 요청: 「영상분석
/// 시작하기 버튼만 눌리게」).
///
/// | 상태 | 누르는 곳 |
/// |---|---|
/// | 큰 판 | 사진 한가운데의 **「영상 분석 시작하기」 알약 하나뿐** |
/// | 납작한 띠 | 띠 **전체**(한 줄짜리 이동 줄이라 알약을 세울 자리가 없다) |
///
/// 🔴 **`home-video-analysis` 키는 판 바깥 테두리에 둔다.** 시험이 이 키로
/// 판의 **크기·자리를 잰다**(`home_screen_test.dart`) — 누르는 위젯으로
/// 옮기면 큰 판에서 알약 크기가 잡혀 그 시험이 엉뚱한 것을 재게 된다.
class _VideoAnalysisPanel extends StatefulWidget {
  const _VideoAnalysisPanel({required this.flat, required this.onTap});

  final double flat;
  final VoidCallback onTap;

  @override
  State<_VideoAnalysisPanel> createState() => _VideoAnalysisPanelState();
}

class _VideoAnalysisPanelState extends State<_VideoAnalysisPanel>
    with SingleTickerProviderStateMixin {
  /// 떠나면서 사진이 흐려지는 시간(2026-09-22 사용자 요청: 「누르면 FUTSAL
  /// 사진만 블러처리로 흐려지면서 영상 분석 페이지로」).
  ///
  /// 🔴 **짧게 둔다.** 화면을 떠나기 전에 손을 붙잡는 연출이라, 길면 「눌렀는데
  /// 안 간다」가 된다.
  /// 떠나는 연출의 길이.
  ///
  /// 🔴 **잉크가 화면을 덮는 시간에 맞춘다**(2026-09-22 정정). 라우트 전환은
  /// `_kHomeTransition` = 1800ms 짜리 `InkPeel` 이고 `coverUntil: 0.35` 라
  /// **630ms 에 화면이 다 덮인다.** 그 안에 끝나야 「사진이 물러나는 것」과
  /// 「잉크가 덮는 것」이 **한 동작**으로 읽힌다.
  static const Duration _leaveMs = Duration(milliseconds: 620);

  late final AnimationController _leave = AnimationController(
    vsync: this,
    duration: _leaveMs,
  );

  /// 멎는 쪽이 느린 곡선 — 처음엔 빠르게 풀리고 끝에서 잦아든다.
  ///
  /// 🔴 **선형으로 두지 말 것.** 흐림이 일정한 속도로 세지면 **기계가 값을
  /// 올리는 것**처럼 보인다(앞 회차에 사용자가 「부자연스럽다」고 한 것의
  /// 절반이 이것이다).
  late final Animation<double> _leaveCurve = CurvedAnimation(
    parent: _leave,
    curve: Curves.easeOutCubic,
  );

  @override
  void dispose() {
    _leave.dispose();
    super.dispose();
  }

  /// 🔴 **흐림과 화면 이동을 **동시에** 시작한다**(2026-09-22 정정, 사용자:
  /// 「블러처리되는거 진짜 너무 부자연스럽고 이상해」).
  ///
  /// 전에는 `await _leave.forward()` 로 **흐림이 다 끝난 뒤에** 옮겨 갔다.
  /// 그러면 260ms 짜리 흐림 한 동작이 끝나고 **그 다음에** 1800ms 짜리 잉크
  /// 전환이 새로 시작해서, 서로 관계없는 동작 **둘**로 보였다 — 게다가 260ms
  /// 안에 시그마를 0→14 로 밀어 올리니 **툭 튀었다.**
  ///
  /// 지금은 잉크가 덮는 동안 그 **아래에서** 사진이 물러난다. 보이는 것은
  /// 「눌렀다 → 사진이 멀어지며 잉크가 덮는다」 하나다.
  ///
  /// 🔴 **두 번 눌리지 않게 막는다** — 떠나는 동안 또 누르면 화면이 두 장
  /// 쌓인다(뒤로 가기가 두 번 필요해진다).
  Future<void> _start() async {
    if (_leave.isAnimating || _leave.isCompleted) return;
    _leave.forward();
    widget.onTap();
    /* 🔴 **되돌려 놓는다.** 이 화면은 뒤로 왔을 때 **그대로 살아 있으므로**
       (`push` 는 홈을 안 버린다) 흐림을 안 풀면 돌아왔을 때 사진이 흐린 채다.
       🔴 **잉크가 다 덮은 뒤에**(630ms) 푼다 — 그 전에 풀면 사용자가 보는
       앞에서 사진이 **도로 선명해졌다가** 덮인다. */
    await Future<void>.delayed(const Duration(milliseconds: 900));
    if (mounted) _leave.value = 0;
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.flat;
    final bigText = (1 - t * 2).clamp(0.0, 1.0);
    final flatText = ((t - 0.5) * 2).clamp(0.0, 1.0);
    final radius = 28 - 10 * t;

    /* 🔴 **스쿼드 판과 같은 차림**(2026-09-21, 사용자 요청 「영상분석 쪽 판도
       같이」) — 면 색은 거의 없고 **은빛 테두리**가 경계를 낸다. 면을 깔면
       뒤의 빛무리가 여기서 끊겨 화면 아래쪽만 검게 죽는다.

       🔴 **테 값을 갈았다**(2026-09-23 사용자 요청: 「외곽선에 제일 얇은
       세련된 실버 색상」). 뒤에 흰 판이 깔리면서 옛 값
       (`SilverEdge.silver` 알파 0.28 · 1px)이 **흰 바탕에 붙어 사라졌다** —
       그 값은 검은 바탕용이다. 왜 이 색·이 굵기인지는 [_kSilverOnWhite]. */
    return DecoratedBox(
      key: const Key('home-video-analysis'),
      /* 🔴 **자식 「앞」에 그린다**(2026-09-23). 기본값(뒤)으로 두면 아래
         [ClipRRect] 가 **같은 모서리로 판을 꽉 채워 테를 통째로 덮는다** —
         가장자리 픽셀을 재서 잡았다(`#fefefe`, 흰색과 1단 차이). 검은
         바탕일 때는 사진이 어두워 테가 있는 것처럼 보였을 뿐이다.
         🔴 **되돌리지 말 것** — 뒤로 옮기면 선이 조용히 사라진다. */
      position: DecorationPosition.foreground,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(
          color: _kSilverOnWhite,
          width: _kSilverOnWhiteWidth,
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: Material(
          // 반투명이라 뒤의 빛무리가 비친다(위 `_kSheetColor` 주석).
          color: _kSheetColor,
          child: InkWell(
            /* 🔴 **띠일 때만 판 전체가 눌린다** — 큰 판에서는 `null` 이라
               아무 데나 눌러도 안 간다(위 표). `null` 이면 `InkWell` 이
               손짓을 아예 안 받으므로 아래의 알약이 그대로 받는다. */
            onTap: t > 0.5 ? widget.onTap : null,
            child: Stack(
              fit: StackFit.expand,
              children: [
                /* 사진 · 가운데 알약. 걷힐 때 살짝 위로 뜬다.
                   🔴 **글과 같은 [Opacity] 안에 둔다.** 판이 납작한 띠가 될 때
                   글만 걷히고 사진이 남으면, 띠 한 줄짜리 글 뒤에서 사진이
                   **가로로 짓눌린 채** 비친다.

                   🔴 **[IgnorePointer] 로 감싸지 않는다** — 안에 눌러야 하는
                   알약이 들어 있다(전에는 글자뿐이라 감쌌다). */
                Opacity(
                  opacity: bigText,
                  child: Transform.translate(
                    offset: Offset(0, -12 * (1 - bigText)),
                    child: _VideoPanelCover(
                      leave: _leaveCurve,
                      onStart: _start,
                    ),
                  ),
                ),
                // 띠의 글 — 한 줄. 들어올 때 살짝 아래에서 올라온다.
                IgnorePointer(
                  child: Opacity(
                    opacity: flatText,
                    child: Transform.translate(
                      offset: Offset(0, 10 * (1 - flatText)),
                      child: const _VideoFlatCopy(),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// 큰 판을 채우는 사진과 그 위의 **「영상 분석 시작하기」 알약 하나**.
///
/// 🔴 **긴 설명을 걷었다**(2026-09-22 사용자 요청: 「사진 안에 긴 내용들 다
/// 삭제」). 아이콘·제목·두 줄 설명이 사진 위에 얹혀 있었는데, 사진이 주인공이
/// 되면서 글이 사진을 가렸다. 제목은 **걷혔고**(판이 무엇인지는
/// 사진이 말한다), 여기 남는 것은 **누를 것 하나**뿐이다.
class _VideoPanelCover extends StatelessWidget {
  const _VideoPanelCover({required this.leave, required this.onStart});

  /// 떠나는 흐림의 진행도(0~1).
  final Animation<double> leave;
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: Stack(
        fit: StackFit.expand,
        children: [
          /* 🔴 **사진만 흐려진다**(사용자 요청: 「그 FUTSAL 사진만 블러처리로
             흐려지면서」). 그래서 흐림이 판 전체가 아니라 [Image] **한 장을**
             감싼다 — 위의 알약은 또렷한 채로 남아 「내가 방금 누른 것」이
             끝까지 보인다.

             🔴 **`ImageFiltered` 를 쓴다(`BackdropFilter` 가 아니다).**
             `BackdropFilter` 는 **뒤에 이미 그려진 것**을 흐리므로 판 뒤의
             바탕까지 같이 먹는다. 여기서 흐릴 것은 이 한 장이다.

             🔴 **시그마가 0 이면 감싸지 않는다** — `sigma: 0` 은 기기에 따라
             그리지 않거나 경고를 낸다. 평소(안 떠날 때)가 그 상태다. */
          AnimatedBuilder(
            animation: leave,
            builder: (context, child) {
              final v = leave.value;
              if (v < 0.001) return child!;
              /* 🔴 **흐림 혼자 두지 않는다 — 살짝 밀어 넣는다**(2026-09-22
                 정정). 제자리에서 흐리기만 하면 **초점이 나간 사진**이지
                 움직임이 아니다. 아주 조금(4%) 키우면 「안으로 들어간다」로
                 읽혀서, 다음 화면으로 가는 것과 뜻이 맞는다.

                 ⚠️ 배율을 더 키우지 말 것 — 판이 작아서 6% 만 넘어가도
                 「사진이 튀어나온다」가 된다. */
              return Transform.scale(
                scale: 1 + 0.04 * v,
                child: ImageFiltered(
                  /* 🔴 **`TileMode.clamp` 이다 — `decal` 이 아니다**(정정).
                     `decal` 은 그림 **바깥을 투명으로** 보고 섞어서, 흐려질수록
                     네 변이 **투명하게 녹아** 판의 검은 면이 비쳤다. 사진이
                     흐려지는 게 아니라 **가장자리부터 사라지는** 것처럼 보인
                     것이 그 때문이다. `clamp` 는 가장자리 색을 늘려 잡으므로
                     변이 끝까지 제 색이다. */
                  imageFilter: ui.ImageFilter.blur(
                    sigmaX: 9 * v,
                    sigmaY: 9 * v,
                    tileMode: TileMode.clamp,
                  ),
                  child: child,
                ),
              );
            },
            /* 🔴 **`cover` + 가운데 정렬**(2026-09-22 정정 — 사진이 바뀌면서
               정렬도 같이 바뀌었다).

               옛 사진(FUTSAL)은 **제목이 맨 위**에 있어 가운데로 두면 글자가
               한가운데서 잘렸고, 그래서 **위쪽 정렬**이었다. 지금 사진
               (`VIDEO AGENT`)은 제목도 선수도 **세로 한가운데**에 있어 위쪽을
               맞추면 오히려 **발과 신발이 잘린다.**
               🔴 **사진을 바꾸면 정렬도 다시 본다** — 정렬은 사진의 성질이지
               이 판의 성질이 아니다.

               ⚠️ 판의 비율은 손가락을 따라 **계속 변한다**(스쿼드 판을
               펼칠수록 납작해진다). 그래서 어느 한 비율에 맞춘 고정 크롭을
               원본에 구워 넣지 않았다 — `cover` 가 그때그때 맞춘다. */
            child: Image.asset(
              'assets/images/analysis_cover.jpg',
              fit: BoxFit.cover,
              alignment: Alignment.center,
            ),
          ),
          /* ⛔ **어둡게 까는 겹을 두지 않는다**(2026-09-22, 사용자 요청:
             「글자 뒤에 있는 검정 그라데이션 빼」). 한 번 넣었다가 뺀 것이다 —
             사진이 주인공이고, 눌러 놓으면 「FUTSAL」과 선수가 죽는다.

             ⚠️ 흰 글자가 사진에 묻히는 문제는 이제 **알약이 대신 푼다** —
             흰 면에 검은 글자라 사진이 밝든 어둡든 똑같이 읽힌다. 막을
             다시 깔지 말 것. */
          /* 🔴 **알약도 같이 물러난다.** 사진만 멀어지고 알약이 제자리에
             또렷하면 **알약만 화면에 붙어 있는 것**처럼 보여 층이 갈라진다.
             사진보다 **빨리** 걷혀서(×1.6) 마지막엔 사진만 남는다. */
          /* 🔴 **사진 한가운데다 (2026-09-23 사용자 요청: 「사진의 가운데에
             두고」).**

             ⚠️ **오른쪽 아래 구석이었다** — 2026-09-22 에 사용자가 그리로
             빼라고 한 자리다. 까닭은 「사진이 `VIDEO AGENT` 로 바뀌면서
             제목 글자 위에 얹혔다」였고, 가운데로 돌아온 지금 **그 겹침은
             다시 난다.** 사용자에게 알리고 진행한 것이니, 겹쳐 보인다는
             지적이 오면 이 자리부터 본다. */
          Align(
            alignment: Alignment.center,
            child: Padding(
              padding: const EdgeInsets.all(_kPillInset),
              child: AnimatedBuilder(
                animation: leave,
                builder: (context, child) => Opacity(
                  opacity: (1 - leave.value * 1.6).clamp(0.0, 1.0),
                  child: child,
                ),
                child: _StartAnalysisPill(onTap: onStart),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 워드마크의 **반쪽** — `SUPER` 와 `SUB` 가 같은 차림을 나눠 쓴다.
///
/// 🔴 **둘을 한 [Text] 로 합치지 않는다.** 판을 내릴 때 **서로 반대쪽으로**
/// 나가야 해서 각자 움직일 수 있어야 한다.
///
/// ⚠️ **`letterSpacing` 덕분에 갈라도 글자 사이가 안 벌어진다** —
/// `letterSpacing` 은 글자마다 **뒤에** 붙으므로 `SUPER` 의 `R` 뒤에도 같은
/// 간격이 이미 있다. 그래서 붙여 놓으면 `SUPERSUB` 한 낱말과 **같은 폭**이다.
/* 🔴 **알약 재질 값(`kSunShadow` · `sunShadow()` · `kPillBlur`)을
   `core/widgets/glass_pill.dart` 로 옮겼다**(2026-09-22). 프로필의 「내
   분석/업로드 영상」 알약이 **같은 재질**이어야 해서다 — 값을 양쪽에 적어
   두면 한쪽만 고쳤을 때 말없이 갈린다. */

/// 사진 오른쪽 아래의 **유일한 단추** — 아이콘 + 「영상 분석 시작하기」.
///
/// 🔴 **면이 없다 — 유리와 도는 실버 선뿐이다**(2026-09-22 사용자 요청:
/// 「외곽선만 진짜 얇은 세련된 실버 색상 돌아가게, 안쪽은 그냥 글래스로
/// 블러만 살짝」). 흰색 → 스카이블루로 갔다가 **면 자체를 걷었다.**
///
/// 🔴 **[SilverSweepBorder] 를 프로필의 「내 영상」 판과 나눠 쓴다.** 서로
/// 다른 화면이라 같이 보이는 일이 없다 — 그쪽 머리말의 「한 화면에 하나」가
/// 지켜진다.
///
/// 🔴 **누르면 촉감 + 살짝 커졌다 돌아온다**(사용자 요청). 흔한 「눌리면
/// 작아진다」의 **반대**이니 되돌리지 말 것.
class _StartAnalysisPill extends StatefulWidget {
  const _StartAnalysisPill({required this.onTap});

  final VoidCallback onTap;

  /// 알약의 모서리 — 공용 [kPillRadius] 다. [SilverSweepBorder] 에도 **같은
  /// 값**을 줘야 도는 선이 면의 모서리를 벗어나지 않는다.
  static const double radius = kPillRadius;

  @override
  State<_StartAnalysisPill> createState() => _StartAnalysisPillState();
}

class _StartAnalysisPillState extends State<_StartAnalysisPill>
    with SingleTickerProviderStateMixin {
  late final AnimationController _press = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 110),
    reverseDuration: const Duration(milliseconds: 220),
  );

  @override
  void dispose() {
    _press.dispose();
    super.dispose();
  }

  void _down() {
    /* 🔴 **손끝 촉감은 누르는 순간**에 준다 — 떼는 순간에 주면 **이미 일어난
       일에 대한 알림**이 되어 반 박자 늦게 느껴진다. */
    HapticFeedback.lightImpact();
    _press.forward();
  }

  void _up() => _press.reverse();

  @override
  Widget build(BuildContext context) {
    const r = Radius.circular(_StartAnalysisPill.radius);
    return AnimatedBuilder(
      animation: _press,
      builder: (context, child) => Transform.scale(
        // 커지는 폭은 **아주 작다** — 크면 알약이 튀어나와 장난스러워진다.
        scale: 1 + 0.06 * Curves.easeOut.transform(_press.value),
        child: child,
      ),
      child: DecoratedBox(
        decoration: const BoxDecoration(
          borderRadius: BorderRadius.all(r),
          boxShadow: kSunShadow,
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.all(r),
          /* 🔴 **뒤를 흐린다 — 면을 깔지 않는다.** 사진이 그대로 비치되
             흐려져서 글자가 읽힌다.

             ⚠️ **흐림은 굴러가는 목록 위에서 쓰지 말 것.** 프로필 판이
             그것 때문에 **흰 직선**이 나왔다(`profile_screen.dart` 의
             `_Block`) — 흐림은 가장자리에서 퍼 올 것이 없어 가장자리 값을
             늘려 쓰는데, 뒤가 구르면 그 띠가 매 프레임 달라진다.
             여기 뒤는 **움직이지 않는 사진**이라 괜찮다. */
          child: BackdropFilter(
            filter: ui.ImageFilter.blur(sigmaX: kPillBlur, sigmaY: kPillBlur),
            child: SilverSweepBorder(
              radius: _StartAnalysisPill.radius,
              child: Material(
                // 유리에 아주 옅은 흰 기 — 0 으로 두면 흐림만 남아 밋밋하다.
                color: Colors.white.withValues(alpha: 0.16),
                child: InkWell(
                  key: const Key('home-video-start'),
                  onTap: widget.onTap,
                  onTapDown: (_) => _down(),
                  onTapUp: (_) => _up(),
                  /* 🔴 **취소도 받는다** — 누른 채 손가락을 끌어 벗어나면
                     `onTapUp` 이 안 온다. 안 받으면 알약이 **커진 채로
                     굳는다.** */
                  onTapCancel: _up,
                  child: const Padding(
                    /* 위아래를 살짝 넓혔다(9 → 12, 2026-09-22 사용자 요청).
                       ⚠️ **한 번 더 키웠다**(2026-09-23: 「살짝만 좀 더 크기
                       키우자」) — 안여백 16/12 → **20/15**, 글자 14 → 15,
                       아이콘 18 → 20. 🔴 **넷을 같이 올린다** — 하나만 키우면
                       알약이 길쭉해지거나 글자만 떠 보인다. */
                    padding: EdgeInsets.symmetric(horizontal: 20, vertical: 15),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Symbols.camera_video,
                          size: 20,
                          weight: 500,
                          color: Colors.white,
                        ),
                        SizedBox(width: 8),
                        Text(
                          '영상 분석 시작하기',
                          style: TextStyle(
                            /* 🔴 **흰 글자다.** 면을 걷어 유리가 되면서
                               뒤의 사진이 비친다 — 검은 글자는 사진의 어두운
                               자리(선수 · 신발)에서 묻힌다. */
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 띠의 글 — 아이콘 · 「영상 분석」 · 화살표 한 줄.
class _VideoFlatCopy extends StatelessWidget {
  const _VideoFlatCopy();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 18),
      child: Row(
        children: [
          const Icon(
            Symbols.camera_video,
            size: 24,
            weight: 300,
            color: _kOnDark,
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              '영상 분석',
              maxLines: 1,
              overflow: TextOverflow.fade,
              softWrap: false,
              style: TextStyle(
                color: _kOnDark,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Icon(Icons.chevron_right, color: _kOnDark.withValues(alpha: 0.6)),
        ],
      ),
    );
  }
}

/// 오른쪽 위 「내 프로필」 단추 — 작은 선수 카드 + 글자. 웹 헤더 오른쪽의
/// 짜임(`SiteHeader` 의 카드 + 「내 프로필」)과 같다.
class _ProfileButton extends StatelessWidget {
  const _ProfileButton({required this.card, required this.onTap});

  /// 🔴 **`null` 이면 아직 카드를 안 만든 것**이라 빈 카드를 그린다
  /// (웹도 헤더·프로필 모두 빈 카드로 둔다).
  final PlayerCard? card;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '내 프로필',
      excludeSemantics: true,
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          key: const Key('home-profile'),
          borderRadius: BorderRadius.circular(10),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (card == null)
                  const BlankPlayerCardView(width: _kProfileCardWidth)
                else
                  PlayerCardView(
                    width: _kProfileCardWidth,
                    seed: card!.publicSlug,
                    alias: aliasOf(card!),
                    style: card!.style,
                    photoUrl: card!.photoUrl,
                  ),
                const SizedBox(height: 5),
                const Text(
                  '내 프로필',
                  /* 🔴 **흰색으로 되돌리고 작게 줄였다**(2026-09-22 정정,
                     사용자 요청: 「내 프로필 색상 흰색으로 바꾸고 글자 크기
                     좀 더 줄이자」). 18 → 14.

                     ⚠️ 바로 앞 회차에 **검정으로 바꿨던 것을 되돌린 것**이다.
                     바탕([ScreenTint])이 흰색이 되면서 흰 글자가 사라질까
                     봐 검정으로 돌렸는데, 실기기에서는 이 자리가 **색이 번져
                     든 쪽**이라 흰 글자가 읽힌다고 사용자가 판단했다.

                     🔴 **카드 폭과 배수를 맞추던 규칙은 여기서 끝난다** —
                     이제 글자는 **읽히는 크기**로, 카드는 **보이는 크기**로
                     따로 정한다. */
                  style: TextStyle(color: Colors.white, fontSize: 14),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
