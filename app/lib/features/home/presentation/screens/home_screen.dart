import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/sport/current_sport.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/async_view.dart';
import '../../../../core/widgets/bar_menu.dart';
import '../../../../core/widgets/figure_background.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../../core/widgets/glass_panel.dart';
import '../../../intro/presentation/brand_mark.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../team/data/models/sport.dart';
import '../../../team/data/sport_providers.dart';

/// 홈의 바탕. 인트로의 잉크가 걷힌 자리를 그대로 이어받는다.
const Color _kHomeBg = Color(0xFF000000);

/// 검은 바탕 위의 글자.
const Color _kOnDark = Color(0xFFFFFFFF);

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
    route: '/videos',
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
          // 홈에서만 인물이 아주 느리게 숨쉰다.
          const FigureBackground(breathe: true),
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
              // 지금 로그인한 사람의 이름.
              Center(
                child: Text(
                  nickname,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(color: _kOnDark),
                ),
              ),
              // 카드 줄을 조금 더 내려 이름과 붙어 보이지 않게 한다.
              const SizedBox(height: 32),
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

    return GlassPanel(
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


/// 종목을 고르는 유리 알약.
class _GlassChip extends StatelessWidget {
  const _GlassChip({
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
    return GlassPanel(
      // 칩에는 도는 빛을 두지 않는다 — 작은 알약에서는 선이 쉴 새 없이
      // 돌아 시선을 끈다.
      radius: 22,
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
