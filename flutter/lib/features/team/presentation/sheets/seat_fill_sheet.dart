import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/widgets/silver_sweep_border.dart';
import '../../../video/data/video_providers.dart';
import '../../data/candidate_providers.dart';
import '../../data/models/contact.dart';
import '../../data/models/squad_candidate.dart';
import 'sheet_skin.dart';

/// 빈 자리에 앉힐 사람으로 고른 결과. 🔴 **여기서 초대까지 하지 않는다** —
/// 시트는 「누구를 고를까」만 답하고, 초대와 낙관적 배치는 판을 들고 있는
/// 화면이 한다(웹도 `onPick` → `SquadPanel.invite` 로 같은 갈래다).
class SeatPick {
  const SeatPick({
    required this.userId,
    required this.nickname,
    this.cardPublicSlug,
  });

  final String userId;
  final String nickname;
  final String? cardPublicSlug;
}

/// 빈 자리를 눌렀을 때 올라오는 시트 — **AI 추천**과 **지인**이 탭 둘로 한
/// 시트에 들어 있다.
///
/// 🔴 **웹은 판 오른쪽에 두 판을 나란히 편다**(`SquadSuggest` + `SquadFriends`).
/// 폰 세로에는 그 자리가 없어서 시트로 접었다 — `www/docs/2026-08-31-앱-이식-
/// 지침.md` §4 가 이식 전에 미리 정해 둔 재설계다.
///
/// 🔴 **웹과 또 다른 것 하나**: 웹은 지인을 고른 뒤 **빈 자리를 다시 눌러**
/// 앉힌다(`placing`). 여기서는 이미 자리를 누르고 들어왔으므로 그 왕복이
/// 없다 — 고르는 즉시 그 자리로 돌아간다.
Future<SeatPick?> showSeatFillSheet(
  BuildContext context, {
  required String teamId,
  required String positionCode,
  required String positionLabel,

  /// 이미 판에 앉은 사람 → 그 자리(**닉네임** → `MF`). 그 사람은 못 고른다.
  ///
  /// 🔴 **닉네임으로 맞춘다** — 스쿼드 구성원에는 `user_id` 가 없고
  /// (`player_card_id`·`card_public_slug`·`nickname` 뿐이다) 지인 목록에는
  /// 카드 슬러그가 없어서, 지금 두 쪽이 공통으로 가진 값이 이것뿐이다. 웹도
  /// 같은 자리에서 닉네임을 쓴다. ⚠️ 닉네임이 같은 두 사람은 구별 못 한다 —
  /// 서버가 어느 한쪽에 id 를 실어 주면 그걸로 바꾼다.
  Map<String, String> placed = const {},
}) =>
    showModalBottomSheet<SeatPick>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _SeatFillSheet(
        teamId: teamId,
        positionCode: positionCode,
        positionLabel: positionLabel,
        placed: placed,
      ),
    );

/* 🔴 **색·틀은 `sheet_skin.dart` 한 곳에서 온다**(2026-09-25 사용자 요청:
   「새로 만드는 것들 그 AI 추천판에 있는 거랑 스타일 똑같이 가져가」).
   전에는 이 파일이 값을 따로 들고 있었다 — 그러면 새 시트가 생길 때마다
   조용히 갈린다. */

const List<String> _kGrades = ['S', 'A', 'B', 'C', 'D', 'F'];

class _SeatFillSheet extends ConsumerStatefulWidget {
  const _SeatFillSheet({
    required this.teamId,
    required this.positionCode,
    required this.positionLabel,
    required this.placed,
  });

  final String teamId;
  final String positionCode;
  final String positionLabel;
  final Map<String, String> placed;

  @override
  ConsumerState<_SeatFillSheet> createState() => _SeatFillSheetState();
}

class _SeatFillSheetState extends ConsumerState<_SeatFillSheet> {
  /// 0 = AI 추천, 1 = 지인.
  int _tab = 0;

  /// 🔴 `null` 이 「등급 상관없음」이다 — `'any'` 같은 글자를 지어 두면 그게
  /// 그대로 서버로 새 나간다.
  String? _grade;

