import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:video_player/video_player.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/bar_menu.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../../core/widgets/glass_panel.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../../core/network/api_client.dart';
import '../../../card/data/card_providers.dart';
import '../../../card/presentation/mate_cards_controller.dart';
import '../../../profile/presentation/widgets/player_card_view.dart';
import '../../../team/auto_seat.dart';
import '../../../team/data/models/squad.dart';
import '../../../team/data/squad_providers.dart';
import '../../../team/seats_from_squad.dart';
import '../../../team/presentation/widgets/squad_board.dart';

/// 홈의 바탕 — **완전한 검정**(2026-09-16 사용자 요청. 하루 동안 흰색이었다).
/// 사진은 안 깐다(`assets/images/home_silhouette.jpg` 는 지금 안 쓴다).
///
/// 🔴 판(`_kSheetColor`)·하단 바(`kNavBarColor`)는 이 바탕보다 **한 단 밝은**
/// 진회색이다 — 바탕과 판을 밝기로만 가른다. 둘을 같은 검정으로 되돌리면
/// 판의 경계가 사라진다.
const Color _kHomeBg = Color(0xFF000000);

/// 검은 바탕 위의 글자.
const Color _kOnDark = Color(0xFFFFFFFF);

/// 유리 조각 모서리.
const double _kCardRadius = 18;

/// 오른쪽 위 「내 프로필」 단추의 카드 폭. 웹 헤더의 작은 카드(`.ss-pcard-mini`)
/// 자리다 — 글자는 안 읽혀도 초록 카드와 인물로 「내 카드」임을 알아본다.
const double _kProfileCardWidth = 48;

/// 위에서 내려오는 스쿼드 판 — 접혔을 때 판이 화면 높이의 몇 할까지 오는가.
const double _kSheetCollapsedFactor = 0.5;

/// 접힌 스쿼드 판을 「들어가는 최대 크기」보다 더 줄이는 비율.
const double _kCollapsedBoardShrink = 0.82;

/// 판 아래 손잡이 줄의 높이. 판을 끌어내리는 자리라는 표식이다.
const double _kSheetHandleH = 28;

