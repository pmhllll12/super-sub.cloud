import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:video_player/video_player.dart';

import '../../../../core/widgets/glass_pill.dart';
import '../../../card/data/models/player_card.dart';
import '../../../card/presentation/mate_cards_controller.dart';
import '../../../profile/presentation/widgets/player_card_view.dart';
import '../../data/models/public_video.dart';
import '../../data/video_providers.dart';

/// 공개 영상 **전체화면 보기** (2026-09-24 사용자 요청 + 레퍼런스).
///
/// 홈 영상 줄에서 가운데 카드를 누르면 여기로 온다. 전에는 `/videos`(영상
/// **분석** 화면)로 갔는데, **어떤 영상을 눌렀는지가 전혀 전달되지 않았다.**
///
/// 🔴 **위아래로 넘기면 공개 영상 전체를 돈다**(사용자 결정). 누른 영상에서
/// 시작한다.
///
/// 🔴 **레퍼런스에서 일부러 뺀 것들 — 되살리지 말 것**(사용자 지시):
/// - **북마크·공유** 단추 (오른쪽 줄에는 좋아요·댓글 **둘만**)
/// - **캡션 두 줄**과 **음악 알약**
/// - 주인 자리의 **Follow 단추** — 카드와 닉네임만 남긴다
/// - 오른쪽 위 **카메라** 단추 — 그 자리에 해당하는 기능이 이 앱엔 없다
class ReelsScreen extends ConsumerStatefulWidget {
  const ReelsScreen({super.key, required this.videoId});

  /// 어느 영상에서 시작하는가. 🔴 **목록에서 이 id 를 찾아 그 자리로 연다** —
  /// 서버에 `GET /videos/{id}`(단건 조회)가 **없어서** 목록에서 찾는다.
  final String videoId;

  @override
  ConsumerState<ReelsScreen> createState() => _ReelsScreenState();
}

class _ReelsScreenState extends ConsumerState<ReelsScreen> {
  /* 🔴 **목록이 온 뒤에 한 번만 만든다.** [PageController.initialPage] 는
     만들 때만 먹으므로, 목록이 오기 전에 만들면 시작 자리를 못 준다. */
  PageController? _pager;
  int _index = 0;

  /// 목록에 그 영상이 없어서 물러나는 중 — 두 번 부르지 않게 한다.
  bool _leaving = false;

  /* 🔴 **좋아요·댓글은 가짜다 — 이 화면 안에서만 산다.**
     계약(`fastapi/docs/api-contract.md`)에 좋아요·댓글이 **아예 없다**(테이블도
     라우터도 없다). 웹도 같은 방식으로 시늉만 내고 있다
     (`www/src/components/HomeFeed.tsx` 의 `liked`·`wrote` 상태).

     ⚠️ **나가면 사라진다. 아무 데도 안 보낸다.** 계약이 열리면 이 둘을 지우고
     응답을 흘려 넣으면 된다 — 미결 `paik` 항목에 올려 두었다.

     🔴 **지어낸 큰 수(45.2k 같은)를 쓰지 않는다.** 시연에서 그 수를 묻는
     사람이 생기고, 그때 「가짜입니다」라고 답하게 된다. 0 에서 시작한다. */
  final Set<String> _liked = {};
  final Map<String, List<String>> _comments = {};

  /// 댓글 칸을 펼쳤는가 — 오른쪽 말풍선으로 여닫는다.
  bool _showComments = false;

  final TextEditingController _draft = TextEditingController();
  final FocusNode _draftFocus = FocusNode();

  @override
  void dispose() {
    _pager?.dispose();
    _draft.dispose();
    _draftFocus.dispose();
    super.dispose();
  }

  /// 목록이 온 뒤 딱 한 번 — 시작 자리를 정하고 쪽 넘김을 세운다.
  ///
  /// 🔴 **가운데쯤에서 시작한다** — 아래 [_kLoopBase] 의 까닭.
  void _ensurePager(List<PublicVideo> videos) {
    if (_pager != null) return;
    final start = videos.indexWhere((v) => v.id == widget.videoId);
    _index = _kLoopBase * videos.length + (start < 0 ? 0 : start);
    _pager = PageController(initialPage: _index);
    _wantCard(videos, _index);
  }