  @override
  Widget build(BuildContext context) {
    final h = MediaQuery.sizeOf(context).height;

    return Container(
      height: h * 0.86,
      decoration: const BoxDecoration(
        color: kSheetInk,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      /* 🔴 **유리 안에 유리를 넣지 않는다**(`refractive_glass.dart`). 시트는
         알파만 쓴 면이고, 안쪽 줄들은 흐림 없이 색만 얹는다. */
      child: Column(
        children: [
          const _Grip(),
          _Header(label: widget.positionLabel),
          _Tabs(
            tab: _tab,
            onTab: (t) => setState(() => _tab = t),
          ),
          Expanded(
            child: _tab == 0
                ? _SuggestTab(
                    teamId: widget.teamId,
                    positionCode: widget.positionCode,
                    grade: _grade,
                    onGrade: (g) => setState(() => _grade = g),
                  )
                : _FriendsTab(placed: widget.placed),
          ),
        ],
      ),
    );
  }
}

class _Grip extends StatelessWidget {
  const _Grip();

  @override
  Widget build(BuildContext context) => Container(
        width: 40,
        height: 4,
        margin: const EdgeInsets.only(top: 10, bottom: 6),
        decoration: BoxDecoration(
          color: kSheetOn.withValues(alpha: 0.22),
          borderRadius: BorderRadius.circular(2),
        ),
      );
}

class _Header extends StatelessWidget {
  const _Header({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 6, 8, 2),
        child: Row(
          children: [
            Expanded(
              child: Text(
                '$label 자리에 넣기',
                style: const TextStyle(
                  color: kSheetOn,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
            ),
            IconButton(
              tooltip: '닫기',
              onPressed: () => Navigator.of(context).pop(),
              icon: Icon(Icons.close, color: kSheetOn.withValues(alpha: 0.7)),
            ),
          ],
        ),
      );
}

class _Tabs extends StatelessWidget {
  const _Tabs({required this.tab, required this.onTab});

  final int tab;
  final ValueChanged<int> onTab;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
        child: Row(
          children: [
            _TabPill(
              key: const Key('seat-tab-ai'),
              label: 'AI 추천',
              on: tab == 0,
              onTap: () => onTab(0),
            ),
            const SizedBox(width: 8),
            _TabPill(
              key: const Key('seat-tab-friends'),
              label: '지인',
              on: tab == 1,
              onTap: () => onTab(1),
            ),
          ],
        ),
      );
}

class _TabPill extends StatelessWidget {
  const _TabPill({
    super.key,
    required this.label,
    required this.on,
    required this.onTap,
  });

  final String label;
  final bool on;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: _Edge(
          on: on,
          radius: 999,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
            child: Text(
              label,
              style: TextStyle(
                color: on ? kSheetOn : kSheetOn.withValues(alpha: 0.6),
                fontSize: 14,
                fontWeight: on ? FontWeight.w600 : FontWeight.w500,
              ),
            ),
          ),
        ),
      );
}

/// 얇은 실버 테 — **고른 것만 그 테가 돌아다닌다**
/// (2026-09-25 사용자 요청: 「누른 버튼들만 부드럽고 자연스럽게 그 외곽선이
/// 돌아다니게」).
///
/// 🔴 **면을 칠하지 않는다.** 고른 표시는 **선**이다 — `silver_sweep_border`
/// 머리말의 「선이 흐르는 것이지 판이 빛나는 것이 아니다」와 같은 판단이고,
/// 칠하면 아래 줄들의 밝은 면과 층이 겹쳐 읽힌다.
///
/// ⚠️ **한 화면에 여럿이 된다** — 그 파일이 원래 「한 화면에 하나」를 걱정했고
/// 홈에서는 색으로 갈랐다. 여기서는 **한 번에 하나만 켜진다**(탭도 등급도
/// 고른 것 하나뿐)라 산만해지지 않는다. 🔴 탭과 등급이 **동시에** 켜져 둘이
/// 도는 것은 맞다 — 둘은 서로 다른 물음(어디서 찾나 / 어느 등급)이다.
class _Edge extends StatelessWidget {
  const _Edge({
    required this.on,
    required this.radius,
    required this.child,
  });

  final bool on;
  final double radius;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (!on) {
      return DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(radius),
          border: Border.all(color: kSheetEdge, width: kSheetEdgeWidth),
        ),
        child: child,
      );
    }
    return SilverSweepBorder(
      radius: radius,
      color: kSheetSilver,
      baseColor: kSheetEdge,
      strokeWidth: 1,
      child: child,
    );
  }
}

