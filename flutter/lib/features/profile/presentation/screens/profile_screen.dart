import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../auth/data/models/app_user.dart';
import '../../../auth/data/models/team_membership.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../card/data/card_providers.dart';
import '../../../card/data/models/player_card.dart';
import '../../../../core/widgets/aurora_background.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../../core/widgets/glass_surface.dart';
import '../../../card/presentation/card_editor_screen.dart';
import '../../../video/presentation/my_videos_controller.dart';
import '../../../video/presentation/screens/my_videos_screen.dart';
import '../widgets/player_card_view.dart';
import '../../../team/data/team_providers.dart';
import 'delete_account_sheet.dart';
import 'nickname_sheet.dart';
import 'team_sheet.dart';
import 'titles_sheet.dart';

/// 내 프로필 — 웹 `/me`(`app/(app)/me/page.tsx`)를 폰 세로에 맞춰 옮긴 것이다.
///
/// 웹은 좌우 두 단(왼쪽 정보 · 오른쪽 영상)인데 **폰에는 옆으로 펼 자리가
/// 없어** 한 줄로 쌓는다(`www/docs/2026-08-31-앱-이식-지침.md` §2-2).
///
/// 웹의 **오른쪽 칸(영상)은 요약 블록 하나**로만 두고 본체는 밀고 들어가는
/// 전용 화면이다(`MyVideosScreen`) — 플레이어·스트립·리포트를 이 목록 안에
/// 다 쌓으면 프로필이 통째로 굴러야 하는 길이가 된다.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);
    if (session is! SessionLoggedIn) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final user = session.user;
    final card = ref.watch(myCardProvider).value;

    /* 🔴 **배경이 내 카드의 색을 따른다**(2026-09-22, 사용자 요청). 홈의
       빛무리와 같은 그림인데 색만 **카드 바탕색 + 자국색** 둘로 갈아 끼운다.
       카드가 없으면 브랜드 민트 그대로다 — 「빈 카드」인데 배경만 요란하면
       무엇을 보는 화면인지 흐려진다.

       🔴 **카드 색을 고치고 돌아오면 부드럽게 건너간다** — 툭 갈리면 화면이
       깜빡인 것처럼 보인다(`AnimatedAuroraBackground`). */
    final tint = card?.style == null
        ? kDefaultAuroraTint
        : (a: card!.style!.bg, b: card.style!.brushColor);

    return AnimatedAuroraBackground(
      tint: tint,
      base: _kBg,
      child: Scaffold(
        // 🔴 **배경을 비운다** — 안 비우면 빛무리를 덮는다.
        backgroundColor: Colors.transparent,
        /* 🔴 **머리칸을 아예 안 둔다**(2026-09-22, 사용자 요청). 제목
           (「MY PROFILE」)도 뒤로가기도 걷었다 — 카드가 이 화면의 첫 얼굴이고,
           그 위에 띠가 하나 더 있으면 카드가 밀려 내려간다.
           🔴 **돌아가는 길은 아래 바가 맡는다** — 로고 알약이 홈이다. 머리칸을
           걷으면서 **나가는 길이 하나도 없어지지 않게** 같이 붙인 것이다. */
        extendBody: true,
        bottomNavigationBar: FloatingNavBar(
          // 3 번이 이 화면(신분증 아이콘)이다.
          currentIndex: 3,
          onTap: (index) {
            if (index == 0) {
              context.go('/home');
              return;
            }
            if (index == 1) {
              context.go('/videos');
              return;
            }
            _notReady(context, '준비 중입니다');
          },
        ),
        body: SafeArea(
          child: ListView(
            padding: EdgeInsets.fromLTRB(
              16,
              8,
              16,
              // 떠 있는 바에 마지막 칸이 가리지 않게.
              FloatingNavBar.heightOf(context),
            ),
            children: [
              _CardHero(card: card, nickname: user.nickname),
              const SizedBox(height: 16),
              _TeamBlock(teams: user.teams),
              const SizedBox(height: 16),
              _InfoBlock(user: user),
              const SizedBox(height: 16),
              const _VideosBlock(),
              const SizedBox(height: 16),
              const _MatchesBlock(),
              const SizedBox(height: 16),
              _AccountBlock(user: user),
            ],
          ),
        ),
      ),
    );
  }
}

