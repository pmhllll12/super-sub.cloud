import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/sport/current_sport.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/async_view.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../team/data/models/sport.dart';
import '../../../team/data/sport_providers.dart';

/// 홈의 바탕. 인트로의 잉크가 걷힌 자리를 그대로 이어받는다.
const Color _kHomeBg = Color(0xFF000000);

/// 검은 바탕 위의 글자.
const Color _kOnDark = Color(0xFFFFFFFF);

/// 카드 면. 검정 위에 아주 옅은 흰 기 한 겹 — 로그인 버튼과 같은 방식이다.
final Color _kCardFill = Colors.white.withValues(alpha: 0.06);

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
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);
    final nickname = session is SessionLoggedIn ? session.user.nickname : '';

    return Scaffold(
      backgroundColor: _kHomeBg,
      // 바는 SafeArea 밖에 떠 있다 — 안에 넣으면 홈 인디케이터 위에서 잘린다.
      bottomNavigationBar: FloatingNavBar(
        currentIndex: 0,
        onTap: (index) => ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('준비 중입니다')),
        ),
      ),
      extendBody: true,
      body: SafeArea(
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
              FloatingNavBar.heightOf(context) + 24,
            ),
            children: [
              _header(context, ref, nickname),
              const SizedBox(height: 18),
              _sportChips(ref, sports),
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
                  for (final d in _kDestinations)
                    _DestinationCard(destination: d),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _header(BuildContext context, WidgetRef ref, String nickname) {
    return Row(
      children: [
        Expanded(
          child: Text(
            '$nickname 님,\n오늘도 뛰어볼까요',
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(color: _kOnDark),
          ),
        ),
        IconButton(
          key: const Key('home-logout'),
          color: _kOnDark,
          icon: const Icon(Icons.logout),
          tooltip: '로그아웃',
          onPressed: () =>
              ref.read(sessionControllerProvider.notifier).logout(),
        ),
      ],
    );
  }

  /// 종목 전환.
  ///
  /// 예전에는 로그인 직후 "어떤 종목을 하시나요?" 화면이 따로 떴다. 첫 화면이
  /// 질문 하나로 채워지는 것이 이상해서 없애고 여기 칩으로 옮겼다. 아직 고르지
  /// 않았으면 목록의 첫 종목을 쓴다.
  Widget _sportChips(WidgetRef ref, List<Sport> sports) {
    final selected = ref.watch(currentSportProvider) ?? sports.first.code;
    return Wrap(
      spacing: 8,
      children: [
        for (final sport in sports)
          ChoiceChip(
            key: Key('home-sport-${sport.code}'),
            label: Text(sport.name),
            selected: sport.code == selected,
            showCheckmark: false,
            backgroundColor: Colors.transparent,
            selectedColor: AppTheme.seed,
            labelStyle: TextStyle(
              color: sport.code == selected ? _kHomeBg : _kOnDark,
            ),
            side: BorderSide(color: _kOnDark.withValues(alpha: 0.25)),
            onSelected: (_) =>
                ref.read(currentSportProvider.notifier).select(sport.code),
          ),
      ],
    );
  }
}

class _DestinationCard extends StatelessWidget {
  const _DestinationCard({required this.destination});

  final _Destination destination;

  @override
  Widget build(BuildContext context) {
    final dim = destination.isReady ? 1.0 : 0.55;

    return Card(
      color: _kCardFill,
      elevation: 0,
      clipBehavior: Clip.antiAlias,
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
