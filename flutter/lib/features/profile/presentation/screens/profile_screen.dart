import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../auth/data/models/app_user.dart';
import '../../../auth/data/models/team_membership.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../card/data/card_providers.dart';
import '../../../card/data/models/player_card.dart';
import '../../../../core/widgets/glass_pill.dart';
import '../../../../core/widgets/screen_tint.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../card/presentation/card_editor_screen.dart';
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
    /* 🔴 **`AsyncValue` 를 통째로 들고 간다 — `.value` 로 납작하게 만들지
       않는다**(2026-09-23). `.value` 는 **오류일 때도 로딩 중에도 `null`**
       이라, 「못 읽었다」와 「아직 안 만들었다」가 화면에서 **같은 그림**이
       된다. 그 자리에 뜨는 것이 「카드 만들기」라 **멀쩡한 카드가 있는데도
       새로 만들려 하게** 된다(지킴이: `profile_card_error_test.dart`).

       ⚠️ 아래 바탕색은 `.value` 를 써도 된다 — 못 읽으면 브랜드 민트로
       물러날 뿐이고, 사용자가 잘못 누를 것이 없다. */
    final cardAsync = ref.watch(myCardProvider);
    final card = cardAsync.value;

    /* 🔴 **배경이 내 카드의 색을 따른다**(2026-09-22, 사용자 요청). 홈의
       빛무리와 같은 그림인데 색만 **카드 바탕색 + 자국색** 둘로 갈아 끼운다.
       카드가 없으면 브랜드 민트 그대로다 — 「빈 카드」인데 배경만 요란하면
       무엇을 보는 화면인지 흐려진다.

       🔴 **카드 색을 고치고 돌아오면 부드럽게 건너간다** — 툭 갈리면 화면이
       깜빡인 것처럼 보인다(`AnimatedAuroraBackground`). */
    /// 카드가 없으면 브랜드 민트 한 쌍 — 「빈 카드」인데 배경만 요란하면
    /// 무엇을 보는 화면인지 흐려진다.
    const fallback = (a: Color(0xFF2EC4B6), b: Color(0xFF118AB2));
    final tint = card?.style == null
        ? fallback
        : (a: card!.style!.bg, b: card.style!.brushColor);

    /* 🔴 **홈과 같은 바탕이다**(2026-09-22 사용자 요청: 「내 프로필 화면에서도
       그냥 배경 전체로 은은하게 색상 퍼지는거 홈페이지랑 똑같이」).
       전에는 `AnimatedAuroraBackground`(빛무리)였다 — 두 화면의 바탕이 갈려
       오갈 때 재질이 바뀌었다. */
    return Stack(
      children: [
        Positioned.fill(
          child: ScreenTint(a: tint.a, b: tint.b),
        ),
        Scaffold(
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
              /* 🔴 **자식마다 붙는 `RepaintBoundary` 를 끈다** (2026-09-23,
                 사용자가 다섯 번 짚은 **그 직선**의 진짜 원인).

                 [ListView] 는 기본으로 **자식 하나하나를 `RepaintBoundary`
                 로 감싼다.** 그러면 그 자식이 **제 층에 따로 그려지고**,
                 층의 크기가 정수 픽셀이 아니면 스크롤로 옮겨 붙일 때
                 **오른쪽·아래 가장자리 한 줄이 비친다.** 카드 높이는
                 `폭 × 비율` 이라 정수일 수가 없다.

                 ⚠️ **`player_card_view.dart` 가 같은 증상을 적어 두고도 못
                 찾은 자리다.** 거기서는 **직접 넣은** `RepaintBoundary` 를
                 빼고 「해결」로 봤는데, 목록이 **자동으로 하나 더** 붙이고
                 있었다. 그래서 빼도 증상이 그대로였다.

                 ⚠️ **대가**: 한 칸이 다시 그려질 때 목록 전체가 같이 다시
                 그려진다. 이 화면은 칸이 예닐곱 개뿐이라 괜찮다 — 칸이 수십
                 개가 되면 그때 다시 본다. */
              addRepaintBoundaries: false,
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
                _CardHero(cardAsync: cardAsync, nickname: user.nickname),
                /* 🔴 **닉네임과 판 사이를 흰 선으로 가른다**(2026-09-22, 사용자
                 요청: 「닉네임과 내 영상 판 가운데에 완전 흰색 선으로」).
                 위아래 여백을 같게 줘서 선이 **둘의 한가운데**에 선다. */
                const SizedBox(height: 14),
                const _Rule(),
                const SizedBox(height: 14),
                const _VideosBlock(),
                /* 🔴 **두 번째 흰 선**(2026-09-22 사용자 요청: 「내 분석/업로드
                 영상 바로 아래에도 … 똑같이 거리 재서」). 위 선과 **같은
                 여백(14)** 을 위아래로 둬서 선이 두 판의 한가운데에 선다.

                 ⚠️ **`_kGap`(6)이 아니다.** 판끼리의 간격과 선을 두르는
                 여백은 **다른 값**이다 — `_kGap` 으로 두면 선이 위 판에
                 붙어 「판의 밑줄」처럼 보인다. 위 선과 같은 14 라야 둘이
                 한 쌍으로 읽힌다. */
                const SizedBox(height: 14),
                const _Rule(),
                const SizedBox(height: 14),
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
      ],
    );
  }
}