/// 빛무리 아래에 깔리는 바탕. 🔴 **어둡게 둔다** — 카드 색이 아무리 밝아도
/// 배경이 밝아지면 흰 글자가 안 읽힌다.
const Color _kBg = Color(0xFF0A0F0C);
const Color _kOn = Color(0xFFFFFFFF);
/// 되돌릴 수 없는 일의 빨강 — 탈퇴·해체가 나눠 쓴다.
const Color _kDanger = Color(0xFFD32F2F);

/// 웹의 유리판 한 칸 — 제목 + 내용.
class _Block extends StatelessWidget {
  const _Block({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    /* 🔴 **유리다**(2026-09-22, 사용자 요청: 「흰색 블러 아주 살짝만」).
       뒤의 빛무리가 비쳐야 배경이 살아난다 — 불투명 판이면 카드 색을 따라
       움직이는 배경이 판에 다 가려진다.

       🔴 **`GlassPanel`(굴절 유리)이 아니라 `GlassSurface`(흐림 + 옅은 흰
       기)다.** 굴절 쪽은 `ImageFilter.shader` 라 Impeller 에서만 돌고 가드가
       필요하다 — 판이 여섯이라 그걸 다 걸 이유가 없다.

       🔴 **판 안의 단추에는 유리를 또 쓰지 않는다** — 「유리 안에 유리」는
       안쪽이 아직 안 끝난 바깥을 읽어 **내용이 프레임째로 사라진다**
       (`refractive_glass.dart`). 안쪽 것들은 색·테두리로만 층을 낸다. */
    return GlassSurface(
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: _kOn,
                fontSize: 14,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}

/// 카드가 이 화면의 **첫 얼굴**이다 — 가운데 위에 그냥 놓는다.
///
/// 🔴 **판(상자)도 「내 선수 카드」 제목도 없다**(2026-09-22, 사용자 요청).
/// 카드 자체가 무엇인지 말하고 있어서 제목은 같은 말을 두 번 하는 자리였고,
/// 상자는 카드 둘레에 테를 하나 더 둘러 **카드가 작아 보이게** 했다.
class _CardHero extends ConsumerWidget {
  const _CardHero({required this.card, required this.nickname});

  final PlayerCard? card;
  final String nickname;

  /// 히어로라 프로필 안의 다른 카드보다 크다.
  static const double _cardWidth = 200;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        /* 🔴 **수정 단추가 카드 오른쪽 위에 붙는다**(사용자 요청). 흐름 안에
           두면 카드가 그만큼 왼쪽으로 밀려 **가운데가 아니게** 된다 —
           `Stack` 으로 띄워 카드의 가운데를 지킨다. */
        SizedBox(
          width: double.infinity,
          child: Stack(
            alignment: Alignment.topCenter,
            clipBehavior: Clip.none,
            children: [
              // 🔴 카드가 없으면 빈 카드다 — 예외가 아니라 정상 상태다.
              if (card == null)
                const BlankPlayerCardView(width: _cardWidth)
              else
                PlayerCardView(
                  width: _cardWidth,
                  seed: card!.publicSlug,
                  alias: aliasOf(card!),
                  style: card!.style,
                  photoUrl: card!.photoUrl,
                ),
              /* 🔴 **글자다**(2026-09-22, 사용자 요청) — 아이콘(`tune`)은
                 무엇을 고치는 단추인지 안 읽혔다. 카드 **오른쪽 위 바깥**에
                 붙여 카드를 안 덮는다. */
              Positioned(
                top: 0,
                right: 0,
                child: _GlassButton(
                  buttonKey: const Key('profile-card-edit'),
                  label: card == null ? '카드 만들기' : '카드 수정',
                  onTap: () => card == null
                      ? _createCard(context, ref)
                      : Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => CardEditorScreen(card: card!),
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        /* 🔴 **닉네임이 카드 정중앙에 온다**(사용자 지적). 아이콘을 그냥
           옆에 붙이면 **둘을 합친 덩어리**가 가운데 서서 닉네임만 보면
           왼쪽으로 쏠린다.

           🔴 **왼쪽에 같은 폭의 빈 자리를 둬서 균형을 맞춘다.** `Stack` 으로
           아이콘을 흐름 밖에 띄우는 길도 있었는데, 그러면 Stack 이 글자
           크기로 줄어들어 **아이콘이 그 밖에 놓이고 눌리지 않는다**(시험이
           잡았다). 빈 자리는 눌릴 일이 없으니 이 쪽이 안전하다. */
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // 오른쪽 아이콘(28) + 사이(6) 만큼 왼쪽을 비운다.
            const SizedBox(width: 34),
            Flexible(
              child: Text(
                nickname,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: _kOn,
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(width: 6),
            _GlassIconButton(
              buttonKey: const Key('profile-edit'),
              icon: Icons.edit,
              tooltip: '닉네임 수정',
              onTap: () => showNicknameSheet(context, nickname),
            ),
          ],
        ),
      ],
    );
  }

  /// 🔴 카드는 **요청할 때** 생긴다(계약 `POST /me/card`) — 가입만으로는
  /// 안 생기고, 조회가 만들지도 않는다.
  ///
  /// 🔴 **첫 모습까지 저장한다** — 안 하면 앱에서 만든 카드가 웹에서 만든
  /// 것과 다르게 보인다(`createCardWithFirstLook`).
  Future<void> _createCard(BuildContext context, WidgetRef ref) async {
    try {
      await createCardWithFirstLook(ref.read(cardRepositoryProvider));
      ref.invalidate(myCardProvider);
    } catch (e) {
      if (context.mounted) _notReady(context, '$e');
    }
  }
}

/// 🔴 **유리 단추 — 안쪽 색을 안 채운다**(2026-09-22, 사용자 요청).
///
/// 뒤를 아주 살짝 흐리고 **제일 얇은 흰 선** 하나만 두른다. 면에 색을 넣으면
/// 카드 색을 따라 움직이는 배경이 그 자리에서 끊긴다.
///
/// 🔴 **판(`_Block`) 안에는 쓰지 않는다** — 「유리 안에 유리」가 되어 내용이
/// 프레임째로 사라진다(`refractive_glass.dart`). 이 둘은 카드 둘레, 즉
/// **판 밖**에 선다.
class _GlassButton extends StatelessWidget {
  const _GlassButton({
    required this.buttonKey,
    required this.label,
    required this.onTap,
  });

  final Key buttonKey;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return _GlassShell(
      radius: BorderRadius.circular(999),
      child: InkWell(
        key: buttonKey,
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          child: Text(
            label,
            style: const TextStyle(color: _kOn, fontSize: 12),
          ),
        ),
      ),
    );
  }
}

/// 같은 재질의 동그란 아이콘 단추.
class _GlassIconButton extends StatelessWidget {
  const _GlassIconButton({
    required this.buttonKey,
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  final Key buttonKey;
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: _GlassShell(
        radius: BorderRadius.circular(999),
        child: InkWell(
          key: buttonKey,
          onTap: onTap,
          child: SizedBox(
            width: 28,
            height: 28,
            child: Icon(icon, size: 14, color: _kOn),
          ),
        ),
      ),
    );
  }
}

/// 아래로 **부드럽게 펼쳐지는 칸**(2026-09-22, 사용자 요청: 「웹처럼 판이
/// 아래로 자연스럽고 부드럽게 열리면서」).
///
/// 🔴 **닫힐 때도 내용을 들고 있는다.** 접자마자 자식을 비우면 줄어들 것이
/// 없어 **툭 접힌다** — 웹이 같은 자리에 남긴 주석과 같은 이유다.
/// `AnimatedSize` 가 높이를 재 주므로 폼이 길어져도 맞출 것이 없다.
///
/// 🔴 **`ClipRect` 로 감싼다** — 줄어드는 동안 안쪽 내용이 밖으로 삐져나온다.
class _Fold extends StatelessWidget {
  const _Fold({required this.open, required this.child});

  final bool open;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: AnimatedSize(
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutCubic,
        alignment: Alignment.topCenter,
        child: open ? child : const SizedBox(width: double.infinity),
      ),
    );
  }
}

/// 유리 + **제일 얇은 흰 테**. 두 단추가 재질을 나눠 쓴다 — 한쪽만 고치면
/// 둘이 갈라진다.
class _GlassShell extends StatelessWidget {
  const _GlassShell({required this.radius, required this.child});