/// 스쿼드 판 · 영상 분석 판의 면 색 — **진회색**(2026-09-16 사용자 지정).
/// 검은 바탕(`_kHomeBg`)보다 한 단 밝아서 판이 층으로 읽힌다.
/// 하단 바 · 로고 알약(`kNavBarColor`)과 **같은 값이어야 한다** — 넷이 한 켜다.
const Color _kSheetColor = Color(0xFF1C1C1E);

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

  /// 손가락을 따라 판이 내려오고 올라간다. [travel] 은 접힘 ↔ 펼침 사이 거리.
  /// 끝을 넘어 더 끌면 **고무줄처럼 뻑뻑해진다**(끄는 만큼의 3할만 따라온다).
  void _dragSheet(DragUpdateDetails d, double travel) {
    if (travel <= 0) return;
    _sheet.stop();
    var delta = d.primaryDelta! / travel;
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
  void _releaseSheet(DragEndDetails d, double travel) {
    final pxPerSec = d.primaryVelocity ?? 0;
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
        await ref.read(squadRepositoryProvider).enlist(
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

  /// 카드를 다른 칸으로 옮긴다 — 서버에 남겨야 새로고침해도 그 자리다.
  Future<void> _moveSeat(
    String teamId,
    String memberId,
    String positionCode,
    int col,
    int row,
  ) async {
    try {
      await ref.read(squadRepositoryProvider).moveSeat(
            teamId,
            memberId: memberId,
            positionCode: positionCode,
            gridCol: col,
            gridRow: row,
          );
      ref.invalidate(squadProvider(teamId));
    } on ApiException catch (e) {
      /* 🔴 **실패하면 알린다.** 자동 착석과 다르다 — 이건 사람이 **시킨 일**이라,
         조용히 넘어가면 「옮겼는데 안 옮겨졌다」가 된다. 판은 서버 값으로 다시
         그려지므로 카드는 저절로 제자리로 돌아간다. */
      if (!mounted) return;
      _notReady(e.message);
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
    return PlayerCardView(width: width, seed: card.publicSlug);
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
    final card = ref.watch(myCardProvider).value;
    final cardSeed = card?.publicSlug;
    // 주장인 팀이 우선, 없으면 속한 첫 팀. 팀이 없으면 판을 안 부른다.
    final teamId = user?.primaryTeamId;
    final squad = teamId == null
        ? null
        : ref.watch(squadProvider(teamId)).value;
    _wantMateCards(squad, cardSeed);
    _autoSeatOnce(squad, card?.id, cardSeed, user?.ownedTeamId);

    return Scaffold(
      backgroundColor: _kHomeBg,
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
          _videoPanel(context),
          _squadSheet(context, cardSeed, squad, user?.ownedTeamId),
        ],
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

  /// 「영상 분석」 — 접혔을 때는 스쿼드 판 **바로 아래부터 하단 바 위까지** 채우는
  /// 네모 판이고 안에서 소개 영상이 되풀이된다. 스쿼드 판을 펼치면 그만큼 밀려
  /// 내려가 **하단 바 바로 위의 납작한 띠**가 되고, 영상은 걷히고 글자만 남는다
  /// (2026-09-15 사용자 요청). 둘 사이는 판을 끄는 손가락을 그대로 따라간다.
  Widget _videoPanel(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final bottomInset = _videoBottomInset(context);
    final geo = _sheetGeometry(context);
    final openTop = geo.collapsedBottom + _kVideoGap;
    final flatTop = size.height - bottomInset - _kVideoFlatH;
    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        final t = _sheetT;
        // 🔴 스쿼드 판처럼 **양쪽 끝까지** 편다(2026-09-15 사용자 요청).
        return Positioned(
          left: 0,
          right: 0,
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
  ({
    double rowTop,
    double openBoardTop,
    double closedBoardTop,
    double boardW,
    double boardH,
    double minScale,
    double collapsedBottom,
    double expandedBottom,
  })
  _sheetGeometry(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final safeTop = MediaQuery.paddingOf(context).top;
    // 펼쳤을 때 판은 납작해진 「영상 분석」 띠 바로 위까지 온다.
    final bottomReserve =
        _videoBottomInset(context) + _kVideoFlatH + _kVideoGap;

    final rowTop = safeTop + 8;
    // 펼쳤을 때 판은 알약 줄 **바로 아래**에 선다. 🔴 예전에는 「내 프로필」
    // 높이(92)만큼 줄을 잡아 알약과 판 사이가 너무 벌어졌다(2026-09-15 사용자
    // 지적) — 펼치면 그 단추는 빠져나가므로 알약 높이만 잡는다.
    final openBoardTop = rowTop + _kPillsRowH + 12;
    // 접혔을 때는 알약이 숨어 그 줄이 비므로 판을 끌어올려 **「내 프로필」 카드
    // 윗변에 맞춘다**(2026-09-15 사용자 요청). 4 는 단추 안쪽 여백이다.
    final closedBoardTop = rowTop + 4;
    final expandedBottom = size.height - bottomReserve;
    final boardW = size.width - 32;
    final boardH = (expandedBottom - _kSheetHandleH - openBoardTop).clamp(
      0.0,
      double.infinity,
    );

    // 접혔을 때의 축소 — 화면 절반쯤에 판이 끝나는 크기. 🔴 다만 **「내 프로필」과
    // 옆으로 겹치지 않는 크기**를 넘지 않는다. 판은 가운데 기준으로 줄어서, 크면
    // 오른쪽 변이 단추 밑으로 파고든다.
    final byHalf = boardH <= 0
        ? 1.0
        : (size.height * _kSheetCollapsedFactor -
                  _kSheetHandleH -
                  openBoardTop) /
              boardH;
    const profileW = _kProfileCardWidth + 8;
    final profileLeft = size.width - 16 - profileW;
    final byProfile = (2 * (profileLeft - 8 - 16) - boardW) / boardW;
    // 거기에 **한 번 더 줄인다**(×0.82, 2026-09-15 사용자 요청) — 접힌 판은 「무엇이
    // 있는지」만 보이면 되고, 펼쳤을 때 커지는 차이가 클수록 끌어내리는 맛이 난다.
    final minScale =
        ([byHalf, byProfile, 1.0].reduce((a, b) => a < b ? a : b) *
                _kCollapsedBoardShrink)
            .clamp(0.2, 1.0);

    // 접힌 판 면은 줄어든 스쿼드 판 · 안내 한 줄 · 손잡이만큼만 — 판을 올린 만큼
    // 같이 짧아진다.
    final collapsedBottom =
        (closedBoardTop + boardH * minScale + _kSheetHintH + _kSheetHandleH)
            .clamp(0.0, expandedBottom);
    return (
      rowTop: rowTop,
      openBoardTop: openBoardTop,
      closedBoardTop: closedBoardTop,
      boardW: boardW,
      boardH: boardH,
      minScale: minScale,
      collapsedBottom: collapsedBottom,
      expandedBottom: expandedBottom,
    );
  }

  Widget _squadSheet(
    BuildContext context,
    String? cardSeed,
    Squad? squad,
    String? ownedTeamId,
  ) {
    final geo = _sheetGeometry(context);
    final rowTop = geo.rowTop;
    final openBoardTop = geo.openBoardTop;
    final closedBoardTop = geo.closedBoardTop;
    final boardW = geo.boardW;
    final boardH = geo.boardH;
    final minScale = geo.minScale;
    final collapsedBottom = geo.collapsedBottom;
    final expandedBottom = geo.expandedBottom;
    const profileW = _kProfileCardWidth + 8;
    final travel = expandedBottom - collapsedBottom;

    final board = _role == _Role.captain
        ? SquadBoard(
            cardSeed: cardSeed,
            squad: squad,
            mySlug: cardSeed,
            mateCardBuilder: _mateCard,
            /* 🔴 **주장이 아니면 `null` 이다 — 아예 못 집는다.** 옮겨도 403 이라
               끌린 뒤 되돌아가는 것보다 못 집게 하는 편이 낫다. 판이 그 팀의
               것이 아닐 때도 마찬가지다. */
            onSeatMoved: (ownedTeamId != null && squad?.teamId == ownedTeamId)
                ? (memberId, positionCode, col, row) =>
                    _moveSeat(ownedTeamId, memberId, positionCode, col, row)
                : null,
            onSeatTap: (_) => _notReady('선수 넣기'),
          )
        : const _MemberPlaceholder();

    return AnimatedBuilder(
      animation: _sheet,
      builder: (context, _) {
        // 판 면의 아래 끝은 **넘친 값 그대로** 따라간다 — 스프링이 살짝 더 늘었다
        // 돌아오는 것이 이 움직임의 맛이다. 판의 크기 · 자리는 조금만 넘치게 묶는다.
        final raw = _sheet.value;
        final t = raw.clamp(-0.04, 1.04);
        final tc = _sheetT;
        final bottom =
            collapsedBottom + (expandedBottom - collapsedBottom) * raw;
        final scale = minScale + (1 - minScale) * t;
        final boardTop = closedBoardTop + (openBoardTop - closedBoardTop) * tc;
        // 펼칠수록 모서리가 조금 더 둥글고, 손잡이는 좁아진다.
        final radius = _kSheetRadius + 8 * tc;
        // 안내 글과 「내 프로필」은 펼치기 **시작하자마자** 걷힌다(앞 4할 안에).
        final fadeOut = (1 - tc / 0.4).clamp(0.0, 1.0);
        return Positioned(
          top: 0,
          left: 0,
          right: 0,
          height: bottom,
          child: GestureDetector(
            key: const Key('home-squad-sheet'),
            behavior: HitTestBehavior.opaque,
            onVerticalDragUpdate: (d) => _dragSheet(d, travel),
            onVerticalDragEnd: (d) => _releaseSheet(d, travel),
            child: Stack(
              clipBehavior: Clip.hardEdge,
              children: [
                // 판 면.
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      // 🔴 **반투명으로 되돌리지 않는다**(2026-09-15 사용자 요청).
                      // 흰 바탕 위에서 비치면 판이 뿌옇게 뜬다. 색은 `_kSheetColor`.
                      color: _kSheetColor,
                      borderRadius: BorderRadius.vertical(
                        bottom: Radius.circular(radius),
                      ),
                      border: Border(
                        bottom: BorderSide(
                          color: _kOnDark.withValues(alpha: 0.14),
                        ),
                      ),
                      // 판 아래로 옅은 그림자 — 판이 홈 위에 떠 있는 층으로 읽힌다.
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.45 * tc),
                          blurRadius: 30,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                  ),
                ),
                // 스쿼드 판 — 제 크기로 짜서 위 가운데 기준으로 줄인다.
                // 🔴 **다 펼치기 전에는 판이 안 눌린다**(2026-09-15 사용자 요청). 작게
                // 줄어 있을 때 빈 자리(+)가 눌리면 판을 끌어내리려던 손가락이 엉뚱한
                // 안내를 띄운다. 판을 끄는 손짓은 바깥 GestureDetector 가 받으므로
                // 그대로 된다.
                Positioned(
                  top: boardTop,
                  left: 16,
                  width: boardW,
                  height: boardH,
                  child: IgnorePointer(
                    key: const Key('home-squad-board-lock'),
                    ignoring: tc < 0.98,
                    child: Transform.scale(
                      scale: scale,
                      alignment: Alignment.topCenter,
                      child: board,
                    ),
                  ),
                ),
                // 접혔을 때 판 바로 아래 안내. 펼치기 시작하면 걷히고, 다 올리면 돌아온다.
                Positioned(
                  top: boardTop + boardH * scale,
                  left: 0,
                  right: 0,
                  height: _kSheetHintH,
                  child: IgnorePointer(
                    child: Opacity(
                      opacity: fadeOut,
                      child: Transform.translate(
                        offset: Offset(0, 8 * (1 - fadeOut)),
                        child: const _PullHint(label: '아래로 내려 내 팀 만들기'),
                      ),
                    ),
                  ),
                ),
                // 팀장 · 팀원 · AI — 판이 다 나온 뒤 차례로 떠오른다([_pills]).
                // 덜 떠올랐으면 안 눌린다(보이지 않는 단추가 눌리는 것을 막는다).
                Positioned(
                  top: rowTop,
                  left: 16,
                  right: 16,
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
                // 「내 프로필」 — 접혀 있을 때만 선다. 펼치면 **오른쪽으로 미끄러져
                // 나가고**(그 자리를 AI 가 쓴다), 다 올리면 돌아온다.
                Positioned(
                  top: rowTop,
                  right: 16,
                  child: IgnorePointer(
                    ignoring: fadeOut < 0.5,
                    child: Opacity(
                      opacity: fadeOut,
                      child: Transform.translate(
                        offset: Offset((profileW + 24) * (1 - fadeOut), 0),
                        child: _ProfileButton(
                          seed: cardSeed,
                          onTap: _openProfile,
                        ),
                      ),
                    ),
                  ),
                ),
                // 손잡이 — 끌어내리는 자리라는 표식. 눌러도 여닫힌다.
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  height: _kSheetHandleH,
                  child: GestureDetector(
                    key: const Key('home-squad-handle'),
                    behavior: HitTestBehavior.opaque,
                    onTap: _toggleSheet,
                    child: Center(
                      child: Container(
                        width: 40 - 12 * tc,
                        height: 4,
                        decoration: BoxDecoration(
                          color: _kOnDark.withValues(alpha: 0.45 - 0.15 * tc),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
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

/// 「내리면 무엇이 나오는지」 미리 말하는 한 줄 — 웹 홈 · 상점의 안내
/// (`.ss-market-scroll`)와 같은 모양이다. 흰 글자 왼쪽에 **초록 이중 화살표**가
/// 붙고, 화살표만 위아래로 흔들리며 옅어졌다 진해진다(1.5초, -5 ↔ +7, 45% ↔ 100%
/// — 웹 `ss-market-scroll-nudge` 값 그대로).
///
/// 글자가 가운데에 오도록 오른쪽에 화살표만큼 빈자리를 둔다(웹과 같은 장치).
/// 기기에서 움직임 줄이기를 켰으면 흔들지 않는다.
class _PullHint extends StatefulWidget {
  const _PullHint({required this.label});

  final String label;

  @override
  State<_PullHint> createState() => _PullHintState();
}

class _PullHintState extends State<_PullHint>
    with SingleTickerProviderStateMixin {
  // 웹(30)보다 조금 작다 — 폰 폭에서 글자에 비해 화살표가 커 보였다(사용자 요청).
  static const double _iconSize = 26;
  static const double _gap = 4;

  late final AnimationController _nudge = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 750),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.disableAnimationsOf(context)) {
      _nudge
        ..stop()
        ..value = 1;
    } else if (!_nudge.isAnimating) {
      _nudge.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _nudge.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final eased = CurvedAnimation(parent: _nudge, curve: Curves.easeInOut);
    return Center(
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedBuilder(
            animation: eased,
            builder: (context, child) => Opacity(
              opacity: 0.45 + 0.55 * eased.value,
              child: Transform.translate(
                offset: Offset(0, -5 + 12 * eased.value),
                child: child,
              ),
            ),
            child: const Icon(
              Symbols.keyboard_double_arrow_down,
              size: _iconSize,
              weight: 300,
              color: AppTheme.seed,
            ),
          ),
          const SizedBox(width: _gap),
          Text(
            widget.label,
            style: const TextStyle(
              color: _kOnDark,
              fontSize: 14,
              letterSpacing: 0.2,
            ),
          ),
          const SizedBox(width: _iconSize + _gap),
        ],
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
      child: SizedBox(
        height: 38,
        child: GlassPanel(
          radius: 19,
          child: Material(
            type: MaterialType.transparency,
            child: InkWell(
              onTap: onTap,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(19),
                  border: selected
                      ? Border.all(color: _kOnDark, width: 1.5)
                      : null,
                ),
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

/// 「영상 분석」 판. [flat] 이 0 이면 소개 영상이 도는 큰 판, 1 이면 하단 바 위의
/// 납작한 띠다(스쿼드 판을 펼친 정도 그대로).
///
/// - 큰 판: 영상이 판을 채우며 **소리 없이 끝없이 되풀이**되고, 그 위에 웹과 같은
///   아이콘(`camera_video`) · 「영상 분석」 · 긴 설명이 가운데 선다.
/// - 띠: 영상 · 설명은 걷히고 아이콘 · 「영상 분석」 · 화살표만 한 줄로 남는다.
/// - 사이: 앞 절반 동안 큰 판의 글이 걷히고, 뒤 절반 동안 띠의 글이 들어온다 —
///   둘이 동시에 보이면 글이 겹쳐 지저분하다.
///
/// 🔴 띠가 되면 **영상을 멈춘다** — 안 보이는 영상이 계속 돌면 배터리만 먹는다.
/// ⚠️ 위젯 시험(`flutter test`)에서는 영상을 만들지 않는다 — 시험 환경에는 영상
/// 재생기가 없어 초기화가 실패한다.
class _VideoAnalysisPanel extends StatefulWidget {
  const _VideoAnalysisPanel({required this.flat, required this.onTap});

  final double flat;
  final VoidCallback onTap;

  @override
  State<_VideoAnalysisPanel> createState() => _VideoAnalysisPanelState();
}

class _VideoAnalysisPanelState extends State<_VideoAnalysisPanel> {
  static const String _asset = 'assets/videos/analysis_showcase.mp4';

  VideoPlayerController? _video;
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    if (Platform.environment.containsKey('FLUTTER_TEST')) return;
    final video = VideoPlayerController.asset(
      _asset,
      videoPlayerOptions: VideoPlayerOptions(mixWithOthers: true),
    );
    _video = video;
    video
        .initialize()
        .then((_) {
          if (!mounted) return;
          video
            ..setLooping(true)
            ..setVolume(0);
          setState(() => _ready = true);
          _syncPlayback();
        })
        .catchError((Object _) {
          // 영상을 못 열어도 판은 글자와 어두운 면으로 그대로 선다.
        });
  }

  @override
  void didUpdateWidget(_VideoAnalysisPanel old) {
    super.didUpdateWidget(old);
    _syncPlayback();
  }

  void _syncPlayback() {
    final video = _video;
    if (video == null || !_ready) return;
    final hidden = widget.flat >= 0.99;
    if (hidden && video.value.isPlaying) {
      video.pause();
    } else if (!hidden && !video.value.isPlaying) {
      video.play();
    }
  }

  @override
  void dispose() {
    _video?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.flat;
    final bigText = (1 - t * 2).clamp(0.0, 1.0);
    final flatText = ((t - 0.5) * 2).clamp(0.0, 1.0);
    final videoOpacity = (1 - t * 1.4).clamp(0.0, 1.0);
    final radius = 28 - 10 * t;
    final video = _video;

    // 🔴 **가운데로 나눈다**(2026-09-15 사용자 요청) — 위 절반은 아이콘 · 글,
    // 아래 절반에만 영상. 영상 위에 글을 얹으면 움직이는 화면 위라 글이 흔들려
    // 읽혔다. 판이 납작해지는 동안 영상 칸은 아래 절반 그대로 같이 줄어든다.
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: Material(
        color: _kSheetColor,
        child: InkWell(
          key: const Key('home-video-analysis'),
          onTap: widget.onTap,
          child: Stack(
            fit: StackFit.expand,
            children: [
              Column(
                children: [
                  // 위 절반 — 아이콘 · 「영상 분석」 · 설명. 걷힐 때 살짝 위로 뜬다.
                  Expanded(
                    child: IgnorePointer(
                      child: Opacity(
                        opacity: bigText,
                        child: Transform.translate(
                          offset: Offset(0, -12 * (1 - bigText)),
                          child: const _VideoPanelCopy(),
                        ),
                      ),
                    ),
                  ),
                  // 아래 절반 — 영상만. 판 폭을 채우고 넘치는 위아래는 자른다.
                  Expanded(
                    child: Opacity(
                      opacity: videoOpacity,
                      child: video != null && _ready
                          // 🔴 판 **끝까지** 채운다(사용자 요청 — 잘려도 된다). `cover`
                          // 에 3% 더 키워, 기기 디코더가 가장자리를 한 줄씩 비우는
                          // 경우에도 판 끝에 검은 틈이 안 남게 한다.
                          ? ClipRect(
                              child: Transform.scale(
                                scale: 1.03,
                                child: SizedBox.expand(
                                  child: FittedBox(
                                    fit: BoxFit.cover,
                                    child: SizedBox(
                                      width: video.value.size.width,
                                      height: video.value.size.height,
                                      child: VideoPlayer(video),
                                    ),
                                  ),
                                ),
                              ),
                            )
                          : const SizedBox.expand(),
                    ),
                  ),
                ],
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
    );
  }
}

/// 큰 판의 글. 웹 목적지 카드(`www/src/lib/destinations.ts`)와 같은 아이콘이고,
/// 설명은 앱에 맞춰 길게 풀었다.
///
/// 🔴 「AI 가 판정한다」고 쓰지 않는다 — 등급은 정해진 기준표로 결정론적 코드가
/// 매기고, 모델은 자세를 재고 근거 문장을 쓴다(`agent/CLAUDE.md` 「무엇이 무엇을
/// 정하는가」). 설명이 그 경계를 흐리면 제안서 · 발표와도 어긋난다.
class _VideoPanelCopy extends StatelessWidget {
  const _VideoPanelCopy();

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        // 판이 좁아지는 도중(높이가 모자랄 때)에는 설명부터, 더 좁으면 아이콘도
        // 뺀다 — 넘치면 줄이 깨진다. 위 절반만 쓰므로 판 전체의 절반 높이다.
        final roomy = box.maxHeight >= 150;
        final showIcon = box.maxHeight >= 70;
        // 줄어드는 도중 몇 픽셀 모자라는 순간이 있다 — 넘치게 두지 않고 그만큼만
        // 통째로 줄인다(`scaleDown` 은 자리가 넉넉하면 제 크기 그대로다).
        return Center(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: SizedBox(
              width: box.maxWidth,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 22),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (showIcon) ...[
                      const Icon(
                        Symbols.camera_video,
                        size: 36,
                        weight: 250,
                        color: _kOnDark,
                      ),
                      const SizedBox(height: 8),
                    ],
                    const Text(
                      '영상 분석',
                      style: TextStyle(
                        color: _kOnDark,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (roomy) ...[
                      const SizedBox(height: 8),
                      Text(
                        '경기 영상을 올리면 영상 속 내 움직임을 따라가며 자세를 재고,\n'
                        '정해진 기준으로 실력을 판정해 근거와 함께 리포트로 보여 드려요.',
                        textAlign: TextAlign.center,
                        maxLines: 4,
                        overflow: TextOverflow.fade,
                        style: TextStyle(
                          color: _kOnDark.withValues(alpha: 0.88),
                          fontSize: 13.5,
                          height: 1.45,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        );
      },
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
  const _ProfileButton({required this.seed, required this.onTap});

  /// 카드의 공개 슬러그. 🔴 **`null` 이면 아직 카드를 안 만든 것**이라 빈
  /// 카드를 그린다(웹도 헤더·프로필 모두 빈 카드로 둔다).
  final String? seed;
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
                if (seed == null)
                  const BlankPlayerCardView(width: _kProfileCardWidth)
                else
                  PlayerCardView(width: _kProfileCardWidth, seed: seed!),
                const SizedBox(height: 4),
                const Text(
                  '내 프로필',
                  style: TextStyle(color: _kOnDark, fontSize: 11),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