// ── AI 추천 ──────────────────────────────────────────────────────────────

class _SuggestTab extends ConsumerWidget {
  const _SuggestTab({
    required this.teamId,
    required this.positionCode,
    required this.grade,
    required this.onGrade,
  });

  final String teamId;
  final String positionCode;
  final String? grade;
  final ValueChanged<String?> onGrade;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(
      candidatesProvider(CandidateQuery(teamId, positionCode, grade: grade)),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _GradeChips(grade: grade, onGrade: onGrade),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 2, 20, 8),
          child: Text(
            /* 🔴 **이 수는 서버가 거른 결과다.** 화면이 한 번 더 거르면 여기
               적힌 수와 실제 줄 수가 갈린다 — 그래서 목록을 그대로 센다. */
            async.maybeWhen(
              data: (list) => '${list.length}명',
              orElse: () => ' ',
            ),
            style: TextStyle(
              color: kSheetOn.withValues(alpha: 0.5),
              fontSize: 12.5,
            ),
          ),
        ),
        Expanded(
          child: async.when(
            loading: () => const _Center(child: SheetSpinner()),
            error: (e, _) => _Center(
              child: SheetMessage(
                title: '후보를 불러오지 못했습니다',
                detail: '$e',
              ),
            ),
            data: (list) => list.isEmpty
                ? _Center(
                    child: SheetMessage(
                      title: grade == null
                          ? '이 자리에 맞는 사람이 아직 없습니다'
                          : '$grade 등급에는 맞는 사람이 없습니다',
                      detail: grade == null
                          ? '조건에 맞는 사람이 생기면 여기 뜹니다.'
                          : '등급을 풀면 더 보입니다.',
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
                    itemCount: list.length,
                    itemBuilder: (_, i) => _CandidateRow(candidate: list[i]),
                  ),
          ),
        ),
      ],
    );
  }
}

class _GradeChips extends StatelessWidget {
  const _GradeChips({required this.grade, required this.onGrade});

  final String? grade;
  final ValueChanged<String?> onGrade;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 46,
        child: ListView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          children: [
            for (final g in _kGrades) ...[
              _GradeChip(
                key: Key('grade-chip-$g'),
                label: g,
                on: grade == g,
                // 같은 칩을 다시 누르면 푼다 — 끄는 길이 칩 자신에게도 있다.
                onTap: () => onGrade(grade == g ? null : g),
              ),
              const SizedBox(width: 7),
            ],
            _GradeChip(
              key: const Key('grade-chip-any'),
              label: '등급 상관없음',
              on: grade == null,
              wide: true,
              onTap: () => onGrade(null),
            ),
          ],
        ),
      );
}

class _GradeChip extends StatelessWidget {
  const _GradeChip({
    super.key,
    required this.label,
    required this.on,
    required this.onTap,
    this.wide = false,
  });

  final String label;
  final bool on;
  final VoidCallback onTap;
  final bool wide;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: _Edge(
          on: on,
          radius: 999,
          child: SizedBox(
            width: wide ? null : 34,
            height: 34,
            child: Padding(
              padding:
                  wide ? const EdgeInsets.symmetric(horizontal: 14) : EdgeInsets.zero,
              child: Center(
                child: Text(
                  label,
                  style: TextStyle(
                    color: on ? kSheetOn : kSheetOn.withValues(alpha: 0.6),
                    fontSize: wide ? 12.5 : 13,
                    fontWeight: on ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
}

class _CandidateRow extends ConsumerWidget {
  const _CandidateRow({required this.candidate});

  final SquadCandidate candidate;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: GestureDetector(
          onTap: () => Navigator.of(context).pop(
            SeatPick(
              userId: candidate.userId,
              nickname: candidate.nickname,
              cardPublicSlug: candidate.cardPublicSlug,
            ),
          ),
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: kSheetBox,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Thumb(slug: candidate.cardPublicSlug),
                const SizedBox(width: 12),
                Expanded(child: _CandidateText(candidate: candidate)),
              ],
            ),
          ),
        ),
      );
}

/// 후보 옆에 도는 장면. 🔴 **대표 영상이 없으면 자리표시자**다 — 검은 칸으로
/// 두면 1.28에서 고친 「끊긴 썸네일이 영영 검다」와 같아 보인다.
class _Thumb extends ConsumerWidget {
  const _Thumb({required this.slug});

  final String? slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    Widget frame(Widget child) => ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: SizedBox(width: 62, height: 84, child: child),
        );

    if (slug == null) return frame(const _ThumbBlank());

    final videoId = ref.watch(candidateFeaturedVideoProvider(slug!)).value;
    if (videoId == null) return frame(const _ThumbBlank());

    /* 🔴 포스터는 앱에 이미 있는 경로를 그대로 쓴다 — 2026-09-25에 붙인
       **재시도 세 번**이 거기 있다. 여기서 새로 받아 오면 그 고침을 못 받는다. */
    final poster = ref.watch(videoPosterProvider(videoId)).value;
    if (poster == null) return frame(const _ThumbBlank());

    return frame(Image.memory(poster, fit: BoxFit.cover));
  }
}