  final BorderRadius radius;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: radius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: kGlassBlur, sigmaY: kGlassBlur),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: radius,
            /* 🔴 **면은 비운다** — 사용자가 「안쪽 색상 다 빼」라고 짚은
               자리다. 형태는 아래 테두리가 세운다. */
            border: Border.all(
              color: _kOn,
              // 이 기기에서 그릴 수 있는 **가장 얇은 선**.
              width: 0.5,
            ),
          ),
          // Material 이 있어야 InkWell 의 물결이 그려진다(색은 안 넣는다).
          child: Material(color: Colors.transparent, child: child),
        ),
      ),
    );
  }
}

void _notReady(BuildContext context, String what) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(what)));
}

/// 소속 — 팀 이름 · 지역 · 종목, 그리고 만들기·고치기·나가기·해체.
///
/// 🔴 **주장과 팀원이 할 수 있는 일이 다르다**(계약 3-3절 권한표):
/// 주장은 고치고 해체하고 **나갈 수 없다**(남은 사람들의 팀이 주인 없이
/// 남는다). 팀원은 나가기만 한다.
class _TeamBlock extends ConsumerStatefulWidget {
  const _TeamBlock({required this.teams});

  final List<TeamMembership> teams;

  @override
  ConsumerState<_TeamBlock> createState() => _TeamBlockState();
}