/* ⛔ **`_kBg`(순검정)를 지웠다**(2026-09-22) — 바탕을 [ScreenTint] 가
   칠하고, 그 바탕은 이제 **흰색**이다. 되살리려면 이 화면의 `Stack` 첫
   자식을 바꾼다. */
///
/// 🔴 전에는 `kAuroraBase`(#141417)를 그대로 썼고 판이 그 위에 **반투명
/// 흰 면**으로 떴다. 이제는 **바탕이 검정, 판이 `kAuroraBase`** 다 — 둘이
/// 자리를 맞바꾼 셈이라 테두리 없이도 판의 경계가 선다(아래 [_Block]).
///
/// ⚠️ 홈은 여전히 `kAuroraBase` 다. 두 화면의 바탕이 갈린 것은 **일부러**이고,
/// 되돌리려면 이 한 줄이다.
const Color _kOn = Color(0xFFFFFFFF);
const Color _kOnPanel = Color(0xFF000000);

/// 흰 판 **안쪽**의 글자·아이콘·테두리 색 — **완전한 검정**이다
/// (2026-09-22 사용자 요청: 「판들의 전체 색상 완전 흰색으로 바꾸고, 글자들이나
/// 버튼 흰색으로 겹치면 완전 검정으로」).
///
/// 🔴 **[_kOn] 과 짝이다.** 검은 바탕 위(카드 · 닉네임 · 흰 선 · 「내 영상」
/// 사진 판)는 [_kOn](흰색), **흰 판 안쪽**은 이것이다. 새로 글자를 놓을 때
/// **어느 바탕 위인지**를 보고 고른다 — 습관대로 [_kOn] 을 쓰면 흰 판에서
/// 글자가 통째로 사라진다.

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
  ///
  /// 🔴 **[_VideosBlock] 이 같이 쓴다**(2026-09-22) — 그 판이 이 선 둘 사이에
  /// 끼어 있어서 **폭이 다르면 셋이 층층이 어긋나 보인다.** 그래서 값을
  /// 베껴 적지 않고 여기 하나를 나눠 쓴다.
  static const double widthFactor = 2 / 3;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 1 / MediaQuery.devicePixelRatioOf(context),
      child: const FractionallySizedBox(
        widthFactor: widthFactor,
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

       🔴 **면이 순백이다**(2026-09-22 정정, 사용자 요청: 「소속 정보 내 경기
       계정 판들의 전체 색상 완전 흰색으로」). 전에는 [kSurfaceWhite](흰색
       18%)라 검은 바탕이 비쳐 **회색 판**이었다.

       🔴 **그래서 판 안쪽 글자는 전부 [_kOnPanel](검정)이다** — 면만 희게
       하고 글자를 두면 **통째로 사라진다.**

       ⚠️ **하단 바 · 로고 알약과 더는 같은 값이 아니다.** 셋이 한 재질이던
       것을 이 판만 뗀 것이고, 그쪽은 [kSurfaceWhite] 그대로다. */
    return DecoratedBox(
      decoration: BoxDecoration(
        color: _kOn,
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
                color: _kOnPanel,
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
  const _CardHero({required this.cardAsync, required this.nickname});

  /// 🔴 **`PlayerCard?` 가 아니라 `AsyncValue` 다**(2026-09-23). 아래
  /// [_cardAction] 이 「없다」와 「못 읽었다」를 갈라야 하는데, `null` 하나로는
  /// 갈 수가 없다 — 그 둘을 같게 그린 것이 이 화면의 결함이었다.
  final AsyncValue<PlayerCard?> cardAsync;
  final String nickname;

  PlayerCard? get card => cardAsync.value;

  static const double _cardWidth = 200;

  /// 카드와 오른쪽 칸 사이.
  static const double _gap = 12;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    /* 🔴 **카드가 왼쪽, 나머지가 그 오른쪽이다**(2026-09-22 사용자 요청:
       「카드는 왼쪽으로 옮기고 닉네임이랑 닉네임 편집은 그 카드의 바로 오른쪽
       위에, 카드 수정 버튼은 그 바로 아래에」).

       ⚠️ **가운데 세로 쌓기였던 것을 통째로 갈았다.** 전에는 카드가 가운데
       서고 그 아래에 닉네임 줄이 있었다 — 그때 있던 장치 둘이 **이제 필요
       없어져서 같이 걷혔다**:

       | 걷은 것 | 왜 있었나 |
       |---|---|
       | 닉네임 왼쪽의 빈 자리 34 | 오른쪽 연필만큼 **균형**을 맞추려던 것. 이제 왼쪽 맞춤이라 균형을 맞출 일이 없다 |
       | 「카드 수정」의 `left` 좌표 계산 | 카드가 **가운데** 서니 그 오른쪽 틈을 좌표로 잡아야 했다. 이제 `Row` 가 자리를 잡는다 |

       🔴 **[CrossAxisAlignment.start] 다** — 오른쪽 칸이 카드보다 짧으므로
       가운데로 두면 닉네임이 카드 한가운데 높이로 내려앉는다. 「카드 바로
       오른쪽 **위**」가 요청이다. */
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
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
        const SizedBox(width: _gap),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // 닉네임 + 연필 — 카드 **오른쪽 위**.
              Row(
                children: [
                  Flexible(
                    child: Text(
                      nickname,
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
              const SizedBox(height: 10),
              /* 🔴 **글귀가 「프로필 카드 수정」이다**(2026-09-22 사용자 요청).
                 「카드 수정」만으로는 **무슨 카드**인지 안 읽혔다 — 이 화면엔
                 카드가 하나뿐이지만 다른 화면에서 오면 그렇지 않다.
                 ⚠️ 카드가 없을 때의 글귀(「카드 만들기」)는 **안 바꿨다** —
                 그쪽은 「만든다」가 이미 무엇인지 말한다. */
              _cardAction(context, ref),
            ],
          ),
        ),
      ],
    );
  }

  /* 🔴 **카드의 네 가지 상태를 각각 다르게 그린다**(2026-09-23).

     | 상태 | 단추 | 왜 |
     |---|---|---|
     | 못 읽음 | **다시 시도** | 🔴 **여기서 「만들기」를 내밀면 안 된다** — 서버에 카드가 멀쩡히 있는데 읽기만 실패한 것일 수 있다 |
     | 읽는 중 | 「불러오는 중」(안 눌림) | 느린 망에서 「만들기」가 **한 번 깜빡이고** 바뀌던 자리다. 그 순간에 눌리면 위와 같은 일이 난다 |
     | 없음 | 카드 만들기 | 진짜로 아직 안 만든 것 |
     | 있음 | 프로필 카드 수정 | |

     ⚠️ **「없음」쪽을 같이 막지 않는다** — 오류를 가리려다 이쪽까지 막으면
     카드를 **처음 만들 길이 사라진다**(지킴이 네 번째 시험). */
  Widget _cardAction(BuildContext context, WidgetRef ref) {
    /* 🔴 **`hasError` 를 `isLoading` 보다 먼저 본다.** 「다시 시도」를 누르면
       Riverpod 이 **앞선 오류를 달고 있는 로딩**으로 가는데, 그때 로딩을
       먼저 보면 단추가 「불러오는 중」으로 갈렸다가 실패하면 다시 돌아온다 —
       누른 사람 눈에는 단추가 춤을 춘다. */
    if (cardAsync.hasError) {
      return _GlassButton(
        buttonKey: const Key('profile-card-retry'),
        label: '불러오지 못했습니다 · 다시 시도',
        onTap: () => ref.invalidate(myCardProvider),
      );
    }
    if (!cardAsync.hasValue) {
      return const _GlassButton.disabled(label: '불러오는 중…');
    }
    final card = this.card;
    return _GlassButton(
      buttonKey: const Key('profile-card-edit'),
      label: card == null ? '카드 만들기' : '프로필 카드 수정',
      onTap: () => card == null
          ? _createCard(context, ref)
          : Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => CardEditorScreen(card: card),
              ),
            ),
    );
  }

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

  /// 눌리지 않는 같은 모양 — 「불러오는 중」처럼 **자리는 지키되 누를 수는
  /// 없어야 하는** 상태에 쓴다. 자리를 안 지키면 값이 도착할 때 옆 글자가
  /// 통째로 밀린다.
  const _GlassButton.disabled({required this.label})
    : buttonKey = const Key('profile-card-loading'),
      onTap = null;

  final Key buttonKey;
  final String label;
  final VoidCallback? onTap;

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
            const Text('아직 팀이 없습니다', style: TextStyle(color: _kOnPanel))
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
                        color: _kOnPanel,
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
                            color: _kOnPanel.withValues(alpha: 0.7),
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
                foregroundColor: _kOnPanel,
                side: BorderSide(color: _kOnPanel.withValues(alpha: 0.4)),
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
            style: TextButton.styleFrom(foregroundColor: _kOnPanel),
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
    /* ⚠️ **여기는 `.value` 로 둔다**(2026-09-23, 위 `_cardAction` 과 함께
       조사한 결과). 못 읽으면 호칭 칸이 **비고 고치기 알약도 안 뜬다**
       (`_TitlesRow` 가 `card != null` 일 때만 그린다) — 누를 것이 없으니
       잘못 누를 것도 없다. 같은 화면 위쪽의 카드 단추가 이미 「불러오지
       못했습니다」를 말하고 있어서, 여기서 한 번 더 말하면 오류 문구가
       한 화면에 둘이 된다. */
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
            style: const TextStyle(color: _kOnPanel, fontSize: 13),
          ),
          const SizedBox(height: 10),
          _label('함께한 날'),
          const SizedBox(height: 2),
          Text(joined, style: const TextStyle(color: _kOnPanel, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _label(String text) => Text(
    text,
    style: TextStyle(color: _kOnPanel.withValues(alpha: 0.7), fontSize: 12),
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
    final ink = danger ? _kDanger : _kOnPanel.withValues(alpha: 0.85);
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
                  side: BorderSide(color: _kOnPanel.withValues(alpha: 0.3)),
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
                        color: _kOnPanel.withValues(alpha: 0.85),
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
    /* ⚠️ **좌우를 흰 선 길이로 좁혔다가 되돌렸다**(2026-09-22, 같은 날 두
       번). 「선 길이만큼 줄이고」였는데 다시 「양옆 화면 끝과 6픽셀만 두자」로
       정정됐다 — 지금은 목록의 좌우 여백(`_kEdge` = 6)이 곧 이 판의 폭이다.
       `_Rule.widthFactor` 와 **더는 엮이지 않는다.** */
    /* ⛔ **판 테두리의 도는 실버(`SilverSweepBorder`)를 걷었다**(2026-09-22
       사용자 요청: 「지금 판 전체에 도는거 하지 마. 외곽선도 주지 말고」).

       붙였던 까닭은 「이 판이 다른 화면으로 밀고 들어가는 유일한 입구라
       여기를 보라는 표시」였다. 🔴 **그 일을 이제 가운데 알약이 한다** —
       누르는 자리가 알약 하나로 좁아졌으니 판 둘레가 도는 것은 **어디를
       눌러야 하는지를 도로 흐린다.**

       🔴 **테두리 자체가 없다** — 가만히 있는 선도 안 긋는다. 사진이 판의
       모양을 그대로 보여 준다. */
    return ClipRRect(
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
            /* 🔴 **판 한가운데다**(2026-09-22 재정정, 사용자 요청: 「글자를
                 그 판의 정중앙으로」).

                 ⚠️ **왼쪽 위 구석으로 옮겼던 것을 되돌린 것이다.** 그때
                 까닭은 「사진이 주인공이고 글자는 이름표다」였는데, 판을
                 좁히면서 구석에 붙은 글자가 **판 폭을 거의 다 먹어** 이름표로
                 안 읽혔다.

                 ⚠️ 위 그라데이션은 **위가 짙은** 채로 뒀다 — 가운데로 오면서
                 글자가 짙은 쪽과 옅은 쪽 사이에 걸치는데, 아래를 더 짙게
                 뒤집으면 사진의 인물이 어두워진다. */
            /* 🔴 **가운데 유리 알약 하나만 눌린다**(2026-09-22 정정, 사용자
               요청: 「판 자체에 버튼을 주지 말고 … 글자에 컴팩트하게 버튼을
               주라고, 홈페이지 스쿼드판 안의 「위로 올려 내 팀 만들기」처럼」).

               ⚠️ **판 전체가 단추였던 것을 걷었다.** 판까지 눌리면 **어디를
               눌러야 하는지**가 흐려진다.

               🔴 **재질·크기가 홈의 「위로 올려 내 팀 만들기」와 같다**
               ([GlassPill]) — 값이 한곳에 있어서 한쪽만 갈릴 일이 없다.
               도는 실버 테두리는 안 붙인다(사용자: 「외곽선 돌아가는건
               안해도 돼」). */
            Center(
              child: GlassPill(
                key: const Key('profile-videos'),
                /* 🔴 **흐림을 끈다** — 이 판은 **굴러가는 목록 안**에 있다
                   (2026-09-22, 사용자 지적: 「스크롤 하면 또또또 카드 외곽에
                   직선이 생겨」). 흐림은 뒤가 구르면 가장자리에 **흰 직선**을
                   만든다 — [GlassPill.blur] 머리말 참고. 홈의 알약들은 뒤가
                   움직이지 않는 사진이라 켜 둔 것이고, 여기는 다르다. */
                blur: false,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => const MyVideosScreen(),
                  ),
                ),
                child: const Text(
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
          ],
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
      child: Text('다가오는 경기가 없습니다.', style: TextStyle(color: _kOnPanel)),
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
                    color: _kOnPanel.withValues(alpha: 0.85),
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
                    /* 🔴 **켜짐과 꺼짐의 밝기가 맞바뀌었다**(2026-09-22
                       정정 — 판이 순백이 되면서).

                       전에는 판이 어두워서 **켜짐이 흰색**이었다. 판이
                       희어진 지금 그대로 두면 **켜짐이 판에 녹아** 스위치가
                       빈 자리로 보인다.

                       🔴 **둘 다 검정으로 칠하지 않는다** — 요청은 「흰색으로
                       겹치면 검정으로」지만 켜짐·꺼짐을 **둘 다** 검정으로
                       하면 **어느 쪽인지 알 수 없다.** 그래서 자리를
                       맞바꿨다: 켜짐이 어둡고 꺼짐이 밝다.

                       ⚠️ 아래 꺼짐 색 주석의 「#333333 vs 순검정」 계산은
                       **어두운 판 시절의 것**이라 지금은 적용되지 않는다. */
                    activeThumbColor: _kOn,
                    activeTrackColor: _kOnPanel,
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
                    inactiveThumbColor: _kOnPanel,
                    // 흰 판에서 **한 끗 어두운** 회색 — 순백이면 자리가 안 보인다.
                    inactiveTrackColor: const Color(0xFFE2E2E2),
                    trackOutlineColor: WidgetStateProperty.resolveWith(
                      (states) => states.contains(WidgetState.selected)
                          ? Colors.transparent
                          : _kOnPanel.withValues(alpha: 0.35),
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
              backgroundColor: _kOnPanel,
              /* 🔴 **순백이다**(2026-09-22 정정, 사용자 요청: 「로그아웃 글자
                 색상 빨간색에서 완전 흰색으로」).

                 ⚠️ **앞서 「탈퇴와 같은 빨강을 쓴다 — 둘은 면과 글자가 서로
                 뒤집힌 한 쌍」이라고 적어 둔 것을 사용자가 다시 뒤집었다.**
                 판이 순백이 되면서 단추 면이 검정이 됐고, 그 위의 빨강은
                 「되돌릴 수 없는 일」로 읽히는데 로그아웃은 그렇지 않다. */
              foregroundColor: _kOn,
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
