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
import '../../../../core/widgets/silver_edge.dart';
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
            /* 🔴 **판을 두 개씩 나란히 둔다**(2026-09-22, 사용자 요청).
               다섯이 세로로 줄줄이 서서 화면이 한참 길었다.
               「내 영상」만 한 줄을 다 쓴다 — 자주 들어가는 입구다. */
            children: [
              _CardHero(card: card, nickname: user.nickname),
              const SizedBox(height: 16),
              const _VideosBlock(),
              const SizedBox(height: 12),
              _Pair(
                left: [
                  _TeamBlock(teams: user.teams),
                  const _MatchesBlock(),
                ],
                right: [
                  _InfoBlock(user: user),
                  _AccountBlock(user: user),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 빛무리 아래에 깔리는 바탕 — `kAuroraBase`(중성 회색)를 그대로 쓴다.
/// 🔴 **화면마다 따로 정하지 않는다** — 갈리면 홈과 프로필이 다른 앱처럼
/// 보인다.
const Color _kBg = kAuroraBase;
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
    /* 🔴 **흐림(`BackdropFilter`)을 안 쓴다** (2026-09-22 정정).
       처음엔 `GlassSurface`(흐림 + 옅은 흰 기)로 만들었는데, 그것이
       **스크롤할 때 흰 직선이 여럿 나오는** 원인이었다: 흐림은 뒤를 퍼다
       쓰는데 **판 가장자리에서는 퍼 올 것이 없어 가장자리 값을 늘려 쓰고**,
       목록이 구르면 그 늘린 띠가 매 프레임 달라져 선으로 보인다. 판이
       여섯이라 선도 여섯이었다(사용자: 「흰 직선들이 계속 나오고」).

       🔴 **대신 반투명 면 + 은빛 실선**이다 — 이 저장소가 `SilverEdge` 를
       둔 이유와 같다(「유리가 아니다 … 흐림 없이 색만 얹는다」). 면이
       반투명이라 뒤의 빛무리는 그대로 비친다. */
    return DecoratedBox(
      decoration: BoxDecoration(
        /* 🔴 레퍼런스의 판(`#444444`)이 바탕(`#2F2F2F`)보다 **한 단 밝다**.
           흰 기를 8% 얹으면 그 자리에 온다 — 회색 바탕에서는 5.5% 로는
           판이 배경에 묻힌다. */
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: SilverEdge.barLine,
          width: SilverEdge.barLineWidth,
        ),
      ),
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

/// 판을 **두 세로 줄**로 쌓는다.
///
/// 🔴 **줄(row)이 아니라 열(column)이다**(2026-09-22 정정, 사용자 지적:
/// 「계정판도 정보 판 바로 아래에 안 붙어있잖아」). 줄로 짜면 **한 줄의
/// 높이가 그 줄에서 제일 긴 판을 따라가서**, 짧은 쪽 아래에 빈 자리가
/// 생기고 다음 줄이 거기서부터 시작한다. 열로 쌓으면 각 판이 **바로 위
/// 판 밑에** 붙고, 위 판이 늘거나 줄면 아래 것이 그만큼 따라 움직인다.
///
/// 🔴 그래서 `IntrinsicHeight` 도 필요 없다 — 그것이 펼침을 「팍」 열리게
/// 만들던 것이다(같은 날 앞선 정정).
class _Pair extends StatelessWidget {
  const _Pair({required this.left, required this.right});

  final List<Widget> left;
  final List<Widget> right;

  @override
  Widget build(BuildContext context) {
    Widget column(List<Widget> items) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < items.length; i += 1) ...[
              if (i > 0) const SizedBox(height: 12),
              items[i],
            ],
          ],
        );

    return Row(
      // 두 열은 서로 키를 안 맞춘다 — 각자 제 내용만큼 길다.
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: column(left)),
        const SizedBox(width: 12),
        Expanded(child: column(right)),
      ],
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
              /* 🔴 **카드 바로 오른쪽**(2026-09-22, 사용자 요청). `right: 0`
                 으로 두면 화면 끝에 붙어 카드와 멀어진다 — 카드가 가운데
                 서므로 그 오른쪽 변은 `화면폭/2 + 카드폭/2` 다. */
              Positioned(
                top: 0,
                left: MediaQuery.sizeOf(context).width / 2 +
                    _cardWidth / 2 +
                    // 카드와 살짝 띄운다. 붙이면 카드 모서리를 먹는다.
                    2,
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
class _Fold extends StatefulWidget {
  const _Fold({required this.open, required this.child});

  final bool open;
  final Widget child;

  @override
  State<_Fold> createState() => _FoldState();
}

class _FoldState extends State<_Fold> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 420),
    value: widget.open ? 1 : 0,
  );

  /* 🔴 **`easeOutCubic` 이 아니다**(2026-09-22 정정). 그 곡선은 **앞이
     가파르다** — 120ms 만에 이미 85% 까지 자라서, 뒤에 붙였던 페이드가
     걷히는 순간에는 **거의 다 펼쳐진 뒤**였다. 그래서 「한 번에 늘어나
     있다」로 보였다(사용자가 세 번 짚었다). 앞뒤가 고른 곡선이라야 자라는
     것이 보인다. */
  late final _curve = CurvedAnimation(parent: _c, curve: Curves.easeInOut);

  @override
  void initState() {
    super.initState();
    /* 🔴 **다 접힌 순간을 듣는다.** `SizeTransition` 은 스스로 다시 그리지만
       **이 `build` 는 다시 안 불린다** — 그래서 아래 「다 접히면 트리에서
       뺀다」가 영영 안 돌고, 보이지 않는 폼이 그대로 남는다(시험이 「새 팀」을
       둘로 세어 잡았다: 목록 하나 + 안 보이는 입력칸 하나). */
    _c.addStatusListener((status) {
      if (status == AnimationStatus.dismissed && mounted) setState(() {});
    });
  }

  @override
  void didUpdateWidget(_Fold old) {
    super.didUpdateWidget(old);
    if (widget.open != old.open) {
      widget.open ? _c.forward() : _c.reverse();
    }
  }

  @override
  void dispose() {
    _curve.dispose();
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    /* 🔴 **다 접히면 트리에서 뺀다** — 안 빼면 보이지 않는 폼의 글쇠 포커스가
       살아 있어, 접은 뒤에도 자판이 올라온다. */
    if (_c.isDismissed && !widget.open) {
      return const SizedBox(width: double.infinity);
    }
    /* 🔴 **페이드를 안 겹친다.** 같은 곡선으로 흐리기까지 걸면 자라는 동안
       내용이 안 보여서, 보일 때쯤엔 이미 다 자라 있다 — 그게 「팍」의
       정체였다. 자라는 것 하나만 보여 준다. */
    return SizeTransition(
      sizeFactor: _curve,
      // 위에서 아래로 자란다.
      alignment: Alignment.topCenter,
      child: widget.child,
    );
  }
}