class _TeamBlockState extends ConsumerState<_TeamBlock> {
  /// 펼쳐진 폼 — `null` 이면 닫힘, `''` 면 **만들기**, 그 밖이면 그 팀 고치기.
  String? _openFor;

  /// 🔴 **닫혀도 마지막 내용을 들고 있는다** — 접는 동안 폼이 사라지면
  /// 줄어들 것이 없어 툭 접힌다.
  String? _lastOpenFor;

  void _toggle(String key) => setState(() {
        _openFor = _openFor == key ? null : key;
        if (_openFor != null) _lastOpenFor = _openFor;
      });

  @override
  Widget build(BuildContext context) {
    final teams = widget.teams;
    final shown = _openFor ?? _lastOpenFor;
    final editing = shown == null || shown.isEmpty
        ? null
        : teams.where((t) => t.teamId == shown).firstOrNull;

    return _Block(
      title: '소속',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (teams.isEmpty)
            const Text('아직 팀이 없습니다', style: TextStyle(color: _kOn))
          else
            for (final t in teams)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                t.name,
                                style: const TextStyle(
                                  color: _kOn,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                '${t.region} · ${t.sportCode}',
                                style: TextStyle(
                                  color: _kOn.withValues(alpha: 0.7),
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        // 주장만 팀을 고칠 수 있다(계약 권한표).
                        if (t.isOwner)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: AppTheme.seed,
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: const Text(
                              '주장',
                              style: TextStyle(
                                color: Color(0xFF0B0B0B),
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                      ],
                    ),
                    _TeamActions(
                      team: t,
                      editing: _openFor == t.teamId,
                      onEdit: () => _toggle(t.teamId),
                    ),
                  ],
                ),
              ),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              key: const Key('profile-team-create'),
              icon: Icon(_openFor == '' ? Icons.close : Icons.add, size: 18),
              label: Text(_openFor == '' ? '닫기' : '팀 만들기'),
              style: OutlinedButton.styleFrom(
                foregroundColor: _kOn,
                side: BorderSide(color: _kOn.withValues(alpha: 0.4)),
              ),
              onPressed: () => _toggle(''),
            ),
          ),
          _Fold(
            open: _openFor != null,
            child: TeamForm(
              // 🔴 고치는 팀이 바뀌면 폼을 새로 세운다 — 안 그러면 칸에 옛
              //    팀 이름이 남는다.
              key: ValueKey('team-form-${shown ?? ''}'),
              team: editing,
              onDone: () => setState(() => _openFor = null),
            ),
          ),
        ],
      ),
    );
  }
}