class _ThumbBlank extends StatelessWidget {
  const _ThumbBlank();

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(color: kSheetBoxInk.withValues(alpha: 0.07)),
        child: Center(
          child: Icon(
            Icons.videocam_off_outlined,
            size: 18,
            color: kSheetBoxInk.withValues(alpha: 0.3),
          ),
        ),
      );
}

class _CandidateText extends StatelessWidget {
  const _CandidateText({required this.candidate});

  final SquadCandidate candidate;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Flexible(
                child: Text(
                  candidate.nickname,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: kSheetBoxInk,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (candidate.grade != null) ...[
                const SizedBox(width: 8),
                _GradeBadge(
                  key: Key('cand-grade-${candidate.userId}'),
                  grade: candidate.grade!,
                ),
              ],
              // 🔴 검수 전 — 그 등급이 아직 사람 손을 안 거쳤다는 뜻이다.
              if (candidate.provisional == true) ...[
                const SizedBox(width: 6),
                const _ProvisionalBadge(),
              ],
            ],
          ),
          /* 🔴 **없으면 아무것도 안 그린다.** `notes` 가 비어 있거나 한 줄인
             것은 정상이고, 화면이 채워 넣으면 없는 말을 카드에 적게 된다. */
          for (final n in candidate.notes)
            Padding(
              padding: const EdgeInsets.only(top: 5),
              /* 🔴 불릿은 **장식이라 글에 안 섞는다** — `'· $n'` 으로 이어
                 붙이면 그 줄이 한 덩어리가 되어 읽는 쪽(시험·스크린 리더)이
                 문구만 집어낼 수 없다. */
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '·',
                    style: TextStyle(
                      color: kSheetBoxInk.withValues(alpha: 0.4),
                      fontSize: 12.5,
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      n,
                      style: TextStyle(
                        color: kSheetBoxInk.withValues(alpha: 0.72),
                        fontSize: 12.5,
                        height: 1.35,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      );
}

class _GradeBadge extends StatelessWidget {
  const _GradeBadge({super.key, required this.grade});

  final String grade;

  /// 🔴 **경계는 서버가 긋는다** — 여기서는 받은 글자에 색만 입힌다.
  /// 🔴 **밝은 면(`kSheetBox`) 위에서 쓰는 값이다.** 검은 화면용 밝은 색을 그대로
  /// 두면 안 된다 — 1.27에서 초록(`#70ED88`)이 흰 판에서 대비 2:1 도 안 나와
  /// 글자가 사라진 그 자리와 같다. 거기서 내린 초록(`#1E7F45`)을 그대로 쓰고
  /// 나머지도 같은 만큼 내렸다.
  static const _color = {
    'S': Color(0xFF9A6B00),
    'A': Color(0xFF1E7F45),
    'B': Color(0xFF16607F),
    'C': Color(0xFF5A6068),
    'D': Color(0xFF9A4E12),
    'F': Color(0xFF9E2B2B),
  };

  @override
  Widget build(BuildContext context) {
    final c = _color[grade] ?? kSheetOn;
    return Container(
      width: 22,
      height: 22,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: c.withValues(alpha: 0.7)),
      ),
      child: Text(
        grade,
        style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w700),
      ),
    );
  }
}

class _ProvisionalBadge extends StatelessWidget {
  const _ProvisionalBadge();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: kSheetBoxInk.withValues(alpha: 0.3)),
        ),
        child: Text(
          '검수 전',
          style: TextStyle(
            color: kSheetBoxInk.withValues(alpha: 0.62),
            fontSize: 10.5,
            fontWeight: FontWeight.w500,
          ),
        ),
      );
}

