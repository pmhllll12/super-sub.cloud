import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../card/data/models/player_card.dart';
import '../../../card/presentation/mate_cards_controller.dart';
import '../../../profile/presentation/widgets/player_card_view.dart';
import '../../../../core/widgets/silver_sweep_border.dart';
import '../../data/match_providers.dart';
import '../../data/squad_providers.dart';
import '../../data/models/match_candidate.dart';
import '../../data/models/review_option.dart';
import '../../data/models/squad.dart';
import '../../seats_from_squad.dart';
import '../widgets/read_only_pitch.dart';
import 'sheet_skin.dart';

/// 🔴 **답을 기다리는 주기.** 웹의 초대 폴링(3초)과 같은 결이다 — 알림 채널이
/// 없어서 「몇 초마다 GET」으로 확인한다(계약 3-12절의 설명).
const Duration kMatchPollEvery = Duration(seconds: 3);

/// 경기 신청을 건 뒤의 화면 — **기다림 → 두 팀 판 → 경기 완료 → 평가.**
///
/// 🔴 **「걸었다」와 「잡혔다」는 다르다.** 신청은 상대 팀장에게 가고, 수락해야
/// `match_id` 가 찬다 — 그 전까지는 기다리는 화면이다.
Future<void> showMatchWaitingSheet(
  BuildContext context, {
  required String teamId,
  required String requestId,
  required String ourTeamName,
  required Squad? ourSquad,
}) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _MatchWaitingSheet(
        teamId: teamId,
        requestId: requestId,
        ourTeamName: ourTeamName,
        ourSquad: ourSquad,
      ),
    );

class _MatchWaitingSheet extends ConsumerStatefulWidget {
  const _MatchWaitingSheet({
    required this.teamId,
    required this.requestId,
    required this.ourTeamName,
    required this.ourSquad,
  });

  final String teamId;
  final String requestId;
  final String ourTeamName;
  final Squad? ourSquad;

  @override
  ConsumerState<_MatchWaitingSheet> createState() => _MatchWaitingSheetState();
}

class _MatchWaitingSheetState extends ConsumerState<_MatchWaitingSheet> {
  Timer? _poll;
  TeamMatchRequest? _request;

  /// 「경기 완료」를 눌렀다 — 평가 화면이다.
  bool _reviewing = false;