/// 팀 한 줄에 붙는 단추들.
class _TeamActions extends ConsumerStatefulWidget {
  const _TeamActions({
    required this.team,
    required this.editing,
    required this.onEdit,
  });

  final TeamMembership team;
  final bool editing;
  final VoidCallback onEdit;

  @override
  ConsumerState<_TeamActions> createState() => _TeamActionsState();
}

class _TeamActionsState extends ConsumerState<_TeamActions> {
  /// 🔴 **되돌릴 수 없는 둘은 한 번 더 묻는다** — 나가기·해체.
  bool _armed = false;
  bool _busy = false;

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      // 🔴 소속은 `GET /me` 가 준다 — 다시 읽어야 이 칸이 따라온다.
      await ref.read(sessionControllerProvider.notifier).refreshMe();
    } catch (e) {
      if (mounted) _notReady(context, '$e');
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _armed = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.team;
    const danger = _kDanger;
    final repo = ref.read(teamRepositoryProvider);

    if (_armed) {
      return Row(
        children: [
          Expanded(
            child: FilledButton(
              key: Key('team-confirm-${t.teamId}'),
              style: FilledButton.styleFrom(backgroundColor: danger),
              onPressed: _busy
                  ? null
                  : () => _run(() => t.isOwner
                      ? repo.disbandTeam(t.teamId)
                      : repo.leaveTeam(t.teamId)),
              child: Text(
                _busy
                    ? '처리하는 중…'
                    : t.isOwner
                        ? '정말 해체합니다'
                        : '정말 나갑니다',
              ),
            ),
          ),
          const SizedBox(width: 8),
          TextButton(
            key: Key('team-cancel-${t.teamId}'),
            onPressed: _busy ? null : () => setState(() => _armed = false),
            style: TextButton.styleFrom(foregroundColor: _kOn),
            child: const Text('취소'),
          ),
        ],
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        if (t.isOwner)
          TextButton(
            key: Key('team-edit-${t.teamId}'),
            onPressed: widget.onEdit,
            style: TextButton.styleFrom(foregroundColor: _kOn),
            child: Text(widget.editing ? '닫기' : '수정'),
          ),
        TextButton(
          key: Key('team-leave-${t.teamId}'),
          onPressed: () => setState(() => _armed = true),
          style: TextButton.styleFrom(foregroundColor: danger),
          /* 🔴 **주장에게는 「나가기」를 안 낸다** — 서버가 409 로 막는다.
             내주면 눌러 보고 거절만 받는다. 주장의 길은 해체다. */
          child: Text(t.isOwner ? '팀 해체' : '팀 나가기'),
        ),
      ],
    );
  }
}

/// 정보 — 호칭 · 이메일 · 함께한 날.
class _InfoBlock extends ConsumerWidget {
  const _InfoBlock({required this.user});

  final AppUser user;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final d = user.createdAt;
    final joined =
        '${d.year}.${d.month.toString().padLeft(2, '0')}'
        '.${d.day.toString().padLeft(2, '0')}부터';
    final card = ref.watch(myCardProvider).value;
    return _Block(
      title: '정보',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          /* 🔴 **사람이 직접 적는다**(2026-09-16 결정, 미결 `paik` 36번).
             원래는 분석이 붙이는 값이라 화면이 읽기만 했다 — 팀이 다시
             정하면서 여기서 고친다. 분류(강점·활동)는 **안 받는다.** */
          /* 🔴 **아래 두 줄과 라벨 자리를 맞춘다**(사용자 지적). 이름표 폭
             (76)은 같은데 `CrossAxisAlignment.start` 라 글자 윗선이 안
             맞았다 — 오른쪽이 알약이라 높이가 달라서다. `baseline` 은 알약이
             글자가 아니라 못 쓰고, **가운데로 맞추면** 한 줄일 때 라벨과
             알약이 같은 선에 온다. */
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                width: 76,
                child: Text(
                  '호칭',
                  style: TextStyle(
                    color: _kOn.withValues(alpha: 0.7),
                    fontSize: 13,
                  ),
                ),
              ),
              Expanded(child: _TitlesRow(card: card)),
            ],
          ),
          const SizedBox(height: 8),
          _row('이메일', user.email),
          const SizedBox(height: 8),
          _row('함께한 날', joined),
        ],
      ),
    );
  }

  Widget _row(String label, String value) => Row(
    children: [
      SizedBox(
        width: 76,
        child: Text(
          label,
          style: TextStyle(color: _kOn.withValues(alpha: 0.7), fontSize: 13),
        ),
      ),
      Expanded(
        child: Text(value, style: const TextStyle(color: _kOn, fontSize: 13)),
      ),
    ],
  );
}