/// 유리 + **제일 얇은 흰 테**./// 유리 + **제일 얇은 흰 테**. 두 단추가 재질을 나눠 쓴다 — 한쪽만 고치면
/// 둘이 갈라진다.
class _GlassShell extends StatelessWidget {
  const _GlassShell({required this.radius, required this.child});

  final BorderRadius radius;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    /* 🔴 **흐림을 안 쓴다**(2026-09-22 정정). `BackdropFilter` 로 만들었더니
       **카드 둘레에 선이 보였다** — 흐림이 가장자리에서 퍼 올 것이 없어
       늘려 쓰는 띠가, 카드 위에 겹쳐 앉은 이 단추 자리에서 드러났다.
       판과 같은 이유이고 같은 처방이다. */
    return DecoratedBox(
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
      child: Material(
        color: Colors.transparent,
        borderRadius: radius,
        clipBehavior: Clip.antiAlias,
        child: child,
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
                    /* 🔴 **배지를 이름 옆이 아니라 아래 줄에 둔다**
                       (2026-09-22). 반쪽 폭에서는 이름 옆에 붙이면 긴
                       팀 이름이 한 글자씩 끊겨 흐른다. */
                    Text(
                      t.name,
                      style: const TextStyle(
                        color: _kOn,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          '${t.region} · ${t.sportCode}',
                          style: TextStyle(
                            color: _kOn.withValues(alpha: 0.7),
                            fontSize: 11,
                          ),
                        ),
                        // 주장만 팀을 고칠 수 있다(계약 권한표).
                        if (t.isOwner)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 7,
                              vertical: 1,
                            ),
                            decoration: BoxDecoration(
                              color: AppTheme.seed,
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: const Text(
                              '주장',
                              style: TextStyle(
                                color: Color(0xFF0B0B0B),
                                fontSize: 10,
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
              icon: Icon(_openFor == '' ? Icons.close : Icons.add, size: 16),
              label: Text(
                _openFor == '' ? '닫기' : '팀 만들기',
                style: const TextStyle(fontSize: 12),
              ),
              style: OutlinedButton.styleFrom(
                foregroundColor: _kOn,
                side: BorderSide(color: _kOn.withValues(alpha: 0.4)),
                visualDensity: VisualDensity.compact,
                padding: const EdgeInsets.symmetric(horizontal: 10),
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
      // 🔴 확인 단계도 세로다 — 반쪽 폭에서 「정말 해체합니다」가 잘린다.
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
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
          TextButton(
            key: Key('team-cancel-${t.teamId}'),
            onPressed: _busy ? null : () => setState(() => _armed = false),
            style: TextButton.styleFrom(foregroundColor: _kOn),
            child: const Text('취소'),
          ),
        ],
      );
    }

    /* 🔴 **왼쪽부터 붙인 컴팩트 알약**(2026-09-22, 사용자 요청: 「지금 위치
       너무 애매하고」). 오른쪽 끝에 글자만 띄워 두니 **무엇에 딸린 단추인지**
       가 안 읽혔다 — 팀 이름 바로 아래 왼쪽에 붙어야 그 팀의 것으로 보인다. */
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [
          if (t.isOwner)
            _Pill(
              pillKey: Key('team-edit-${t.teamId}'),
              label: widget.editing ? '닫기' : '수정',
              onTap: widget.onEdit,
            ),
          _Pill(
            pillKey: Key('team-leave-${t.teamId}'),
            /* 🔴 **주장에게는 「나가기」를 안 낸다** — 서버가 409 로 막는다.
               내주면 눌러 보고 거절만 받는다. 주장의 길은 해체다. */
            label: t.isOwner ? '팀 해체' : '팀 나가기',
            danger: true,
            onTap: () => setState(() => _armed = true),
          ),
        ],
      ),
    );
  }
}