  @override
  void initState() {
    super.initState();
    _check();
    _poll = Timer.periodic(kMatchPollEvery, (_) => _check());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _check() async {
    try {
      final all = await ref.read(matchRepositoryProvider).requests(widget.teamId);
      if (!mounted) return;
      final mine = all.where((r) => r.id == widget.requestId);
      if (mine.isEmpty) return;
      setState(() => _request = mine.first);
      // 🔴 답이 오면 그만 묻는다 — 안 그러면 화면이 살아 있는 동안 계속 나간다.
      if (!mine.first.isPending) _poll?.cancel();
    } catch (_) {
      // 한 번 실패해도 다음 주기에 다시 묻는다.
    }
  }

  @override
  Widget build(BuildContext context) {
    final req = _request;
    final accepted = req != null && req.isAccepted && req.matchId != null;

    return SheetShell(
      title: accepted ? (_reviewing ? '경기 평가' : '경기가 잡혔습니다') : '신청을 보냈습니다',
      child: !accepted
          ? const Center(
              child: SheetMessage(
                title: '상대 팀장의 답을 기다리는 중입니다',
                detail: '수락하면 여기에서 바로 이어집니다.',
              ),
            )
          : _reviewing
              ? _ReviewPane(
                  matchId: req.matchId!,
                  /* 🔴 **우리 팀도 평가한다**(2026-09-25 사용자 요청) —
                     같이 뛴 사람은 상대만이 아니다. 나는 뺀다(자기 평가는
                     계약도 422 `SELF_REVIEW` 로 막는다). */
                  groups: [
                    (widget.ourTeamName, _ourMates()),
                    (req.targetTeamName, _opponents(req)),
                  ],
                  onDone: () => Navigator.of(context).pop(),
                )
              : _MatchPane(
                  request: req,
                  ourTeamName: widget.ourTeamName,
                  ourSquad: widget.ourSquad,
                  /* 🔴 **상대 판을 진짜로 읽는다**(2026-09-25 사용자 요청:
                     「실제 그 사람들의 카드가 나와야지」). 슬러그가 없거나
                     아직 안 왔으면 그때만 자리표시자다. */
                  theirSquad: _theirSquad(req),
                  opponents: _opponents(req),
                  cardBuilder: _card,
                  onFinish: () => setState(() => _reviewing = true),
                ),
    );
  }

  /// 그 슬러그의 카드가 **이미 와 있으면** 그린다 — 홈 판과 **같은 통**을
  /// 쓴다(`mateCardsProvider`). 🔴 따로 받아 오면 홈이 이미 받아 둔 카드를
  /// 두 번 부르고, 꾸밈이 갈릴 수 있다.
  Widget? _card(String slug, double width) {
    final card = ref.watch(mateCardsProvider)[slug];
    if (card == null) {
      // 🔴 **빌드 중에 상태를 바꾸지 않는다** — 프레임이 끝난 뒤로 미룬다.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) ref.read(mateCardsProvider.notifier).want([slug]);
      });
      return null;
    }
    return PlayerCardView(
      width: width,
      seed: card.publicSlug,
      alias: aliasOf(card),
      style: card.style,
      photoUrl: card.photoUrl,
    );
  }

  /// 우리 팀에서 **나 말고** 같이 뛴 사람들.
  ///
  /// 🔴 **나는 뺀다** — 자기 평가는 계약이 422 `SELF_REVIEW` 로 막는다.
  List<String> _ourMates() {
    final seats = seatsFromSquad(
      widget.ourSquad,
      squadSizeOf(widget.ourSquad?.formation),
    );
    return [
      for (final s in seats.slots) ?seats.mates[s.area],
    ];
  }

  /// 상대 팀 판 — 슬러그가 있으면 읽어 온다.
  ///
  /// ⚠️ **슬러그가 `null` 인 것은 정상이다**(스쿼드를 아직 안 만든 팀).
  Squad? _theirSquad(TeamMatchRequest req) {
    final slug = req.targetSquadSlug;
    if (slug == null) return null;
    return ref.watch(squadBySlugProvider(slug)).value;
  }

  /// 상대 팀 선수들.
  ///
  /// 🔴 **이름을 지어내지 않는다.** 상대 판(`GET /squads/{slug}`)을 읽을 수
  /// 있으면 그 이름이고, 없으면 **「팀이름 선수 N」으로 자리만** 채운다 —
  /// 사람이 봤을 때 「아직 못 읽었다」가 드러나야 한다.
  ///
  /// ⚠️ 슬러그가 `null` 인 것은 **정상이다**(스쿼드를 아직 안 만든 팀).
  List<String> _opponents(TeamMatchRequest req) {
    final size = seatsFromSquad(widget.ourSquad, squadSizeOf(widget.ourSquad?.formation))
        .slots
        .length;
    return [
      for (var i = 1; i <= size; i++) '${req.targetTeamName} 선수 $i',
    ];
  }
}

// ── 잡힌 경기 ─────────────────────────────────────────────────────────────

class _MatchPane extends StatelessWidget {
  const _MatchPane({
    required this.request,
    required this.ourTeamName,
    required this.ourSquad,
    required this.theirSquad,
    required this.opponents,
    required this.cardBuilder,
    required this.onFinish,
  });

  final TeamMatchRequest request;
  final String ourTeamName;
  final Squad? ourSquad;

  /// 상대 판. `null` 이면 못 읽은 것이고, 그때만 [opponents] 로 자리를 채운다.
  final Squad? theirSquad;
  final List<String> opponents;