/// 호칭 알약들 + 고치는 입구.
///
/// 🔴 **비어 있을 때는 아무 말도 안 한다**(웹과 같은 판단). 바로 옆에
/// 「호칭 정하기」가 서 있어서 「아직 정한 호칭이 없습니다」를 두면 **빈 것을
/// 두 번 말하는** 자리가 된다.
///
/// 🔴 **미달 표식이 아니다**(계약 4장) — 빈 것은 정상이라 「없음」·자물쇠 같은
/// 표를 대신 넣지 않는다.
class _TitlesRow extends ConsumerStatefulWidget {
  const _TitlesRow({required this.card});

  final PlayerCard? card;

  @override
  ConsumerState<_TitlesRow> createState() => _TitlesRowState();
}

class _TitlesRowState extends ConsumerState<_TitlesRow> {
  bool _open = false;

  @override
  Widget build(BuildContext context) {
    final card = widget.card;
    final all = card?.titles ?? const <CardTitle>[];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (all.isNotEmpty)
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final t in all)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppTheme.seed.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    t.label,
                    style: const TextStyle(
                      color: AppTheme.seed,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
        // 🔴 카드가 없으면 고칠 데가 없다 — 호칭은 카드에 붙는다.
        if (card != null) ...[
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              // 알약이 있을 때만 위를 띄운다 — 없으면 라벨과 한 줄이어야 한다.
              padding: EdgeInsets.only(top: all.isEmpty ? 0 : 6),
              child: Material(
                color: Colors.transparent,
                shape: StadiumBorder(
                  side: BorderSide(color: _kOn.withValues(alpha: 0.3)),
                ),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  key: const Key('profile-titles-edit'),
                  onTap: () => setState(() => _open = !_open),
                  child: Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    child: Text(
                      _open
                          ? '닫기'
                          : all.isEmpty
                              ? '호칭 정하기'
                              : '호칭 고치기',
                      style: TextStyle(
                        color: _kOn.withValues(alpha: 0.85),
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          _Fold(
            open: _open,
            child: TitlesForm(
              card: card,
              onDone: () => setState(() => _open = false),
            ),
          ),
        ],
      ],
    );
  }
}

/// 내 영상 — **요약만.** 본체는 밀고 들어가는 전용 화면이다.
///
/// 🔴 **갈래별 편수를 적는다.** 웹은 편수를 안 적지만(영상 아래 `1 / N` 이
/// 이미 말한다) 여기엔 그 줄이 없어서, 편수마저 없으면 **들어가 보기 전에는
/// 영상이 있는지조차 모른다.**
class _VideosBlock extends ConsumerWidget {
  const _VideosBlock();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncVideos = ref.watch(myVideosProvider);