  /// 그 자리의 영상 — 🔴 **나머지로 고른다. 여기가 「끝없이」의 전부다**
  /// (홈 영상 줄과 같은 수법이다).
  PublicVideo _videoAt(List<PublicVideo> videos, int i) =>
      videos[i % videos.length];

  /// 🔴 **옆 쪽의 재생 주소를 미리 받아 둔다** (2026-09-24). 주소 받기는
  /// 네트워크 왕복이라, 넘긴 **뒤에** 받기 시작하면 그동안 포스터만 보인다.
  ///
  /// ⚠️ **주소만 미리 받고 재생기는 안 연다** — 여는 것은 여전히 지금 쪽
  /// 하나뿐이다(안드로이드 디코더 수). 🔴 **목록 전체를 미리 받지 말 것**:
  /// 사전 서명 주소는 900초 뒤 만료라 뒤쪽 것은 볼 때쯤 이미 죽어 있다
  /// (`video_providers.dart` 의 `playbackUrlProvider` 머리말).
  void _warmNeighbours(List<PublicVideo> videos, int i) {
    for (final n in [i - 1, i + 1]) {
      if (n < 0) continue;
      final id = _videoAt(videos, n).id;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) ref.read(playbackUrlProvider(id));
      });
    }
  }

  /// 그 자리 주인의 카드를 받아 둔다 — 🔴 **보이는 것만**(`mateCardsProvider`
  /// 의 규칙 그대로). 목록 전체의 카드를 한꺼번에 부르면 요청이 영상 수만큼 나간다.
  void _wantCard(List<PublicVideo> videos, int i) {
    if (i < 0 || videos.isEmpty) return;
    final slug = _videoAt(videos, i).uploaderCardSlug;
    if (slug == null || slug.isEmpty) return;
    /* 🔴 **`build` 중에 provider 를 고치지 않는다** — 그리는 도중에 상태를
       바꾸면 Flutter 가 그 프레임을 버리고 다시 짓는다. */
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) ref.read(mateCardsProvider.notifier).want([slug]);
    });
  }

  void _send(String videoId) {
    final text = _draft.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _comments.putIfAbsent(videoId, () => []).add(text);
      _draft.clear();
    });
    _draftFocus.unfocus();
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(publicVideosProvider);
    final videos = async.value ?? const <PublicVideo>[];

    /* 🔴 **목록이 비었거나 그 영상이 사라졌으면 물러난다.** 엉뚱한 영상을
       말없이 보여 주는 것보다 낫다 — 누른 것과 다른 것이 뜨면 버그로 읽힌다. */
    if (async.hasValue &&
        !_leaving &&
        (videos.isEmpty ||
            videos.indexWhere((v) => v.id == widget.videoId) < 0)) {
      _leaving = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && context.canPop()) context.pop();
      });
    }

    if (videos.isNotEmpty) _ensurePager(videos);
    final pager = _pager;

    /* 🔴 **상태 바 글자를 밝게** — 화면이 통째로 영상이라 어둡다.
       `ScreenTint` 는 바탕색으로 스스로 정하는데 여기엔 그 위젯이 없다. */
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: Scaffold(
        backgroundColor: Colors.black,
        /* 🔴 **입력줄이 키보드를 피해 올라온다.** 기본값(true)에 기대면
           전체화면 영상까지 같이 밀려 위가 잘린다 — 영상은 그대로 두고
           아래 겹침만 [MediaQuery.viewInsetsOf] 로 띄운다. */
        resizeToAvoidBottomInset: false,
        body: pager == null
            ? const Center(
                child: CircularProgressIndicator(color: Colors.white24),
              )
            : Stack(
                fit: StackFit.expand,
                children: [
                  PageView.builder(
                    /* 🔴 **여기서는 [PageView] 가 맞다.** 홈 영상 줄의
                       「[PageView] 금지」는 **카드가 겹칠 때 가운데가 맨 위로
                       안 온다**는 이유였다(`home_video_strip.dart` 머리말).
                       이 화면은 한 번에 한 장이고 겹치지 않는다. */
                    scrollDirection: Axis.vertical,
                    controller: pager,
                    /* 🔴 **끝이 없다** (2026-09-24 사용자 요청: 「영상 다 내리면
                       끝이 아니라, 올라온 영상들 계속 나오게」). `itemCount` 를
                       안 주면 쪽이 무한히 이어지고, 어느 영상인지는 **나머지**로
                       정한다([_videoAt]) — 홈 영상 줄과 같은 수법이다. */
                    itemCount: null,
                    onPageChanged: (i) {
                      setState(() => _index = i);
                      _wantCard(videos, i);
                      _warmNeighbours(videos, i);
                    },
                    itemBuilder: (context, i) => _ReelPage(
                      /* 🔴 **열쇠를 자리(`i`)로 준다.** 영상 id 로 주면 같은
                         영상이 여러 자리에 서는 「끝없이」에서 **한 열쇠가 여러
                         쪽**이 되어 상태가 엉킨다. */
                      key: ValueKey(i),
                      video: _videoAt(videos, i),
                      /* 🔴 **재생기는 지금 쪽 하나만 연다.** 안드로이드는 동시에
                         열 수 있는 디코더가 몇 개 안 되고, 넘긴 만큼 쌓아 두면
                         몇 편 뒤부터 **아무것도 안 열린다**(홈 영상 줄이 같은
                         데서 데였다). 나머지 쪽은 포스터만 그린다. */
                      open: i == _index,
                    ),
                  ),
                  _overlay(_videoAt(videos, _index)),
                ],
              ),
      ),
    );
  }

  Widget _overlay(PublicVideo video) {
    final liked = _liked.contains(video.id);
    final comments = _comments[video.id]?.length ?? 0;
    return SafeArea(
      child: Stack(
        children: [
          Positioned(top: 8, left: 12, child: _backButton()),
          Positioned(
            right: 12,
            /* 🔴 **보내기 단추 바로 위다** (2026-09-24 사용자 요청: 「하트랑
               댓글 보는 버튼 2개 더 아래로 내리자. 전송 버튼 위로 오게 해줘」).
               132 → 64 — 보내기(아래에서 8, 높이 46 → 윗변 54)에서 10 띄운 값이다.
               ⚠️ 보내기 단추 크기를 바꾸면 이 값도 같이 본다. */
            bottom: 64,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _RailButton(
                  key: const Key('reel-like'),
                  /* 🔴 **속이 찬 하트다**(2026-09-24 레퍼런스). 빈 하트였는데
                     사용자가 레퍼런스를 다시 보냈다 — 눌렀는지는 **색**으로
                     가른다(흰색 ↔ 분홍), 모양이 아니라. */
                  icon: Icons.favorite,
                  label: '${liked ? _kLikeBase + 1 : _kLikeBase}',
                  tint: liked ? const Color(0xFFFF4D67) : Colors.white,
                  onTap: () => setState(() {
                    if (liked) {
                      _liked.remove(video.id);
                    } else {
                      _liked.add(video.id);
                    }
                  }),
                ),
                const SizedBox(height: 18),
                _RailButton(
                  key: const Key('reel-comment'),
                  // 🔴 말풍선(레퍼런스) — 네모 말풍선이 아니라 **둥근** 것이다.
                  icon: Symbols.chat_bubble,
                  label: '$comments',
                  /* 🔴 **누르면 쓴 댓글이 보인다**(2026-09-24 사용자 지적:
                     「댓글 썼으면 댓글 아이콘 누르면 보여야지」). 전에는 아래
                     입력줄로 **초점만** 옮겼다 — 쓴 것을 다시 볼 길이 없었다. */
                  onTap: () => setState(() => _showComments = !_showComments),
                ),
              ],
            ),
          ),
          /* 🔴 **댓글 칸이 펼쳐지면 주인 줄을 가린다** — 둘이 같은 자리를 놓고
             다투면 좁은 폰에서 겹친다. 댓글을 보는 동안 주인은 잠깐 없어도 된다. */
          if (!_showComments)
            Positioned(left: 16, right: 92, bottom: 86, child: _owner(video))
          else
            /* 🔴 **오른쪽 줄을 피해서 선다** (2026-09-24). 하트·말풍선이 보내기
               바로 위로 내려오면서 이 판과 **같은 높이**가 됐다 — 폭을 끝까지
               주면 단추 둘이 판에 덮여 다시 접을 수가 없다. */
            Positioned(left: 12, right: 76, bottom: 78, child: _commentList(video)),
          Positioned(left: 12, right: 12, bottom: 8, child: _composer(video)),
        ],
      ),
    );
  }

  /// 🔴 **[Scaffold] 의 머리칸이 없다** — 화면이 통째로 영상이라 띠를 얹을 수
  /// 없다. 그래서 `tester.pageBack()`(머리칸의 뒤로가기를 찾는다)은 **여기에
  /// 안 걸린다.** 시험은 이 키로 누른다.
  Widget _backButton() => _RoundTapTarget(
    key: const Key('reel-back'),
    onTap: () => context.canPop() ? context.pop() : context.go('/home'),
    child: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 18),
  );

  /// 주인 — 🔴 **작은 카드와 닉네임뿐이다**(사용자 지시: Follow 단추 없음).
  ///
  /// 🔴 **부드럽게 갈린다** (2026-09-24 사용자 지적: 「영상 바뀔때, 카드랑
  /// 닉네임 바뀌는거, 지금 부자연스러우니까」). 전에는 쪽을 넘기는 순간 글자와
  /// 그림이 **툭 갈아 끼워졌다** — 영상은 부드럽게 미끄러지는데 이 줄만 튀었다.
  ///
  /// 🔴 **갈리는 계기가 둘이다** — ⑴ 쪽을 넘겨 **영상이 바뀔 때** ⑵ 그 주인의
  /// 카드가 **뒤늦게 도착할 때**(`mateCardsProvider` 는 비동기다). 둘 다
  /// 잡으려고 열쇠에 **영상 id 와 「카드가 왔는가」를 함께** 넣는다 — id 만
  /// 넣으면 카드가 도착하는 순간이 또 툭 튄다.
  Widget _owner(PublicVideo video) {
    final slug = video.uploaderCardSlug;
    final card = slug == null ? null : ref.watch(mateCardsProvider)[slug];
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 260),
      /* 🔴 **나가는 것과 들어오는 것을 **겹치지 않게** 쌓는다.** 기본값은 둘을
         같은 자리에 겹쳐 놓는데, 카드 그림이 서로 비쳐 **두 장이 겹친 한순간**
         이 보인다. 나가는 것을 먼저 지우고 들어오는 것만 남긴다. */
      layoutBuilder: (current, previous) => Stack(
        alignment: Alignment.centerLeft,
        children: [...previous, ?current],
      ),
      transitionBuilder: (child, anim) => FadeTransition(
        opacity: anim,
        // 살짝 아래에서 올라온다 — 그냥 켜지는 것보다 「바뀌었다」가 읽힌다.
        child: SlideTransition(
          position: Tween(
            begin: const Offset(0, 0.25),
            end: Offset.zero,
          ).animate(CurvedAnimation(parent: anim, curve: Curves.easeOutCubic)),
          child: child,
        ),
      ),
      child: _ownerRow(video, card),
    );
  }

  Widget _ownerRow(PublicVideo video, PlayerCard? card) {
    return Row(
      // 🔴 열쇠가 바뀌어야 [AnimatedSwitcher] 가 갈아 끼운다 — 위 머리말의 둘.
      key: ValueKey('${video.id}|${card != null}'),
      mainAxisSize: MainAxisSize.min,
      children: [
        /* 🔴 **카드가 없을 수 있다** — 카드를 한 번도 안 만든 사람이면 슬러그가
           아예 없고, 있어도 아직 안 온 동안이 있다. 그때는 닉네임만 남는다. */
        if (card != null)
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: PlayerCardView(
              width: _kOwnerCardW,
              seed: card.publicSlug,
              alias: aliasOf(card),
              style: card.style,
              photoUrl: card.photoUrl,
            ),
          )
        else
          const SizedBox(width: _kOwnerCardW),
        const SizedBox(width: 10),
        Flexible(
          child: Text(
            video.uploaderNickname ?? '',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              shadows: _kOverlayShadow,
            ),
          ),
        ),
      ],
    );
  }

  /// 이 영상에 쓴 댓글 — 🔴 **이 화면 안에서만 산다**(위 `_comments` 머리말).
  ///
  /// 🔴 **키보드가 올라오면 같이 올라간다** — 안 그러면 쓰는 동안 자기가 쓴
  /// 것이 키보드에 덮여 안 보인다.
  Widget _commentList(PublicVideo video) {
    final items = _comments[video.id] ?? const <String>[];
    final lift = MediaQuery.viewInsetsOf(context).bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: lift),
      // 🔴 입력줄·단추와 **같은 흰 유리**다 — 셋이 한 벌로 읽혀야 한다.
      child: _glass(
        radius: 18,
        child: Container(
          key: const Key('reel-comment-list'),
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.34,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: items.isEmpty
            ? const Text(
                '아직 댓글이 없습니다',
                style: TextStyle(color: Colors.white70, fontSize: 13),
              )
            : ListView.separated(
                shrinkWrap: true,
                reverse: true,
                itemCount: items.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                /* 🔴 **거꾸로 그린다**(`reverse`) — 방금 쓴 것이 아래(입력줄
                   가까이)에 오고, 길어지면 그 자리가 먼저 보인다. */
                itemBuilder: (context, i) => Text(
                  items[items.length - 1 - i],
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                ),
              ),
        ),
      ),
    );
  }

  Widget _composer(PublicVideo video) {
    // 키보드가 올라온 만큼만 띄운다 — 영상은 안 밀린다(위 주석).
    final lift = MediaQuery.viewInsetsOf(context).bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: lift),
      child: Row(
        children: [
          Expanded(
            /* 🔴 **테가 없다 — 흰 유리뿐이다** (2026-09-24 사용자 요청:
               「외곽선 그냥 없애고, 안쪽은 흰색 블러로만 처리하자」).
               ⛔ `border:` 를 되살리지 말 것. */
            child: _glass(
              radius: 26,
              child: Padding(
                padding: const EdgeInsets.only(left: 14, right: 18),
                child: Row(
                  children: [
                    /* 🔴 **알약 **안** 왼쪽에 웃는 얼굴**(2026-09-24 레퍼런스).
                       ⚠️ **아무 일도 안 한다** — 레퍼런스에서는 이모지 고르기
                       입구인데, 우리에겐 그 화면이 없다. 생기면 여기 붙인다. */
                    Icon(
                      Icons.emoji_emotions_outlined,
                      color: Colors.white.withValues(alpha: 0.85),
                      size: 22,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        key: const Key('reel-comment-field'),
                        controller: _draft,
                        focusNode: _draftFocus,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                        ),
                        cursorColor: Colors.white,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _send(video.id),
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(
                            vertical: 16,
                          ),
                          hintText: '댓글 달기...',
                          hintStyle: TextStyle(
                            color: Colors.white.withValues(alpha: 0.55),
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          _RoundTapTarget(
            key: const Key('reel-comment-send'),
            /* 🔴 **보내기만 무지개 동그라미다**(2026-09-24 레퍼런스). 화면에서
               **유일하게 색이 있는 자리**라 「여기를 누른다」가 한눈에 온다 —
               나머지는 전부 흰 아이콘에 검은 반투명이다.
               ⛔ 다른 단추에 이 그라데이션을 돌려 쓰지 말 것. */
            gradient: _kSendGradient,
            onTap: () => _send(video.id),
            child: const Icon(Symbols.send, color: Colors.white, size: 20),
          ),
        ],
      ),
    );
  }
}

/// 주인 카드의 폭 — 🔴 **작게**(사용자 지시). [PlayerCardView] 가 380 폭으로
/// 짜고 통째로 줄이므로 이 값만 주면 된다. 높이는 3:4.1 로 따라온다.
const double _kOwnerCardW = 44;

/// 좋아요 수의 **출발값** — 🔴 **0 이다.** 위 `_liked` 머리말의 까닭.
const int _kLikeBase = 0;

/// 끝없이 돌기 위해 **몇 바퀴 앞에서 시작하는가** (2026-09-24).
///
/// 🔴 **위로도 넘길 수 있어야 해서 필요하다.** [PageView] 는 자리가 0 아래로
/// 못 가므로, 0 에서 시작하면 **아래로만** 끝이 없고 위로는 곧 막힌다.
/// 1000 바퀴 앞에서 시작하면 양쪽 다 사람이 닿을 수 없는 거리가 된다.
///
/// ⚠️ **시작 자리가 커진다** — 시험이 자리를 잴 때는 **목록 길이로 나눈
/// 나머지**를 봐야 한다.
const int _kLoopBase = 1000;

/// 영상 위에 뜨는 글자는 그림자를 두른다 — 밝은 장면에서 흰 글자가 사라진다.
const List<Shadow> _kOverlayShadow = [
  Shadow(color: Color(0x99000000), blurRadius: 8),
];

/// 영상과 포스터를 화면에 앉히는 방법 — 🔴 **`contain` 이다. 잘라내지 않는다**
/// (2026-09-24 사용자 지적: 「가로 영상인데 다 세로로 자르면 어떻게 해? 영상은
/// 다 보여야지」). 남는 자리는 검정이다(인스타그램·유튜브 쇼츠가 그렇다).
///
/// 🔴 **상수로 빼 둔 까닭은 시험 때문이다.** 위젯 시험에서는 재생기가 초기화되지
/// 않아 [FittedBox] 가 **아예 안 생긴다** — 그리는 자리에서 `BoxFit` 을 읽는
/// 시험은 `cover` 로 되돌려도 **그냥 통과했다**(실제로 그렇게 헛시험을 한 번
/// 썼다). 값 자체를 못 박아야 되돌림이 잡힌다.
///
/// ⛔ **[BoxFit.cover] 로 되돌리지 말 것.** 홈 영상 줄은 `cover` 가 맞는데
/// (작은 카드가 한 줄에 서므로 폭을 맞춰야 한다) 여기는 **한 편을 보는 자리**다.
const BoxFit kReelFit = BoxFit.contain;

/// 보내기 단추의 무지개 — 레퍼런스의 보라 → 분홍 → 주황 대각선.
const LinearGradient _kSendGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFF7B5CFF), Color(0xFFD94FD5), Color(0xFFFF8A3D)],
);