  /// 그 슬러그의 **진짜 선수 카드**를 그려 준다.
  final Widget? Function(String slug, double width) cardBuilder;
  final VoidCallback onFinish;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
        children: [
          _When(playedAt: request.playedAt, place: request.place),
          const SizedBox(height: 14),
          /* 🔴 **위아래로 쌓는다**(2026-09-25 사용자 요청). 폰 폭에 나란히
             놓으면 카드가 손톱만 해져 아무것도 안 읽힌다. */
          ReadOnlyPitch(
            title: ourTeamName,
            squad: ourSquad,
            cardBuilder: cardBuilder,
          ),
          const SizedBox(height: 16),
          ReadOnlyPitch(
            title: request.targetTeamName,
            squad: theirSquad,
            // 🔴 진짜 판이 있으면 자리표시자는 안 쓴다.
            placeholders: theirSquad == null ? opponents : const [],
            cardBuilder: cardBuilder,
          ),
          const SizedBox(height: 18),
          /* 🔴 **취소와 달리 되돌릴 수 없다** — 누르면 평가로 넘어간다.
             웹도 같은 자리에서 한 번 더 묻는데, 폰에서는 시트가 하나 더
             뜨는 것이 더 어수선해 **다음 화면이 곧 확인**이 되게 뒀다
             (평가를 안 내고 닫으면 아무 일도 안 일어난다). */
          _PrimaryButton(label: '경기 완료', onTap: onFinish),
        ],
      );
}

class _When extends StatelessWidget {
  const _When({required this.playedAt, required this.place});

  final String playedAt;
  final String place;

  @override
  Widget build(BuildContext context) {
    final at = DateTime.tryParse(playedAt);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: kSheetBox,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Text(
            at == null
                ? playedAt
                : '${at.month}월 ${at.day}일 '
                    '${at.hour.toString().padLeft(2, '0')}:'
                    '${at.minute.toString().padLeft(2, '0')}',
            style: const TextStyle(
              color: kSheetBoxInk,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            place,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: kSheetBoxInk.withValues(alpha: 0.7),
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

// ── 평가 ──────────────────────────────────────────────────────────────────

class _ReviewPane extends ConsumerStatefulWidget {
  const _ReviewPane({
    required this.matchId,
    required this.groups,
    required this.onDone,
  });

  final String matchId;

  /// (팀 이름, 그 팀에서 같이 뛴 사람들) — 우리 팀이 먼저다.
  final List<(String, List<String>)> groups;
  final VoidCallback onDone;

  @override
  ConsumerState<_ReviewPane> createState() => _ReviewPaneState();
}

class _ReviewPaneState extends ConsumerState<_ReviewPane> {
  /// 상대 한 명마다 고른 항목들.
  final Map<String, Set<String>> _picked = {};

  /// 지금 **펼쳐 둔 사람.** 🔴 한 번에 하나만 연다 (2026-09-25 사용자 요청:
  /// 「사람 판마다 리뷰 버튼 다 처음부터 보여주지말고」) — 다섯 명 × 아홉
  /// 항목이 한꺼번에 펼쳐지면 무엇을 고르는 중인지 잃는다.
  String? _open;

  List<ReviewOption>? _options;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final opts = await ref.read(matchRepositoryProvider).reviewOptions();
    if (!mounted) return;
    setState(() => _options = opts);
  }

  @override
  Widget build(BuildContext context) {
    final options = _options;
    if (options == null) return const Center(child: SheetSpinner());

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            '같이 뛴 사람을 눌러 평가해 주세요.',
            style: TextStyle(color: kSheetOnDim, fontSize: 13),
          ),
        ),
        for (final (team, people) in widget.groups) ...[
          if (people.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.only(top: 4, bottom: 8, left: 4),
              child: Text(
                team,
                style: TextStyle(
                  color: kSheetOn.withValues(alpha: 0.55),
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.4,
                ),
              ),
            ),
            for (final who in people)
              _ReviewRow(
                who: who,
                options: options,
                open: _open == who,
                picked: _picked[who] ?? const {},
                onToggleOpen: () =>
                    setState(() => _open = _open == who ? null : who),
                onToggle: (code) => setState(() {
                  final set = _picked.putIfAbsent(who, () => <String>{});
                  set.contains(code) ? set.remove(code) : set.add(code);
                }),
              ),
          ],
        ],
        const SizedBox(height: 6),
        _PrimaryButton(
          label: _sending ? '보내는 중…' : '평가 보내기',
          /* 🔴 **하나도 안 고르면 못 낸다**(422 `NO_OPTION_SELECTED`).
             화면이 먼저 막아야 빈 평가로 서버를 부르지 않는다. */
          enabled: !_sending && _picked.values.any((s) => s.isNotEmpty),
          onTap: _submit,
        ),
      ],
    );
  }

  Future<void> _submit() async {
    setState(() => _sending = true);
    final repo = ref.read(matchRepositoryProvider);
    try {
      for (final entry in _picked.entries) {
        if (entry.value.isEmpty) continue;
        await repo.submitReview(
          widget.matchId,
          revieweeId: entry.key,
          optionCodes: entry.value.toList(),
        );
      }
      if (!mounted) return;
      widget.onDone();
    } catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow({
    required this.who,
    required this.options,
    required this.open,
    required this.picked,
    required this.onToggleOpen,
    required this.onToggle,
  });

  final String who;
  final List<ReviewOption> options;
  final bool open;
  final Set<String> picked;
  final VoidCallback onToggleOpen;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: kSheetBox,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            GestureDetector(
              onTap: onToggleOpen,
              behavior: HitTestBehavior.opaque,
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      who,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: kSheetBoxInk,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  // 몇 개 골랐는지 — 접혀 있어도 고른 것이 있다는 게 보인다.
                  if (picked.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: Text(
                        '${picked.length}개',
                        style: const TextStyle(
                          color: kSheetGreen,
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  Icon(
                    open ? Icons.expand_less : Icons.expand_more,
                    size: 20,
                    color: kSheetBoxInk.withValues(alpha: 0.5),
                  ),
                ],
              ),
            ),
            if (open) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  // 🔴 **순서를 건드리지 않는다** — 서버가 준 그대로다(계약).
                  for (final o in options)
                    _OptionChip(
                      option: o,
                      on: picked.contains(o.code),
                      onTap: () => onToggle(o.code),
                    ),
                ],
              ),
            ],
          ],
        ),
      );
}