/// 정보 — 호칭 · 이메일 · 함께한 날.
///
/// 🔴 **라벨을 값 위에 쌓는다**(2026-09-22). 판이 반쪽 폭이 되면서 옆에
/// 붙이던 76px 이름표 때문에 이메일이 **한 글자씩 끊겨** 여러 줄로 흘렀다.
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
          /* 🔴 **호칭은 라벨 오른쪽에 선다**(2026-09-22, 사용자 요청).
             아래에 두면 알약 한두 개 때문에 줄이 하나 더 생겨, 옆의 이메일·
             함께한 날과 리듬이 안 맞았다. */
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                // 알약의 첫 줄과 글자 높이를 맞춘다.
                padding: const EdgeInsets.only(top: 3),
                child: _label('호칭'),
              ),
              const SizedBox(width: 8),
              Expanded(child: _TitlesRow(card: card)),
            ],
          ),
          const SizedBox(height: 10),
          _label('이메일'),
          const SizedBox(height: 2),
          /* 🔴 **이메일은 `@` 에서 끊는다.** 좁은 칸에서 기본 줄바꿈은 글자
             단위라 `player@supersub.te` / `st` 처럼 잘린다 — 읽기 나쁘다. */
          Text(
            user.email.replaceFirst('@', '@\u200B'),
            style: const TextStyle(color: _kOn, fontSize: 13),
          ),
          const SizedBox(height: 10),
          _label('함께한 날'),
          const SizedBox(height: 2),
          Text(joined, style: const TextStyle(color: _kOn, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _label(String text) => Text(
        text,
        style: TextStyle(color: _kOn.withValues(alpha: 0.7), fontSize: 12),
      );
}

/// 작은 알약 단추 — 좁은 판에서 글자 단추 대신 쓴다.
class _Pill extends StatelessWidget {
  const _Pill({
    required this.pillKey,
    required this.label,
    required this.onTap,
    this.danger = false,
  });

  final Key pillKey;
  final String label;
  final VoidCallback onTap;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final ink = danger ? _kDanger : _kOn.withValues(alpha: 0.85);
    return Material(
      color: Colors.transparent,
      shape: StadiumBorder(
        side: BorderSide(color: ink.withValues(alpha: danger ? 0.7 : 0.3)),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: pillKey,
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          child: Text(
            label,
            // 🔴 좁은 칸에서 글자가 **세로로 쌓이지 않게** 한다.
            softWrap: false,
            overflow: TextOverflow.visible,
            style: TextStyle(color: ink, fontSize: 12),
          ),
        ),
      ),
    );
  }
}

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