/// 오른쪽 줄의 동그란 단추 하나 — 아이콘 + 숫자.
class _RailButton extends StatelessWidget {
  const _RailButton({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
    this.tint = Colors.white,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color tint;

  @override
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      // 🔴 레퍼런스의 동그라미가 뒤로 가기보다 **크다** — 46 → 54.
      _RoundTapTarget(
        onTap: onTap,
        size: 54,
        child: Icon(icon, color: tint, size: 26),
      ),
      const SizedBox(height: 6),
      Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w600,
          shadows: _kOverlayShadow,
        ),
      ),
    ],
  );
}

/// 반투명 동그라미 위의 누르는 자리 — 뒤로 가기·좋아요·댓글·보내기가 나눠 쓴다.
class _RoundTapTarget extends StatelessWidget {
  const _RoundTapTarget({
    super.key,
    required this.onTap,
    required this.child,
    this.size = 46,
    this.gradient,
  });

  final VoidCallback onTap;
  final Widget child;
  final double size;

  /// 주면 반투명 검정 대신 이것으로 칠한다 — 지금은 보내기 하나뿐이다.
  final Gradient? gradient;

  @override
  Widget build(BuildContext context) {
    final body = Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        /* 🔴 **흰 유리다 — 검정 반투명이 아니다** (2026-09-24 사용자 요청:
           「안쪽은 흰색 블러로만 처리하자. 글래스로」). 입력줄과 **같은 재질**
           이라야 한 벌로 읽힌다. */
        color: gradient == null ? Colors.white.withValues(alpha: kPillTint) : null,
        gradient: gradient,
        shape: BoxShape.circle,
      ),
      child: child,
    );
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      // 무지개(보내기)는 유리가 아니다 — 제 색으로 꽉 찬다.
      child: gradient != null ? body : _glassCircle(body),
    );
  }
}