// ── 지인 ─────────────────────────────────────────────────────────────────

class _FriendsTab extends ConsumerStatefulWidget {
  const _FriendsTab({required this.placed});

  final Map<String, String> placed;

  @override
  ConsumerState<_FriendsTab> createState() => _FriendsTabState();
}

class _FriendsTabState extends ConsumerState<_FriendsTab> {
  final _controller = TextEditingController();

  /// 🔴 **타자마다 서버에 묻지 않는다** — 웹과 같은 250ms 다.
  Timer? _debounce;
  String _query = '';
  List<FoundUser> _found = const [];
  final _requested = <String>{};

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String v) {
    _debounce?.cancel();
    setState(() => _query = v.trim());
    if (_query.isEmpty) {
      setState(() => _found = const []);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 250), _search);
  }

  Future<void> _search() async {
    final q = _query;
    final rows = await ref.read(contactRepositoryProvider).search(q);
    // 타자가 이어졌으면 늦게 온 결과를 버린다 — 안 버리면 순서가 뒤집힌다.
    if (!mounted || q != _query) return;
    setState(() => _found = rows);
  }

  Future<void> _request(FoundUser u) async {
    await ref.read(contactRepositoryProvider).request(u.id);
    if (!mounted) return;
    setState(() => _requested.add(u.id));
  }

  @override
  Widget build(BuildContext context) {
    final contacts = ref.watch(contactsProvider);
    final requests = ref.watch(contactRequestsProvider);

    /* 🔴 지인은 **화면에서 거른다** — 서버에 다시 묻지 않는다. 그래야 타자를
       치는 동안 지인이 깜빡이며 사라지지 않는다(웹과 같은 판단). */
    final mine = (contacts.value ?? const <Contact>[])
        .where((c) => _query.isEmpty || c.nickname.contains(_query))
        .toList();

    final others =
        _found.where((f) => !mine.any((c) => c.userId == f.id)).toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
      children: [
        _SearchField(controller: _controller, onChanged: _onChanged),
        const SizedBox(height: 12),
        for (final r in requests.value ?? const <ContactRequest>[])
          _RequestRow(request: r),

        /* 🔴 **지인이 위, 다른 사람이 아래** (2026-09-25 사용자 요청). 섞어
           두면 이미 아는 사람과 처음 보는 사람이 구별이 안 된다. */
        if (mine.isNotEmpty) const _GroupLabel('지인'),
        for (final c in mine)
          _ContactRow(contact: c, placedAt: widget.placed[c.nickname]),
        if (mine.isEmpty && _query.isEmpty)
          SheetMessage(
            title: '아직 지인이 없습니다',
            detail: '닉네임으로 찾아 지인 신청을 보내 보세요.',
          ),

        // 이미 지인인 사람은 아래 묶음에서 뺀다 — 같은 사람이 두 줄이 된다.
        if (others.isNotEmpty) const _GroupLabel('다른 사람'),
        for (final f in others)
          _FoundRow(
            found: f,
            sent: _requested.contains(f.id),
            onRequest: () => _request(f),
          ),

        /* ⚠️ **아무것도 안 치면 아래가 빈다.** 서버의 `GET /users/search` 가
           `q` 를 **최소 한 자** 받고(빈 값은 422), 「전체 사용자 목록」 경로가
           계약에 없다 — 그 경로가 생기면 여기를 처음부터 채운다. */
        if (_query.isEmpty && mine.isNotEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 14),
            child: Text(
              '닉네임을 한 자만 쳐도 다른 사람이 아래에 뜹니다.',
              style: TextStyle(color: kSheetOnDim, fontSize: 12.5),
            ),
          ),
      ],
    );
  }
}

/// 묶음 이름 — 「지인」 / 「다른 사람」.
class _GroupLabel extends StatelessWidget {
  const _GroupLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 4, bottom: 8, left: 4),
        child: Text(
          text,
          style: TextStyle(
            color: kSheetOn.withValues(alpha: 0.55),
            fontSize: 12,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.4,
          ),
        ),
      );
}

class _SearchField extends StatelessWidget {
  const _SearchField({required this.controller, required this.onChanged});

