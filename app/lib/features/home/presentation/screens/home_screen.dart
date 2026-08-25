import 'dart:math' show pi;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/sport/current_sport.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/async_view.dart';
import '../../../../core/widgets/bar_menu.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../../core/widgets/refractive_glass.dart';
import '../../../intro/presentation/brand_mark.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../team/data/models/sport.dart';
import '../../../team/data/sport_providers.dart';

/// 홈의 바탕. 인트로의 잉크가 걷힌 자리를 그대로 이어받는다.
const Color _kHomeBg = Color(0xFF000000);

/// 검은 바탕 위의 글자.
const Color _kOnDark = Color(0xFFFFFFFF);

/// 배경 인물이 화면에서 차지하는 높이 비율.
///
/// 인물이 화면 대부분을 쓰고 맨 아래에서만 검정으로 잦아든다. 0.72였는데
/// 아래가 너무 일찍 검어져 인물이 잘려 보였다.
const double _kFigureHeightFactor = 0.88;

/// 인물을 검정으로 잦아들게 하는 막.
///
/// 사진 자체가 아래로 갈수록 어둡지만 딱 떨어지지는 않는다. 이 막이 그
/// 나머지를 지워 사진의 아랫변이 선으로 보이지 않게 한다.
const LinearGradient _kFigureFade = LinearGradient(
  begin: Alignment.topCenter,
  end: Alignment.bottomCenter,
  colors: [Color(0x00000000), Color(0x4D000000), Color(0xFF000000)],
  stops: [0.62, 0.88, 1],
);

/// 유리 세기. 홈의 유리는 늘 서 있다.
const Animation<double> _kGlassOn = AlwaysStoppedAnimation<double>(1);

/// 가장자리가 뒤를 끌어당기는 정도.
const double _kWarp = 7;

/// 카드 모서리.
const double _kCardRadius = 18;

/// 홈에서 갈라져 나가는 곳들.
///
/// **앱의 뼈대를 여기서 한눈에 보여 준다.** 각 카드가 자기 화면으로 가는
/// 입구다. [route]가 null이면 아직 만들지 않은 화면이라 "준비 중"으로 표시하고
/// 눌러도 안내만 띄운다 — 감춰 두면 앱이 무엇을 하는 물건인지 첫 화면에서
/// 읽히지 않는다.
class _Destination {
  const _Destination({
    required this.title,
    required this.summary,
    required this.icon,
    this.route,
  });

  final String title;
  final String summary;
  final IconData icon;
  final String? route;

  bool get isReady => route != null;
}

const List<_Destination> _kDestinations = [
  _Destination(
    title: '영상 분석',
    summary: '경기 영상을 올리면\n실력 리포트가 나옵니다',
    icon: Icons.videocam_outlined,
  ),
  _Destination(
    title: '용병 매칭',
    summary: '경기를 찾고\n지원 현황을 봅니다',
    icon: Icons.sports_soccer_outlined,
  ),
  _Destination(
    title: '내 선수 카드',
    summary: '호칭을 모으고\n카드를 공유합니다',
    icon: Icons.badge_outlined,
  ),
  _Destination(
    title: '내 팀',
    summary: '팀원과 스쿼드를\n관리합니다',
    icon: Icons.groups_outlined,
  ),
  _Destination(
    title: '레슨 · 코치',
    summary: '제휴 코치와\n연결합니다',
    icon: Icons.school_outlined,
  ),
  _Destination(
    title: '내 프로필',
    summary: '닉네임과\n가입 정보',
    icon: Icons.person_outline,
    route: '/profile',
  ),
];