/// 동그란 유리 — 🔴 **[ClipOval] 이 [BackdropFilter] 를 감싼다.** 순서가
/// 뒤바뀌면 흐림이 **네모로** 새어 나가 동그라미 밖에 흐린 자국이 남는다.
Widget _glassCircle(Widget child) => ClipOval(
  child: BackdropFilter(
    filter: ui.ImageFilter.blur(sigmaX: kPillBlur, sigmaY: kPillBlur),
    child: child,
  ),
);

/// 둥근 네모 유리 — 입력줄과 댓글 칸이 나눠 쓴다.
///
/// 🔴 **테가 없다** (2026-09-24 사용자 요청). 흰 기([kPillTint])와 흐림
/// ([kPillBlur])뿐이고, 값은 이 저장소의 다른 유리들과 **같은 것**을 쓴다.
///
/// ⚠️ **뒤가 도는 영상이다.** `glass_pill.dart` 머리말이 「흐림은 굴러가는
/// 목록 위에서 쓰지 말 것 — 가장자리에서 퍼 올 것이 없어 늘린 띠가 매 프레임
/// 달라져 **흰 직선**으로 보인다」고 경고한다. 여기서는 사용자가 유리를 콕
/// 집어 골랐으므로 **실기기에서 그 띠가 뜨는지 보고** 판단한다 — 뜨면 흐림만
/// 빼고 흰 기는 남긴다(모양은 그대로다).
Widget _glass({required double radius, required Widget child}) => ClipRRect(
  borderRadius: BorderRadius.circular(radius),
  child: BackdropFilter(
    filter: ui.ImageFilter.blur(sigmaX: kPillBlur, sigmaY: kPillBlur),
    child: ColoredBox(
      color: Colors.white.withValues(alpha: kPillTint),
      child: child,
    ),
  ),
);