    return _Block(
      title: '내 영상',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: const Key('profile-videos'),
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => const MyVideosScreen()),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                Expanded(
                  child: asyncVideos.when(
                    loading: () => Text(
                      '불러오는 중…',
                      style: TextStyle(color: _kOn.withValues(alpha: 0.6)),
                    ),
                    /* 🔴 **오류를 「없음」으로 그리지 않는다** — 로그인이
                       풀렸는데 「아직 올린 영상이 없습니다」로 보이면 사람은
                       자기 영상이 사라진 줄 안다. */
                    error: (e, _) => Text(
                      '영상을 불러오지 못했습니다',
                      style: TextStyle(color: _kOn.withValues(alpha: 0.6)),
                    ),
                    data: (all) {
                      final split = splitVideos(all);
                      if (all.isEmpty) {
                        return const Text(
                          '아직 올린 영상이 없습니다',
                          style: TextStyle(color: _kOn),
                        );
                      }
                      return Text(
                        '분석 ${split.analyzed.length} · 업로드 ${split.uploaded.length}',
                        style: const TextStyle(color: _kOn, fontSize: 15),
                      );
                    },
                  ),
                ),
                Icon(
                  Icons.chevron_right,
                  color: _kOn.withValues(alpha: 0.6),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MatchesBlock extends StatelessWidget {
  const _MatchesBlock();

  @override
  Widget build(BuildContext context) {
    // ⚠️ 경기 경로(`GET /teams/{id}/matches`)는 아직 안 붙였다 — 웹도 팀이
    //    없으면 같은 문구를 보여 준다.
    return const _Block(
      title: '내 경기',
      child: Text('다가오는 경기가 없습니다.', style: TextStyle(color: _kOn)),
    );
  }
}

/// 계정 — 지인 검색 노출 · 로그아웃.
class _AccountBlock extends ConsumerWidget {
  const _AccountBlock({required this.user});

  final AppUser user;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Block(
      title: '계정',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          /* 🔴 **`Material` 로 감싼다.** `ListTile` 은 바탕과 잉크를 가장 가까운
             Material 에 그리는데, 색 있는 상자 안에 그냥 두면 그 상자가 효과를
             가린다고 프레임워크가 경고를 던진다(시험이 그걸로 깨졌다). */
          Material(
            color: Colors.transparent,
            child: SwitchListTile(
              key: const Key('profile-searchable'),
              contentPadding: EdgeInsets.zero,
              value: user.isNicknameSearchable,
              activeThumbColor: AppTheme.seed,
              title: const Text(
                '지인 검색에 나를 보이기',
                style: TextStyle(color: _kOn, fontSize: 14),
              ),
              subtitle: Text(
                '닉네임으로 나를 찾아 지인 신청을 보낼 수 있습니다.',
                style: TextStyle(
                  color: _kOn.withValues(alpha: 0.6),
                  fontSize: 12,
                ),
              ),
              onChanged: (v) async {
                try {
                  await ref
                      .read(sessionControllerProvider.notifier)
                      .setNicknameSearchable(v);
                } catch (e) {
                  if (context.mounted) _notReady(context, '$e');
                }
              },
            ),
          ),
          const SizedBox(height: 8),
          /* 🔴 **로그아웃이 왼쪽, 탈퇴가 오른쪽 끝**(웹과 같은 자리). 자주
             쓰는 것이 먼저고 **위험한 것이 끝**이다. 🔴 로그아웃은 빨갛지
             않다 — 같은 줄에서 빨강을 나눠 쓰면 **탈퇴의 빨강이 경고로 안
             읽힌다.** 다시 로그인하면 그만인 일이다. */
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                key: const Key('profile-logout'),
                onPressed: () =>
                    ref.read(sessionControllerProvider.notifier).logout(),
                style: TextButton.styleFrom(foregroundColor: _kOn),
                child: const Text('로그아웃'),
              ),
              const SizedBox(width: 8),
              /* 🔴 **채운 빨강이다**(2026-09-22, 사용자 요청). 글자만 빨갛던
                 때는 옆의 로그아웃과 **같은 무게**로 보여서, 되돌릴 수 없는
                 쪽이 눈에 안 띄었다. */
              FilledButton(
                key: const Key('profile-delete-account'),
                onPressed: () => showDeleteAccountSheet(context),
                style: FilledButton.styleFrom(
                  backgroundColor: _kDanger,
                  foregroundColor: _kOn,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  visualDensity: VisualDensity.compact,
                ),
                child: const Text('회원 탈퇴'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
