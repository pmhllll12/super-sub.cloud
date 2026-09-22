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
import '../../../card/presentation/card_editor_screen.dart';
import '../../../video/presentation/screens/my_videos_screen.dart';
import '../../../../core/widgets/card_side_smoke.dart';
import '../widgets/silver_sweep_border.dart';
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
        /* 🔴 **`bottom: false` 가 있어야 내용이 바 밑으로 지나간다**
           (2026-09-22, 사용자 지적: 「하단바 자체에 검정 판이 또 있어서
           안 보인다 … 판 자체가 직선으로 보이지?」).

           `extendBody: true` 는 **바 높이만큼 body 의 `MediaQuery` 아래
           여백을 늘려 준다** — `SafeArea` 가 그것을 그대로 먹어서 목록이
           **바 윗변에서 잘렸다.** 그래서 반투명 바 뒤에 비칠 것이 아무것도
           없었고, 잘린 자리가 **가로 직선**으로 드러났다(판 둘이 나란히
           같은 높이에서 끊겨 더 또렷했다).

           🔴 **`SafeArea` 를 통째로 걷지는 않는다** — 위쪽(상태 바)은 여전히
           피해야 한다. 아래만 끈다.

           ⚠️ 바에 가리는 것은 아래 `padding` 이 맡는다 — 둘이 **같은 일을
           두 번** 하고 있었던 것이고, 남길 쪽은 `padding` 이다(그쪽은 자리를
           비워 줄 뿐 **잘라 내지 않는다**). */
        body: SafeArea(
          bottom: false,
          child: ListView(
            padding: EdgeInsets.fromLTRB(
              _kEdge,
              8,
              _kEdge,
              // 떠 있는 바에 마지막 칸이 가리지 않게.
              FloatingNavBar.heightOf(context),
            ),
            /* 🔴 **판을 두 개씩 나란히 둔다**(2026-09-22, 사용자 요청).
               다섯이 세로로 줄줄이 서서 화면이 한참 길었다.
               「내 영상」만 한 줄을 다 쓴다 — 자주 들어가는 입구다. */
            children: [
              _CardHero(card: card, nickname: user.nickname),
              /* 🔴 **닉네임과 판 사이를 흰 선으로 가른다**(2026-09-22, 사용자
                 요청: 「닉네임과 내 영상 판 가운데에 완전 흰색 선으로」).
                 위아래 여백을 같게 줘서 선이 **둘의 한가운데**에 선다. */
              const SizedBox(height: 14),
              const _Rule(),
              const SizedBox(height: 14),
              const _VideosBlock(),
              const SizedBox(height: _kGap),
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

/// 빛무리 아래에 깔리는 바탕 — **완전한 검정**이다(2026-09-22 정정,
/// 사용자 요청: 「배경 완전 검정으로」).
///
/// 🔴 전에는 `kAuroraBase`(#141417)를 그대로 썼고 판이 그 위에 **반투명
/// 흰 면**으로 떴다. 이제는 **바탕이 검정, 판이 `kAuroraBase`** 다 — 둘이
/// 자리를 맞바꾼 셈이라 테두리 없이도 판의 경계가 선다(아래 [_Block]).
///
/// ⚠️ 홈은 여전히 `kAuroraBase` 다. 두 화면의 바탕이 갈린 것은 **일부러**이고,
/// 되돌리려면 이 한 줄이다.
const Color _kBg = Color(0xFF000000);
const Color _kOn = Color(0xFFFFFFFF);

/// 화면 양끝 ↔ 판 사이, 그리고 판끼리의 간격. **둘 다 같은 값**이다
/// (2026-09-22 사용자 요청: 「양옆 화면 끝에서 판의 거리가 6픽셀 … 판끼리의
/// 거리도 6픽셀 똑같이」). 전에는 바깥 16 · 안쪽 12 로 갈려 있었다.
///
/// 🔴 **논리 픽셀이다 — `DesignScale`(`context.d`)을 쓰지 않는다.** 그쪽은
/// 화면 폭에 비례해 늘어나서 **기기마다 다른 여백**이 된다. 요청이 「어떤
/// 휴대폰에서건」이라 비례하지 않는 값을 쓴다.
const double _kEdge = 6;
const double _kGap = 6;

/// 되돌릴 수 없는 일의 빨강 — 탈퇴·해체가 나눠 쓴다.
const Color _kDanger = Color(0xFFD32F2F);

/// 닉네임과 아래 판들을 가르는 **완전한 흰 선**(2026-09-22, 사용자 요청).
///
/// 🔴 **반투명이 아니라 순백(`_kOn`)이다** — 「완전 흰색」으로 짚으신 자리다.
/// 판의 면([kSurfaceWhite])처럼 옅게 주면 검은 바탕에서 **회색 선**이 되어
/// 가르는 일을 못 한다.
///
/// 굵기는 **그 기기에서 그릴 수 있는 가장 얇은 선**이다 — 순백이라 두꺼우면
/// 선이 아니라 띠가 되고, 카드보다 그쪽으로 눈이 간다.
class _Rule extends StatelessWidget {
  const _Rule();

  /// 가로로 차지하는 몫 — 🔴 **화면 폭 전체가 아니다**(2026-09-22 정정,
  /// 사용자 요청: 「지금의 3분의 2로 길이 줄이자」). 가운데 맞춤이라 좌우가
  /// 같은 길이씩 짧아진다.
  static const double _widthFactor = 2 / 3;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 1 / MediaQuery.devicePixelRatioOf(context),
      child: const FractionallySizedBox(
        widthFactor: _widthFactor,
        child: ColoredBox(color: _kOn),
      ),
    );
  }
}

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

       🔴 **대신 색만 얹는다** — 이 저장소가 `SilverEdge` 를 둔 이유와 같다
       (「유리가 아니다 … 흐림 없이 색만 얹는다」).

       🔴 **면은 [kSurfaceWhite](반투명 흰색), 테두리는 없다**(2026-09-22
       사용자 요청: 「판들과 하단바 색상 흰색으로 · 흰색 살짝만 들어간 판으로
       뒤에 비치긴 해야해」 + 레퍼런스 한 장).

       하단바 · 로고 알약과 **같은 값**을 쓴다 — 셋이 한 재질이다. */
    return DecoratedBox(
      decoration: BoxDecoration(
        color: kSurfaceWhite,
        borderRadius: BorderRadius.circular(16),
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
          if (i > 0) const SizedBox(height: _kGap),
          items[i],
        ],
      ],
    );

    return Row(
      // 두 열은 서로 키를 안 맞춘다 — 각자 제 내용만큼 길다.
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: column(left)),
        const SizedBox(width: _kGap),
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

  /// 연기가 카드 위아래로 더 차지하는 자리.
  ///
  /// 🔴 **0 으로 두지 말 것** — 연기가 카드 높이에서 딱 끊기면 그 끝이
  /// **가로선**으로 보인다. 덩이들이 제풀에 옅어져 사라질 여유를 준다.
  ///
  /// ⚠️ **한 번 위/아래를 따로 두고 아래끝을 흰 선에 맞췄다가 되돌렸다**
  /// (2026-09-22) — 그때는 선 위를 두 색으로 꽉 채우려던 것이었다.
  static const double _smokePad = 96;

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
              /* 🔴 **카드보다 먼저 그린다** — 연기는 카드 뒤에 있어야 한다.
                 `Stack` 은 나중 것이 위이므로 이 자리를 옮기면 연기가 카드를
                 덮는다. 카드가 없으면(빈 카드) 쓸 색도 없으니 안 그린다. */
              if (card?.style != null)
                Positioned(
                  // 카드보다 위아래로 조금 넉넉히 — 연기가 카드 높이에서
                  // 뚝 끊기면 그 끝이 **가로선**으로 드러난다.
                  top: -_smokePad,
                  bottom: -_smokePad,
                  left: 0,
                  right: 0,
                  child: CardSideSmoke(
                    colors: (a: card!.style!.bg, b: card!.style!.brushColor),
                    cardWidth: _cardWidth,
                  ),
                ),
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
                 서므로 그 오른쪽 변은 `무대폭/2 + 카드폭/2` 다.

                 🔴 **「무대폭」은 화면 폭이 아니라 목록 여백을 뺀 폭이다**
                 (2026-09-22 정정). 이 `Stack` 은 `ListView` 의 좌우 여백
                 **안**에 있어서 좌표 0 이 화면 왼쪽이 아니다. 화면 폭을
                 그대로 쓰면 단추가 여백만큼 오른쪽으로 밀리는데, 여백이
                 16 이던 동안은 카드와의 틈이 18 이라 **틀린 줄 몰랐다** —
                 여백을 [_kEdge] 로 줄이자 드러났다. */
              Positioned(
                /* 🔴 **오른쪽 아래다**(2026-09-22 정정, 사용자 요청: 「카드
                   오른쪽 위에 있는 카드 수정 버튼을 카드 오른쪽 아래로」).
                   `top: 0` 이던 자리다. */
                bottom: 0,
                /* 🔴 **카드 오른쪽 변 ↔ 화면 오른쪽 끝의 한가운데**
                   (2026-09-22, 사용자 요청).

                   🔴 **`left` 에 좌표를 계산해 넣지 않는다** — 그건 단추의
                   **왼쪽 변**을 놓는 것이라, 가운데에 맞추려면 단추 폭을 알아야
                   하고 글자가 바뀌면(「카드 만들기」) 어긋난다. 대신 **틈 전체를
                   상자로 잡고** 아래 `Center` 에게 맡긴다.

                   `right: -_kEdge` — 이 `Stack` 은 목록의 좌우 여백 안이라
                   화면 끝이 여기서 `-_kEdge` 다. */
                left:
                    (MediaQuery.sizeOf(context).width - 2 * _kEdge) / 2 +
                    _cardWidth / 2,
                right: -_kEdge,
                child: Center(
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
        /* 🔴 **키웠다**(2026-09-22, 사용자 요청). 12/7·글자 12 → 14/9·글자 14.
           ⚠️ 여기가 거의 한계다 — 이 단추는 **카드 오른쪽 변과 화면 끝 사이**
           (약 105논리px)에 들어가야 한다. 더 키우면 그 틈을 넘어 글자가
           줄바꿈되거나 카드를 덮는다. */
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          child: Text(label, style: const TextStyle(color: _kOn, fontSize: 14)),
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
        /* 🔴 **면이 흰색 10% 다**(2026-09-22 정정, 사용자 요청: 「카드 수정
           버튼 안쪽을 흰색 10퍼만 주자」).

           ⚠️ 전에는 **비워** 뒀다(사용자가 「안쪽 색상 다 빼」라고 짚었던
           자리다) — 그때는 카드 위에 얹혀서 카드 그림이 비쳐야 했다. 이제
           단추가 카드 **밖**(오른쪽 아래 틈)으로 나와서 비칠 것이 검은
           바탕뿐이라, 면이 없으면 글자만 떠 있는 것처럼 보인다.

           🔴 **연필 단추도 같이 바뀐다** — 둘이 이 틀을 나눠 쓴다. 한쪽만
           고치면 재질이 갈린다. */
        color: _kOn.withValues(alpha: 0.10),
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
                  : () => _run(
                      () => t.isOwner
                          ? repo.disbandTeam(t.teamId)
                          : repo.leaveTeam(t.teamId),
                    ),
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
        /* 🔴 **아주 조금만 키웠다**(2026-09-22, 사용자 요청: 「진짜 아주
           살짝만」). 안여백 10/4 → 12/6, 글자 12 → 13. 더 키우면 반쪽 폭
           칸에서 「팀 해체」가 「수정」 옆에 못 서고 줄이 바뀐다. */
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: Text(
            label,
            // 🔴 좁은 칸에서 글자가 **세로로 쌓이지 않게** 한다.
            softWrap: false,
            overflow: TextOverflow.visible,
            style: TextStyle(color: ink, fontSize: 13),
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
                  padding: const EdgeInsets.symmetric(
                    horizontal: 9,
                    vertical: 3,
                  ),
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
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
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

  /// 판 높이.
  ///
  /// 🔴 **옛 판과 같은 키다**(2026-09-22 정정, 사용자 지적: 「내 영상 판 너
  /// 맘대로 또 세로 크기 키우지 말고, 원래대로 줄여」). 사진을 깔면서 132 로
  /// 늘렸던 것을 되돌렸다 — 화면에서 재 보니 옛 판이 **235물리px = 90논리px**
  /// 였다.
  ///
  /// ⚠️ 사진이 있어야 하는 판이라 **내용이 아니라 이 값이** 키를 정한다.
  /// 그래서 글자를 키우거나 줄여도 판은 안 움직인다.
  static const double _height = 90;

  static const double _radius = 16;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    /* 🔴 **다른 판들과 생김새가 다르다**(2026-09-22, 사용자 요청). 사진이
       깔리고, 글자는 「내 영상」 하나뿐이며, **판 전체가 단추**다.
       숫자(「분석 2 · 업로드 2」)와 오른쪽 `>` 는 걷었다.

       🔴 **그래서 [_Block] 을 안 쓴다.** 그쪽은 제목 + 내용 두 칸짜리 틀이라
       여기 쓰려면 제목도 안여백도 다 꺼야 하고, **끌 것이 많다는 것 자체가
       재사용하면 안 된다는 뜻**이다(`MiniPitch` 때와 같은 판단). */
    return SilverSweepBorder(
      radius: _radius,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(_radius),
        child: SizedBox(
          height: _height,
          width: double.infinity,
          child: Stack(
            fit: StackFit.expand,
            children: [
              /* 🔴 **얼굴이 가운데 오게 자른다**(사용자 요청). 원본이
                 3340×724 짜리 가로로 긴 사진이라 `cover` 로 채우면 좌우가
                 많이 잘리는데, 머리가 원본의 가로 한가운데에 있어서
                 `Alignment.center` 가 곧 「얼굴 가운데」다. */
              Image.asset(
                'assets/images/videos_cover.jpg',
                fit: BoxFit.cover,
                alignment: Alignment.center,
              ),
              /* 🔴 **어둡게 깐다.** 사진이 밝아서 그냥 두면 흰 글자가 연기에
                 묻힌다. 아래로 갈수록 더 어둡게 해서 **글자가 앉는 쪽**을
                 눌러 준다 — 글자에 그림자를 주는 것보다 깨끗하다. */
              const DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [Color(0x99000000), Color(0x33000000)],
                  ),
                ),
              ),
              /* 🔴 **왼쪽 위 구석**(2026-09-22 정정, 사용자 요청). 한가운데
                 큰 글자로 뒀던 것을 옮겼다 — 사진이 주인공이고 글자는 이름표다.
                 위 그라데이션도 **위가 짙게** 뒤집었다(글자가 앉는 쪽을 눌러
                 준다). */
              const Align(
                alignment: Alignment.topLeft,
                child: Padding(
                  padding: EdgeInsets.fromLTRB(14, 10, 0, 0),
                  child: Text(
                    '내 분석/업로드 영상',
                    style: TextStyle(
                      color: _kOn,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.2,
                    ),
                  ),
                ),
              ),
              /* 🔴 **판 전체가 단추다**(사용자 요청). `Material` 이 있어야
                 물결이 그려지고, 맨 위에 둬야 사진·글자가 탭을 안 먹는다. */
              Material(
                color: Colors.transparent,
                child: InkWell(
                  key: const Key('profile-videos'),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const MyVideosScreen(),
                    ),
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
                /* 🔴 **작게 줄인다**(2026-09-22, 사용자 요청: 「너무 커. 좀
                   크기 줄이고」). `Switch` 는 크기를 직접 못 받아서
                   `Transform.scale` 로 줄인다 — 그래서 **누르는 자리도 같이**
                   줄어든다(0.8 까지가 한계다. 더 줄이면 손가락으로 못 짚는다).
                   🔴 `Align` 으로 감싸 **줄어든 만큼 남는 자리를 안 차지하게**
                   한다 — 안 감싸면 옛 크기만큼 자리를 잡는다. */
                child: Transform.scale(
                  scale: 0.8,
                  child: Switch(
                    key: const Key('profile-searchable'),
                    value: user.isNicknameSearchable,
                    // 🔴 **흰색이다**(사용자 요청) — 브랜드 민트였다.
                    activeThumbColor: _kOn,
                    activeTrackColor: _kOn.withValues(alpha: 0.45),
                    /* 🔴 **끄면 검정이다**(2026-09-22, 사용자 요청: 「끌 때는
                       검정으로」). 기본 꺼짐 색은 테마가 주는 회색이라 **판
                       위에서 떠 보였다.**

                       🔴 **원과 면의 검정이 다르다**(2026-09-22 정정, 사용자
                       지적: 「완전 검정으로 만들면 원의 버튼 자체가 안 보이니까」).
                       둘 다 완전 검정이면 **원이 면에 녹아** 스위치가 빈 알약
                       하나로 보인다. 원만 완전 검정이고 **면은 80%** 라, 판의
                       밝기가 20% 비쳐 원의 자리가 드러난다.

                       🔴 **「80% 검정」을 알파가 아니라 명도로 잡는다**
                       (2026-09-22 재정정). 처음엔 `검정 * 알파 0.8` 로 했는데,
                       판(`#2E2E2E`)이 20%만 비쳐 **`#090909`** 가 됐다 —
                       순검정 원과 차이가 **9/255** 라 사용자가 「아직도 완전
                       검정이야. 원이 안 보여」로 잡았다. 흰색에서 검정 쪽으로
                       80% 간 **`#333333`** 이면 원(`#000000`)과 확실히 갈린다.

                       ⚠️ **알파로 돌아가지 말 것** — 뒤가 어두우면 어떤 알파를
                       줘도 순검정에 붙는다. 이건 **불투명 명도**여야 한다.

                       🔴 **테두리도 남긴다** — 면이 어두워서 그것마저 없으면
                       스위치가 어디 있는지 안 보인다. */
                    inactiveThumbColor: _kBg,
                    inactiveTrackColor: const Color(0xFF333333),
                    trackOutlineColor: WidgetStateProperty.resolveWith(
                      (states) => states.contains(WidgetState.selected)
                          ? Colors.transparent
                          : _kOn.withValues(alpha: 0.35),
                    ),
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
              ),
            ],
          ),
          const SizedBox(height: 8),
          /* 🔴 **세로로 쌓는다** — 한 줄에 두면 「회원 탈퇴」가 반쪽 폭에서
             잘린다. 자주 쓰는 로그아웃이 위, **되돌릴 수 없는 탈퇴가 아래**다.

             🔴 **흰 면에 빨간 글자다**(2026-09-22 정정, 사용자 요청:
             「로그아웃 버튼은 흰색으로, 글자를 회원탈퇴 버튼의 똑같은
             빨간색으로」). 빨강은 아래 탈퇴 단추와 **같은 [_kDanger]** 이고,
             둘은 **면과 글자가 서로 뒤집힌 한 쌍**이 된다.

             ⚠️ **앞서 여기 적어 둔 「로그아웃은 안 빨갛다 — 같은 칸에서 빨강을
             나눠 쓰면 탈퇴의 빨강이 경고로 안 읽힌다」를 사용자가 뒤집었다.**
             그 판단을 되살리지 말 것. */
          FilledButton(
            key: const Key('profile-logout'),
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).logout(),
            style: FilledButton.styleFrom(
              backgroundColor: _kOn,
              foregroundColor: _kDanger,
              visualDensity: VisualDensity.compact,
            ),
            child: const Text('로그아웃', style: TextStyle(fontSize: 12)),
          ),
          // 🔴 **좁혔다**(2026-09-22, 사용자 요청: 「너무 멀다」). 6 → 3.
          //    둘은 한 묶음(계정에서 나가는 길)이라 붙어 있는 편이 맞다.
          const SizedBox(height: 3),
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