/// 앱의 첫 화면. 여기서 모든 곳으로 갈라진다.
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

  /// 테두리를 도는 빛의 위상. 유리 조각 전부가 이 하나를 나눠 쓴다 —
  /// 조각마다 티커를 두면 여덟 개가 따로 돈다.
  late final AnimationController _sheen = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 7),
  )..repeat();

  bool _menuOpen = false;

  @override
  void dispose() {
    _menu.dispose();
    _sheen.dispose();
    super.dispose();
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
    if (index == 0) return; // 이미 홈이다.
    _notReady();
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

  void _notReady([String? what]) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${what ?? '이 기능'} — 준비 중입니다')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider);
    final nickname = session is SessionLoggedIn ? session.user.nickname : '';

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
            loggedIn: ref.watch(sessionControllerProvider) is SessionLoggedIn,
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
          // 배경 인물. 위쪽에 걸고 아래는 검정으로 잦아들게 한다.
          Align(
            alignment: Alignment.topCenter,
            child: FractionallySizedBox(
              heightFactor: _kFigureHeightFactor,
              // **세로를 채우고 오른쪽을 잘라 낸다.** 사진은 세로가 짧아
              // 화면에 맞추면 좌우가 남는데, 왼쪽에 얼굴이 있으므로 왼쪽을
              // 기준으로 붙이고 오른쪽(뒤통수 바깥)이 잘리게 둔다.
              child: const Image(
                image: AssetImage('assets/images/home_figure.jpg'),
                fit: BoxFit.cover,
                alignment: Alignment.centerLeft,
              ),
            ),
          ),
          Align(
            alignment: Alignment.topCenter,
            child: FractionallySizedBox(
              heightFactor: _kFigureHeightFactor,
              child: const DecoratedBox(
                decoration: BoxDecoration(gradient: _kFigureFade),
                child: SizedBox.expand(),
              ),
            ),
          ),
          _content(context, nickname),
        ],
      ),
    );
  }

  Widget _content(BuildContext context, String nickname) {
    return SafeArea(
        // 종목 목록은 리포지토리에서 온다. 지연·실패·빈 목록이 실제로
        // 발생하므로 네 상태를 AsyncView 한 곳에서 처리한다(스펙 6절).
        child: AsyncView<List<Sport>>(
          value: ref.watch(sportsProvider),
          isEmpty: (sports) => sports.isEmpty,
          emptyMessage: '등록된 종목이 없습니다',
          onRetry: () => ref.invalidate(sportsProvider),
          data: (sports) => ListView(
            // 바가 자리를 차지하지 않고 떠 있으므로 그만큼 띄운다.
            padding: EdgeInsets.fromLTRB(
              20,
              12,
              20,
              FloatingNavBar.heightOf(context) +
                  BarMenu.heightOf(context) +
                  24,
            ),
            children: [
              _brand(),
              const SizedBox(height: 18),
              _sportChips(sports),
              const SizedBox(height: 28),
              Text(
                '무엇을 할까요',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(color: _kOnDark),
              ),
              const SizedBox(height: 12),
              GridView(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate:
                    const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  // 비율 대신 높이를 못박는다 — 한글 두 줄이 들어가는 칸이라
                  // 화면 폭에 따라 비율이 흔들리면 글자가 잘린다.
                  mainAxisExtent: 148,
                ),
                children: [
                  for (var i = 0; i < _kDestinations.length; i++)
                    _DestinationCard(
                      destination: _kDestinations[i],
                      sheen: _sheen,
                      // 조각마다 위상을 어긋내 여덟이 한꺼번에 반짝이지 않게.
                      phase: i * 0.13,
                    ),
                ],
              ),
            ],
          ),
        ),
    );
  }

  /// 화면 위쪽 가운데에 앉는 로고.
  ///
  /// **Hero 표를 달지 않는다.** 로그인에서 날아온 글자가 앉는 자리는 하단 바의
  /// 알약이고, 한 화면에 같은 표가 둘이면 터진다. 이 글자는 그냥 글자다.
  Widget _brand() => const Center(
        child: BrandMark(fontSize: kBrandLandedSize),
      );

  /// 종목 전환.
  ///
  /// 예전에는 로그인 직후 "어떤 종목을 하시나요?" 화면이 따로 떴다. 첫 화면이
  /// 질문 하나로 채워지는 것이 이상해서 없애고 여기 칩으로 옮겼다. 아직 고르지
  /// 않았으면 목록의 첫 종목을 쓴다.
  Widget _sportChips(List<Sport> sports) {
    final selected = ref.watch(currentSportProvider) ?? sports.first.code;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (final sport in sports)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5),
            child: _GlassChip(
              key: Key('home-sport-${sport.code}'),
              label: sport.name,
              selected: sport.code == selected,
              sheen: _sheen,
              phase: sports.indexOf(sport) * 0.17,
              onTap: () =>
                  ref.read(currentSportProvider.notifier).select(sport.code),
            ),
          ),
      ],
    );
  }
}

class _DestinationCard extends StatelessWidget {
  const _DestinationCard({
    required this.destination,
    required this.sheen,
    required this.phase,
  });

  final _Destination destination;
  final Animation<double> sheen;
  final double phase;