class _OptionChip extends StatelessWidget {
  const _OptionChip({
    required this.option,
    required this.on,
    required this.onTap,
  });

  final ReviewOption option;
  final bool on;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    /* 🔴 **「주의」는 색을 가른다** — 좋은 평가와 같은 모습이면 잘못 누른다.
       고른 뒤에야 다르면 이미 늦다. */
    final tint = option.isCaution ? const Color(0xFF9E2B2B) : kSheetGreen;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 140),
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
          color: on ? tint.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: on ? tint : kSheetBoxInk.withValues(alpha: 0.22),
          ),
        ),
        child: Text(
          option.label,
          style: TextStyle(
            color: on ? tint : kSheetBoxInk.withValues(alpha: 0.75),
            fontSize: 12.5,
            fontWeight: on ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }
}

/// 그 화면의 **할 일 하나** — 테가 돈다.
class _PrimaryButton extends StatelessWidget {
  const _PrimaryButton({
    required this.label,
    required this.onTap,
    this.enabled = true,
  });

  final String label;
  final VoidCallback onTap;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final body = Container(
      alignment: Alignment.center,
      padding: const EdgeInsets.symmetric(vertical: 13),
      child: Text(
        label,
        style: TextStyle(
          color: enabled ? kSheetOn : kSheetOn.withValues(alpha: 0.35),
          fontSize: 14.5,
          fontWeight: FontWeight.w700,
        ),
      ),
    );

    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: enabled
          ? SilverSweepBorder(radius: 14, strokeWidth: 1, child: body)
          : DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: kSheetEdge, width: kSheetEdgeWidth),
              ),
              child: body,
            ),
    );
  }
}