  final TextEditingController controller;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => TextField(
        key: const Key('friend-search'),
        controller: controller,
        onChanged: onChanged,
        style: const TextStyle(color: kSheetBoxInk, fontSize: 14.5),
        cursorColor: kSheetBoxInk,
        decoration: InputDecoration(
          hintText: '닉네임으로 찾기',
          hintStyle: TextStyle(color: kSheetBoxInk.withValues(alpha: 0.42)),
          prefixIcon: Icon(Icons.search,
              color: kSheetBoxInk.withValues(alpha: 0.42), size: 20),
          filled: true,
          fillColor: kSheetBox,
          contentPadding: const EdgeInsets.symmetric(vertical: 14),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide.none,
          ),
        ),
      );
}

class _ContactRow extends StatelessWidget {
  const _ContactRow({required this.contact, required this.placedAt});

  final Contact contact;

  /// 이미 앉아 있으면 그 자리(`MF`), 아니면 `null`.
  final String? placedAt;

  @override
  Widget build(BuildContext context) {
    final seated = placedAt != null;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: GestureDetector(
        // 🔴 이미 앉은 사람은 못 고른다 — 고르면 판에 둘이 된다.
        onTap: seated
            ? null
            : () => Navigator.of(context).pop(
                  SeatPick(
                    userId: contact.userId,
                    nickname: contact.nickname,
                    cardPublicSlug: contact.cardPublicSlug,
                  ),
                ),
        child: Opacity(
          opacity: seated ? 0.45 : 1,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            decoration: BoxDecoration(
              color: kSheetBox,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    contact.nickname,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: kSheetBoxInk,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                if (seated) ...[
                  /* 🔴 **밝은 면용 초록이다.** `AppTheme.seed`(`#70ED88`)는
                     검은 화면용이라 이 면에서 대비가 2:1 도 안 나온다 —
                     1.27이 리포트에서 겪고 내린 값(`#1E7F45`)을 그대로 쓴다. */
                  Icon(Icons.check, size: 16, color: kSheetGreen),
                  const SizedBox(width: 5),
                  Text(
                    placedAt!,
                    style: TextStyle(
                      color: kSheetGreen,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RequestRow extends ConsumerWidget {
  const _RequestRow({required this.request});

  final ContactRequest request;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
            color: kSheetBox,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(
            children: [
              const Expanded(
                child: Text(
                  '지인 신청이 왔습니다',
                  style: TextStyle(color: kSheetBoxInk, fontSize: 14),
                ),
              ),
              _SmallButton(
                label: '수락',
                onTap: () async {
                  await ref.read(contactRepositoryProvider).accept(request.id);
                  ref
                    ..invalidate(contactsProvider)
                    ..invalidate(contactRequestsProvider);
                },
              ),
            ],
          ),
        ),
      );
}

class _FoundRow extends StatelessWidget {
  const _FoundRow({
    required this.found,
    required this.sent,
    required this.onRequest,
  });

  final FoundUser found;
  final bool sent;
  final VoidCallback onRequest;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: kSheetOn.withValues(alpha: 0.12)),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  found.nickname,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: kSheetBoxInk.withValues(alpha: 0.85),
                    fontSize: 15,
                  ),
                ),
              ),
              /* 🔴 **여기서 바로 앉히지 않는다.** 지인이 아닌 사람을 고를 수
                 있게 두면 동의 없이 부르는 길이 생긴다 — 신청이 먼저다. */
              _SmallButton(
                label: sent ? '신청함' : '지인 신청',
                dim: sent,
                onTap: sent ? null : onRequest,
              ),
            ],
          ),
        ),
      );
}

class _SmallButton extends StatelessWidget {
  const _SmallButton({required this.label, this.onTap, this.dim = false});

  final String label;
  final VoidCallback? onTap;
  final bool dim;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
          /* 🔴 이 버튼들은 **밝은 줄 안**에 있다 — 테도 글자도 그 면 위에서
             읽히는 값이어야 한다(바깥 탭·등급 칩은 검은 면 위라 실버다). */
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: kSheetBoxInk.withValues(alpha: dim ? 0.18 : 0.45),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: kSheetBoxInk.withValues(alpha: dim ? 0.4 : 0.9),
              fontSize: 12.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      );
}

/// 가운데 한 조각 — 로딩·안내가 판 한가운데 서는 자리.
class _Center extends StatelessWidget {
  const _Center({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) =>
      Center(child: Padding(padding: const EdgeInsets.all(32), child: child));
}