/// 계정 — 지인 검색 노출 · 로그아웃 · 탈퇴.
///
/// 🔴 **반쪽 폭이라 세로로 쌓는다**(2026-09-22). `SwitchListTile` 은 제목과
/// 스위치를 한 줄에 놓아서 좁은 칸에서 **제목이 두세 줄로 흐르고** 스위치가
/// 구석에 끼었다. 설명줄은 걷었다 — 좁은 칸에서 넉 줄을 먹는다.
class _AccountBlock extends ConsumerWidget {
  const _AccountBlock({required this.user});

  final AppUser user;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Block(
      title: '계정',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '지인 검색 노출',
                  style: TextStyle(
                    color: _kOn.withValues(alpha: 0.85),
                    fontSize: 12,
                  ),
                ),
              ),
              /* 🔴 **`Material` 로 감싼다.** 스위치는 잉크를 가장 가까운
                 Material 에 그리는데, 없으면 프레임워크가 경고를 던진다
                 (시험이 그걸로 깨졌다). */
              Material(
                color: Colors.transparent,
                child: Switch(
                  key: const Key('profile-searchable'),
                  value: user.isNicknameSearchable,
                  activeThumbColor: AppTheme.seed,
                  // 좁은 칸이라 기본 여백을 줄인다.
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
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
            ],
          ),
          const SizedBox(height: 8),
          /* 🔴 **세로로 쌓는다** — 한 줄에 두면 「회원 탈퇴」가 반쪽 폭에서
             잘린다. 자주 쓰는 로그아웃이 위, **되돌릴 수 없는 탈퇴가 아래**다.
             🔴 로그아웃은 안 빨갛다 — 같은 칸에서 빨강을 나눠 쓰면 탈퇴의
             빨강이 경고로 안 읽힌다. */
          OutlinedButton(
            key: const Key('profile-logout'),
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).logout(),
            style: OutlinedButton.styleFrom(
              foregroundColor: _kOn,
              side: BorderSide(color: _kOn.withValues(alpha: 0.35)),
              visualDensity: VisualDensity.compact,
            ),
            child: const Text('로그아웃', style: TextStyle(fontSize: 12)),
          ),
          const SizedBox(height: 6),
          FilledButton(
            key: const Key('profile-delete-account'),
            onPressed: () => showDeleteAccountSheet(context),
            style: FilledButton.styleFrom(
              backgroundColor: _kDanger,
              foregroundColor: _kOn,
              visualDensity: VisualDensity.compact,
            ),
            child: const Text('회원 탈퇴', style: TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