/// 쪽 하나 — 포스터를 깔고 그 위에 영상을 덮는다.
///
/// 🔴 **컨트롤러는 「속성이 실제로 바뀔 때」만 건드린다 — `build` 에서 하지
/// 않는다.** `home_video_strip.dart` 의 `_VideoCardState` 와 같은 까닭이고 같은
/// 꼴이다: `build` 안에서 열고·틀고·버리면 **실기기에서 앱이 통째로 죽는다**
/// (`Fatal signal 6 (SIGABRT) in MediaCodec_loop`, 2026-09-24).
/// ⛔ 되돌리지 말 것.
class _ReelPage extends ConsumerStatefulWidget {
  const _ReelPage({super.key, required this.video, required this.open});

  final PublicVideo video;

  /// 지금 보고 있는 쪽인가 — 🔴 **참인 쪽만 재생기를 연다.**
  final bool open;

  @override
  ConsumerState<_ReelPage> createState() => _ReelPageState();
}

class _ReelPageState extends ConsumerState<_ReelPage> {
  VideoPlayerController? _c;

  /// 지금 컨트롤러가 물고 있는 주소 — 같은 주소로 두 번 만들지 않는다.
  String? _for;

  /// 손으로 멈춰 둔 상태(화면을 눌렀다). 쪽을 넘기면 풀린다.
  bool _paused = false;