  @override
  Widget build(BuildContext context) {
    final dim = destination.isReady ? 1.0 : 0.55;

    return _GlassPanel(
      radius: _kCardRadius,
      sheen: sheen,
      phase: phase,
      child: InkWell(
        onTap: () {
          if (destination.route case final route?) {
            context.push(route);
            return;
          }
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('${destination.title} — 준비 중입니다')),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(destination.icon, size: 26, color: AppTheme.seed),
              const Spacer(),
              Opacity(
                opacity: dim,
                child: Text(
                  destination.title,
                  style: Theme.of(context)
                      .textTheme
                      .titleSmall
                      ?.copyWith(color: _kOnDark),
                ),
              ),
              const SizedBox(height: 4),
              Opacity(
                opacity: dim * 0.8,
                child: Text(
                  destination.summary,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: _kOnDark),
                ),
              ),
              if (!destination.isReady) ...[
                const SizedBox(height: 6),
                Text(
                  '준비 중',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: _kOnDark.withValues(alpha: 0.5),
                      ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// 뒤를 굴절시키는 유리 한 조각.
///
/// 로그인 시트의 버튼과 달리 여기는 **진짜 유리를 쓸 수 있다** — 홈의 카드는
/// 다른 유리 안에 들어 있지 않다. 유리 안의 유리가 금지인 이유는
/// `refractive_glass.dart` 주석 참고.
class _GlassPanel extends StatelessWidget {
  const _GlassPanel({
    required this.radius,
    required this.child,
    required this.sheen,
    this.phase = 0,
  });

  final double radius;
  final Widget child;

  /// 테두리를 도는 빛의 위상(0~1을 반복).
  final Animation<double> sheen;

  /// 이 조각만큼 늦게 돈다. 전부 같은 위상이면 한꺼번에 반짝여 기계처럼 보인다.
  final double phase;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      // 테두리는 유리 **위에** 그린다 — 밑에 두면 굴절에 먹혀 흐려진다.
      foregroundPainter: _TravelingEdge(
        repaint: sheen,
        progress: sheen,
        phase: phase,
        radius: radius,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: LayoutBuilder(
          builder: (context, box) => RefractiveGlass(
            notch: GlassNotch(
              left: 0,
              right: box.maxWidth,
              depth: box.maxHeight,
              radius: radius,
              pill: true,
            ),
            strength: _kGlassOn,
            warp: _kWarp,
            child: child,
          ),
        ),
      ),
    );
  }
}

/// 둘레를 도는 얇은 흰 빛.
///
/// 늘 켜져 있는 아주 옅은 선 위에, 한 점만 밝은 띠가 원을 그리며 돈다.
/// 스윕 그라데이션을 회전시켜 만든다 — 점을 좌표로 움직이면 모서리에서
/// 속도가 튀는데, 각도로 돌리면 둘레를 고르게 지난다.
class _TravelingEdge extends CustomPainter {
  const _TravelingEdge({
    required super.repaint,
    required this.progress,
    required this.phase,
    required this.radius,
  });

  final Animation<double> progress;
  final double phase;
  final double radius;

  /// **아주 얇다.** 굵으면 테두리가 눈에 먼저 들어와 유리가 아니라 상자로
  /// 읽힌다.
  static const double _width = 1.0;

  @override
  void paint(Canvas canvas, Size size) {
    final rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      Radius.circular(radius),
    ).deflate(_width / 2);

    // 늘 있는 선. 빛이 지나가지 않는 동안에도 모양이 서 있어야 한다.
    canvas.drawRRect(
      rrect,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = _width
        ..color = Colors.white.withValues(alpha: 0.10),
    );

    final t = (progress.value + phase) % 1.0;
    final shader = SweepGradient(
      colors: const [
        Color(0x00FFFFFF),
        Color(0x00FFFFFF),
        Color(0xE6FFFFFF),
        Color(0x00FFFFFF),
        Color(0x00FFFFFF),
      ],
      // 밝은 구간이 좁아야 "한 점이 지나간다"로 읽힌다.
      stops: const [0, 0.42, 0.5, 0.58, 1],
      transform: GradientRotation(t * 2 * pi),
    ).createShader(Offset.zero & size);

    canvas.drawRRect(
      rrect,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = _width
        ..shader = shader,
    );
  }

  @override
  bool shouldRepaint(_TravelingEdge old) =>
      old.phase != phase || old.radius != radius;
}

/// 종목을 고르는 유리 알약.
class _GlassChip extends StatelessWidget {
  const _GlassChip({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
    required this.sheen,
    required this.phase,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Animation<double> sheen;
  final double phase;

  @override
  Widget build(BuildContext context) {
    return _GlassPanel(
      radius: 22,
      sheen: sheen,
      phase: phase,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 10),
          child: Text(
            label,
            style: TextStyle(
              // 고른 것만 브랜드색으로 선다 — 유리 면은 둘이 같다.
              color: selected ? AppTheme.seed : _kOnDark,
              fontSize: 14,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}