  /// 🔴 **여는 일과 버리는 일을 줄 세운다** — 겹치면 아직 초기화 중인 것을
  /// 버리게 되고, 그게 네이티브에서 터지는 자리다.
  Future<void> _work = Future.value();

  @override
  void initState() {
    super.initState();
    if (widget.open) _sync();
  }

  @override
  void didUpdateWidget(_ReelPage old) {
    super.didUpdateWidget(old);
    if (widget.open != old.open || widget.video.id != old.video.id) {
      // 넘겨서 다시 온 쪽은 멈춰 둔 것을 푼다.
      if (widget.open && !old.open) _paused = false;
      _sync();
    }
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  void _sync() {
    if (!widget.open) {
      _queue(_close);
      return;
    }
    final url = ref.read(playbackUrlProvider(widget.video.id)).value;
    if (url != null) _queue(() => _open(url));
  }

  void _queue(Future<void> Function() job) {
    _work =
        _work.then((_) => mounted ? job() : Future.value()).catchError((_) {});
  }

  Future<void> _open(String url) async {
    if (_for == url) return;
    /* 🔴 **줄 서 있는 동안 이 쪽을 지나쳤으면 그만둔다** (2026-09-24 사용자
       지적: 「영상 재생이 안되는 것들이 너무 많아」).

       까닭: 여는 일은 [_work] 로 **한 줄로 세워** 놓는데, 재생기 하나를 여는 데
       네트워크 왕복이 걸린다. 빠르게 넘기면 지나간 쪽들의 열기가 줄에 쌓이고,
       **지금 보는 쪽의 열기가 그 뒤에 선다** — 그래서 화면에는 포스터만 남는다.
       지나간 것을 여기서 버려야 줄이 안 막힌다. */
    if (!mounted || !widget.open) return;
    _for = url;
    final old = _c;
    _c = null;
    // 🔴 **먼저 비운다** — 새것을 만드는 동안 옛것이 그려지면 안 된다.
    await old?.dispose();
    final next = VideoPlayerController.networkUrl(Uri.parse(url));
    try {
      await next.initialize();
      /* 🔴 **여기는 소리가 난다** — 홈 영상 줄은 음소거지만(줄이 저절로 돈다),
         이 화면은 **사람이 일부러 열어서 보는 자리**다. */
      await next.setVolume(1);
      await next.setLooping(true);
    } catch (_) {
      // 못 열면 포스터만 남는다 — 나머지 쪽은 그대로 넘길 수 있어야 한다.
      await next.dispose();
      _for = null;
      return;
    }
    // 🔴 여는 사이에 넘어갔을 수도 있다 — 위와 같은 까닭이다.
    if (!mounted || !widget.open) {
      await next.dispose();
      _for = null;
      return;
    }
    _c = next;
    setState(() {});
    await _apply();
  }

  Future<void> _close() async {
    final old = _c;
    if (old == null) return;
    _c = null;
    _for = null;
    await old.dispose();
    if (mounted) setState(() {});
  }

  Future<void> _apply() async {
    final c = _c;
    if (c == null || !c.value.isInitialized) return;
    final want = widget.open && !_paused;
    if (want && !c.value.isPlaying) {
      await c.play();
    } else if (!want && c.value.isPlaying) {
      await c.pause();
    }
  }

  void _toggle() {
    setState(() => _paused = !_paused);
    _queue(_apply);
  }

  @override
  Widget build(BuildContext context) {
    /* 🔴 **`watch` 가 아니라 `listen` 이다** — 주소가 도착하는 그 한 번만
       받으면 된다. `watch` 로 두면 리빌드 고리에 컨트롤러 조작이 다시 엮인다. */
    /* 🔴 **`listen` 이 아니라 `watch` 다 (2026-09-24 정정).** 전에는 「주소가
       도착하는 그 한 번만 받으면 된다」며 `listen` 을 썼는데, 그것은 **값이
       바뀔 때만** 울린다 — 주소가 이 쪽보다 **먼저** 도착해 있으면 한 번도
       안 울리고, [_sync] 의 `ref.read` 도 그 찰나를 놓치면 **영영 안 열렸다.**
       「재생이 안 되는 것들이 너무 많다」의 한 갈래가 이것이었다.
       (`fireImmediately` 로 고치려 했으나 이 버전의 `WidgetRef.listen` 에는
       그 인자가 없다.)

       🔴 **그래도 `build` 에서 컨트롤러를 만지는 것은 아니다** — [_queue] 는
       **줄에 얹기만** 하고, 실제 열기는 그 뒤 비동기로 일어난다. 게다가
       `_for != url` 이 막아서 **같은 주소로는 다시 안 얹힌다.** 그 둘이 없으면
       리빌드마다 열기가 쏟아져 `home_video_strip.dart` 가 겪은 그 죽음이 된다. */
    if (widget.open) {
      final url = ref.watch(playbackUrlProvider(widget.video.id)).value;
      if (url != null && _for != url) _queue(() => _open(url));
    }

    // 포스터는 **모든 쪽**이 본다 — 열지 않은 쪽이 검게 비지 않는 자리다.
    final poster = ref.watch(videoPosterProvider(widget.video.id)).value;

    final c = _c;
    final ready = c != null && c.value.isInitialized;

    return GestureDetector(
      onTap: _toggle,
      behavior: HitTestBehavior.opaque,
      child: Stack(
        fit: StackFit.expand,
        children: [
          const ColoredBox(color: Colors.black),
          if (poster != null)
            // 🔴 영상과 **같은 맞춤**이어야 한다 — 아래 `contain` 주석 참고.
            Image.memory(poster, fit: kReelFit, gaplessPlayback: true),
          /* 🔴 **잘라내지 않는다 — `contain` 이다** (2026-09-24 사용자 지적:
             「가로 영상인데 다 세로로 자르면 어떻게 해? 영상은 다 보여야지」).

             ⛔ **`cover` 로 되돌리지 말 것.** 처음엔 홈 영상 줄을 따라 `cover`
             로 뒀는데, 그쪽은 **작은 카드가 한 줄에 서는 자리**라 폭을 맞추려고
             자르는 것이 맞고, 여기는 **한 편을 보는 자리**라 자르면 경기 장면의
             양옆이 통째로 날아간다. 가로 영상이 특히 심했다.

             남는 자리는 **검정**이다(인스타그램·유튜브 쇼츠가 그렇다) — 세로로
             찍은 것은 꽉 차고, 가로로 찍은 것은 위아래에 검은 띠가 남는다. */
          if (ready)
            FittedBox(
              fit: kReelFit,
              child: SizedBox(
                width: c.value.size.width,
                height: c.value.size.height,
                child: VideoPlayer(c),
              ),
            ),
          if (_paused && widget.open)
            const Center(
              child: Icon(
                Icons.play_arrow_rounded,
                color: Colors.white70,
                size: 72,
              ),
            ),
        ],
      ),
    );
  }
}
