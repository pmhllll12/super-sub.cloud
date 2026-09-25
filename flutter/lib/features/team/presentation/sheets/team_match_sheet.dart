import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/widgets/silver_edge.dart';
import '../../../../core/widgets/silver_sweep_border.dart';
import '../../data/match_providers.dart';
import '../../data/models/match_candidate.dart';
import '../../data/regions.dart';
import '../../match_prefs.dart';
import '../../match_proposal.dart';
import '../../venues.dart';
import 'sheet_skin.dart';

/// 「팀 매칭」 — 조건을 정하고 **비슷한 팀**에 경기를 건다.
///
/// 🔴 **두 화면이 한 시트에 있다.** 조건을 한 번도 안 정했으면 조건 폼이
/// 먼저 뜨고(웹 `MatchPrefs.tsx`), 정해져 있으면 바로 팀 목록이다
/// (웹 `TeamMatch.tsx`). 폰에서는 이 둘을 오가느라 시트가 닫혔다 열리는 것이
/// 더 어수선해서 한 자리에 뒀다.
///
/// 돌려주는 값은 **걸린 신청**이다 — `null` 이면 아무것도 안 걸고 닫았다.
/// 🔴 **「걸었다」이지 「잡혔다」가 아니다.** 확정은 상대가 수락하는 순간이고
/// 그것은 부르는 쪽이 기다린다.
Future<TeamMatchRequest?> showTeamMatchSheet(
  BuildContext context, {
  required String teamId,
}) =>
    showModalBottomSheet<TeamMatchRequest>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _TeamMatchSheet(teamId: teamId),
    );

class _TeamMatchSheet extends ConsumerStatefulWidget {
  const _TeamMatchSheet({required this.teamId});

  final String teamId;

  @override
  ConsumerState<_TeamMatchSheet> createState() => _TeamMatchSheetState();
}

class _TeamMatchSheetState extends ConsumerState<_TeamMatchSheet> {
  /// 조건을 **지금 고치는 중**인가. 처음 열 때는 조건이 없으면 참이 된다.
  bool? _editing;

  MatchPrefs? _prefs;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(teamPrefsProvider(widget.teamId));
    final prefs = _prefs ?? async.value;
    // 🔴 **`null` 과 빈 조건을 가른다** — 「처음이라 물어야 하는가」가 그
    //    차이로 정해진다.
    final editing = _editing ?? (async.hasValue && prefs == null);

    return SheetShell(
      title: editing ? '경기 조건' : '비슷한 팀',
      child: async.isLoading && _prefs == null
          ? const Center(child: SheetSpinner())
          : editing
              ? _PrefsForm(
                  initial: prefs ?? const MatchPrefs(),
                  onDone: _save,
                )
              : _CandidateList(
                  teamId: widget.teamId,
                  prefs: prefs ?? const MatchPrefs(),
                  onEdit: () => setState(() => _editing = true),
                ),
    );
  }

  Future<void> _save(MatchPrefs next) async {
    try {
      await ref.read(matchRepositoryProvider).saveTeamPrefs(widget.teamId, next);
      if (!mounted) return;
      setState(() {
        _prefs = next;
        _editing = false;
      });
      ref.invalidate(matchCandidatesProvider(widget.teamId));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}

// ── 조건 폼 ───────────────────────────────────────────────────────────────

class _PrefsForm extends StatefulWidget {
  const _PrefsForm({required this.initial, required this.onDone});

  final MatchPrefs initial;
  final ValueChanged<MatchPrefs> onDone;

  @override
  State<_PrefsForm> createState() => _PrefsFormState();
}

class _PrefsFormState extends State<_PrefsForm> {
  late final List<String> _regions = [...widget.initial.regions];
  late final List<TimeSlot> _times = [...widget.initial.times];
  final _region = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _region.dispose();
    super.dispose();
  }

  /// 🔴 **둘 다 있어야 찾을 수 있다** — 하나라도 비면 「비슷하다」를 판단할
  /// 근거가 없다.
  bool get _ready => _regions.isNotEmpty && _times.isNotEmpty;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
        children: [
          const Padding(
            padding: EdgeInsets.only(bottom: 14),
            child: Text(
              '어떤 경기를 찾으세요?',
              style: TextStyle(
                color: kSheetOn,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          _Field(
            label: '어느 동네에서',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  key: const Key('match-region'),
                  controller: _region,
                  onChanged: (v) => setState(() => _query = v.trim()),
                  style: const TextStyle(color: kSheetBoxInk, fontSize: 14.5),
                  cursorColor: kSheetBoxInk,
                  decoration: sheetInput('동네 이름을 적으세요'),
                ),
                /* 🔴 **저장되는 값은 목록의 것이다**(`regions.dart` 머리말).
                   자유 입력을 그대로 두면 「강남구」·「서울 강남구」가 다른
                   값이 되어 대조가 통째로 깨진다. */
                for (final r in searchRegions(_query, limit: 5))
                  if (!_regions.contains(r))
                    _SuggestRow(label: r, onTap: () => _addRegion(r)),
                if (_regions.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final r in _regions)
                          _Chip(
                            label: r,
                            onRemove: () => setState(() => _regions.remove(r)),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          _Field(
            label: '언제',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var i = 0; i < _times.length; i++)
                  _SlotRow(
                    slot: _times[i],
                    onChanged: (s) => setState(() => _times[i] = s),
                    onRemove: () => setState(() => _times.removeAt(i)),
                  ),
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: _OutlineButton(
                    key: const Key('match-add-time'),
                    label: '+ 시간 추가',
                    onTap: () => setState(
                      () => _times.add(
                        // 토요일 09:00~11:00 — 웹과 같은 첫 값이다.
                        const TimeSlot(day: 6, from: '09:00', to: '11:00'),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          _PrimaryButton(
            label: '팀 찾기',
            enabled: _ready,
            onTap: () => widget.onDone(
              MatchPrefs(regions: _regions, times: _times),
            ),
          ),
          if (!_ready)
            const Padding(
              padding: EdgeInsets.only(top: 10),
              child: Text(
                '동네와 시간을 하나씩은 골라야 찾을 수 있습니다.',
                style: TextStyle(color: kSheetOnDim, fontSize: 12.5),
              ),
            ),
        ],
      );

  void _addRegion(String r) {
    setState(() {
      _regions.add(r);
      _region.clear();
      _query = '';
    });
  }
}

class _SlotRow extends StatelessWidget {
  const _SlotRow({
    required this.slot,
    required this.onChanged,
    required this.onRemove,
  });

  final TimeSlot slot;
  final ValueChanged<TimeSlot> onChanged;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            _Picker<int>(
              value: slot.day,
              items: [for (var d = 0; d < 7; d++) (d, kDays[d])],
              onChanged: (d) => onChanged(
                TimeSlot(day: d, from: slot.from, to: slot.to),
              ),
            ),
            const SizedBox(width: 6),
            _Picker<String>(
              value: slot.from,
              items: [for (final h in kHours) (h, h)],
              onChanged: (h) => onChanged(
                TimeSlot(
                  day: slot.day,
                  from: h,
                  // 🔴 시작이 끝을 넘으면 서버가 422 로 막는다 — 넘기 전에
                  //    끝을 함께 민다.
                  to: h.compareTo(slot.to) >= 0 ? _nextHour(h) : slot.to,
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 4),
              child: Text('~', style: TextStyle(color: kSheetOnDim)),
            ),
            _Picker<String>(
              value: slot.to,
              // 끝은 시작보다 뒤만 고를 수 있다.
              items: [
                for (final h in kHours)
                  if (h.compareTo(slot.from) > 0) (h, h),
              ],
              onChanged: (h) => onChanged(
                TimeSlot(day: slot.day, from: slot.from, to: h),
              ),
            ),
            const Spacer(),
            IconButton(
              tooltip: '지우기',
              onPressed: onRemove,
              icon: const Icon(Icons.close, size: 18, color: kSheetOnDim),
            ),
          ],
        ),
      );

  static String _nextHour(String h) {
    final i = kHours.indexOf(h);
    return i < 0 || i + 1 >= kHours.length ? kHours.last : kHours[i + 1];
  }
}

// ── 비슷한 팀 ─────────────────────────────────────────────────────────────

class _CandidateList extends ConsumerStatefulWidget {
  const _CandidateList({
    required this.teamId,
    required this.prefs,
    required this.onEdit,
  });

  final String teamId;
  final MatchPrefs prefs;
  final VoidCallback onEdit;

  @override
  ConsumerState<_CandidateList> createState() => _CandidateListState();
}

class _CandidateListState extends ConsumerState<_CandidateList> {
  /// 지금 펼쳐 둔 팀 — 시각·구장을 고르는 칸이 그 아래 열린다.
  String? _open;
  Proposal? _when;
  Venue? _where;
  bool _sending = false;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(matchCandidatesProvider(widget.teamId));
    /* 🔴 **이미 건 팀은 잠근다**(2026-09-25 사용자 요청). 계약도 같은 상대에
       겹쳐 거는 것을 409 로 막으므로, 눌리게 두면 오류만 보게 된다. */
    final live = ref.watch(liveRequestsProvider(widget.teamId)).value ?? const {};
    final proposals = proposalsFrom(widget.prefs.times);
    final venues = venuesFor(widget.prefs.regions);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
          child: _OutlineButton(label: '설정 수정', onTap: widget.onEdit),
        ),
        Expanded(
          child: async.when(
            loading: () => const Center(child: SheetSpinner()),
            error: (e, _) => Center(
              child: SheetMessage(title: '후보를 불러오지 못했습니다', detail: '$e'),
            ),
            data: (list) => list.isEmpty
                ? const Center(
                    child: SheetMessage(
                      title: '지금은 맞는 팀이 없습니다',
                      detail: '동네나 시간을 넓히면 더 보입니다.',
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
                    itemCount: list.length,
                    itemBuilder: (_, i) => _CandidateRow(
                      team: list[i],
                      request: live[list[i].teamId],
                      onCancel: _cancel,
                      /* 🔴 **잡힌 경기는 거기서 끝이 아니다**(2026-09-25
                         사용자 요청). 누르면 그 신청을 돌려주고, 부르는 쪽이
                         경기 화면을 연다 — 신청 직후와 **같은 길**이다. */
                      onOpenMatch: (r) => Navigator.of(context).pop(r),
                      open: _open == list[i].teamId,
                      proposals: proposals,
                      venues: venues,
                      when: _when,
                      where: _where,
                      sending: _sending,
                      onToggle: () => setState(() {
                        _open = _open == list[i].teamId ? null : list[i].teamId;
                        _when = proposals.isEmpty ? null : proposals.first;
                        _where = venues.isEmpty ? null : venues.first;
                      }),
                      onWhen: (p) => setState(() => _when = p),
                      onWhere: (v) => setState(() => _where = v),
                      onApply: () => _apply(list[i]),
                    ),
                  ),
          ),
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: Text(
            '신청은 상대 팀장에게 갑니다 — 수락해야 경기가 잡힙니다.',
            style: TextStyle(color: kSheetOnDim, fontSize: 12),
          ),
        ),
      ],
    );
  }

  /// 걸어 둔 신청을 무른다 — 그 팀 판은 다시 「경기 신청」이 된다.
  Future<void> _cancel(String requestId) async {
    try {
      await ref
          .read(matchRepositoryProvider)
          .cancelRequest(widget.teamId, requestId: requestId);
      if (!mounted) return;
      ref.invalidate(liveRequestsProvider(widget.teamId));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _apply(MatchCandidate team) async {
    final when = _when;
    final where = _where;
    /* 🔴 **시각과 구장은 필수다**(계약 3-15절). 시각은 **우리가 올린 조건**
       에서 만든 것이고 지어내지 않는다 — 조건이 비면 고를 것이 없다. */
    if (when == null || where == null || _sending) return;

    setState(() => _sending = true);
    try {
      final made = await ref.read(matchRepositoryProvider).requestMatch(
            widget.teamId,
            targetTeamId: team.teamId,
            playedAt: toPlayedAt(when.at),
            place: where.name,
          );
      if (!mounted) return;
      // 잠금 상태를 곧바로 반영한다 — 다시 들어와도 「수락 대기중」이다.
      ref.invalidate(liveRequestsProvider(widget.teamId));
      Navigator.of(context).pop(made);
    } catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}

class _CandidateRow extends StatelessWidget {
  const _CandidateRow({
    required this.team,
    required this.request,
    required this.onCancel,
    required this.onOpenMatch,
    required this.open,
    required this.proposals,
    required this.venues,
    required this.when,
    required this.where,
    required this.sending,
    required this.onToggle,
    required this.onWhen,
    required this.onWhere,
    required this.onApply,
  });

  final MatchCandidate team;

  /// **내가 그 팀에 걸어 둔** 신청. `null` 이면 아직 안 걸었다.
  final TeamMatchRequest? request;
  final bool open;
  final List<Proposal> proposals;
  final List<Venue> venues;
  final Proposal? when;
  final Venue? where;
  final bool sending;
  final VoidCallback onToggle;

  /// 걸어 둔 신청을 무른다.
  final ValueChanged<String> onCancel;

  /// 이미 잡힌 경기를 연다.
  final ValueChanged<TeamMatchRequest> onOpenMatch;
  final ValueChanged<Proposal> onWhen;
  final ValueChanged<Venue> onWhere;
  final VoidCallback onApply;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: kSheetBox,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                team.name,
                style: const TextStyle(
                  color: kSheetBoxInk,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                '${team.regionLabel} · ${team.formation}',
                style: TextStyle(
                  color: kSheetBoxInk.withValues(alpha: 0.6),
                  fontSize: 12.5,
                ),
              ),
              /* 🔴 **서버가 준 문장 그대로**다 — 화면이 겹침을 다시 계산하지
                 않는다(계약의 「하지 말 것」). 빈 배열도 정상이다. */
              if (team.reasons.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 9),
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final r in team.reasons) _ReasonChip(text: r.detail),
                    ],
                  ),
                ),
              const SizedBox(height: 11),
              /* 🔴 **한 번 걸었으면 못 누른다** — 「경기 신청」 그대로 두면
                 눌러 놓고 409 만 보게 된다. 무엇을 기다리는 중인지 적는다. */
              _OutlineButton(
                label: switch (request) {
                  null => open ? '접기' : '경기 신청',
                  final r when r.isAccepted => '경기가 잡혔습니다',
                  _ => '수락 대기중',
                },
                onTap: switch (request) {
                  null => onToggle,
                  final r when r.isAccepted => () => onOpenMatch(r),
                  // 아직 답을 기다리는 중 — 누를 것이 없다(아래 「신청 취소」).
                  _ => null,
                },
                onBox: true,
                dim: request != null && !request!.isAccepted,
              ),
              /* 🔴 **건 쪽이 무를 수 있어야 한다**(2026-09-25 사용자 요청).
                 상대가 답을 안 하면 그 팀이 **영영 잠긴 채**로 남는다.
                 🔴 **`pending` 일 때만**이다 — 이미 잡힌 경기는 계약이
                 `DELETE /matches/{id}` 로 따로 두었고 앱은 아직 안 붙였다. */
              if (request case final r? when r.isPending) ...[
                const SizedBox(height: 8),
                _OutlineButton(
                  label: '신청 취소',
                  onTap: () => onCancel(r.id),
                  onBox: true,
                ),
              ],
              if (open && request == null) ...[
                const SizedBox(height: 12),
                _Label('언제'),
                _Picker<Proposal>(
                  value: when,
                  items: [for (final p in proposals) (p, p.label)],
                  onChanged: onWhen,
                  onBox: true,
                ),
                const SizedBox(height: 10),
                _Label('어디서'),
                _Picker<Venue>(
                  value: where,
                  items: [for (final v in venues) (v, v.name)],
                  onChanged: onWhere,
                  onBox: true,
                ),
                const SizedBox(height: 12),
                _PrimaryButton(
                  label: sending ? '신청하는 중…' : '이 시각으로 신청',
                  enabled: !sending && when != null && where != null,
                  onTap: onApply,
                  onBox: true,
                ),
              ],
            ],
          ),
        ),
      );
}

class _ReasonChip extends StatelessWidget {
  const _ReasonChip({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: kSheetBoxInk.withValues(alpha: 0.22)),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: kSheetBoxInk.withValues(alpha: 0.75),
            fontSize: 11.5,
          ),
        ),
      );
}

// ── 조각들 ────────────────────────────────────────────────────────────────

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
        decoration: BoxDecoration(
          color: kSheetBox,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Text(
                label,
                style: const TextStyle(
                  color: kSheetBoxInk,
                  fontSize: 13.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            child,
          ],
        ),
      );
}

class _Label extends StatelessWidget {
  const _Label(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 5),
        child: Text(
          text,
          style: TextStyle(
            color: kSheetBoxInk.withValues(alpha: 0.6),
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      );
}

class _SuggestRow extends StatelessWidget {
  const _SuggestRow({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 9),
          child: Text(
            label,
            style: TextStyle(
              color: kSheetBoxInk.withValues(alpha: 0.8),
              fontSize: 14,
            ),
          ),
        ),
      );
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.onRemove});

  final String label;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.fromLTRB(11, 5, 5, 5),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: kSheetBoxInk.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: const TextStyle(color: kSheetBoxInk, fontSize: 12.5),
            ),
            const SizedBox(width: 3),
            GestureDetector(
              onTap: onRemove,
              child: Icon(
                Icons.close,
                size: 15,
                color: kSheetBoxInk.withValues(alpha: 0.55),
              ),
            ),
          ],
        ),
      );
}

/// 고르는 칸. 🔴 **폰에서는 `DropdownButton` 이 화면 위로 뜬다** — 시트 안에서
/// 도 제대로 열리므로 그대로 쓴다(`Picker` 를 따로 지어 시트를 하나 더 띄우면
/// 시트 안의 시트가 된다).
class _Picker<T> extends StatelessWidget {
  const _Picker({
    required this.value,
    required this.items,
    required this.onChanged,
    this.onBox = false,
  });

  final T? value;
  final List<(T, String)> items;
  final ValueChanged<T> onChanged;

  /// 밝은 줄 **안**인가 — 글자색이 갈린다.
  final bool onBox;

  @override
  Widget build(BuildContext context) {
    final ink = onBox ? kSheetBoxInk : kSheetOn;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: ink.withValues(alpha: 0.25)),
      ),
      child: DropdownButton<T>(
        value: value,
        isDense: true,
        /* 🔴 **폭을 판에 맞춘다.** 구장 이름이 「서울특별시 산악문화체험센터
           난지천인조잔디축구장」처럼 길어서, 안 맞추면 폭 360 짜리 폰에서
           칸이 통째로 넘친다(시험이 잡았다). */
        isExpanded: true,
        underline: const SizedBox.shrink(),
        dropdownColor: onBox ? kSheetBox : kSheetInk,
        iconEnabledColor: ink.withValues(alpha: 0.6),
        style: TextStyle(color: ink, fontSize: 13),
        items: [
          for (final (v, label) in items)
            DropdownMenuItem(
              value: v,
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: ink, fontSize: 13),
              ),
            ),
        ],
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    );
  }
}

class _OutlineButton extends StatelessWidget {
  const _OutlineButton({
    super.key,
    required this.label,
    required this.onTap,
    this.onBox = false,
    this.dim = false,
  });

  final String label;

  /// `null` 이면 **안 눌린다.**
  final VoidCallback? onTap;
  final bool onBox;
  final bool dim;

  @override
  Widget build(BuildContext context) {
    final ink = onBox ? kSheetBoxInk : kSheetOn;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        alignment: Alignment.center,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: ink.withValues(alpha: dim ? 0.18 : 0.4)),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: ink.withValues(alpha: dim ? 0.45 : 0.9),
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

/// 그 화면에서 **할 일 하나** — 고른 것만 테가 도는 규칙과 같은 결이다.
class _PrimaryButton extends StatelessWidget {
  const _PrimaryButton({
    required this.label,
    required this.enabled,
    required this.onTap,
    this.onBox = false,
  });

  final String label;
  final bool enabled;
  final VoidCallback onTap;
  final bool onBox;

  @override
  Widget build(BuildContext context) {
    final ink = onBox ? kSheetBoxInk : kSheetOn;
    final body = Container(
      alignment: Alignment.center,
      padding: const EdgeInsets.symmetric(vertical: 13),
      child: Text(
        label,
        style: TextStyle(
          color: enabled ? ink : ink.withValues(alpha: 0.35),
          fontSize: 14.5,
          fontWeight: FontWeight.w700,
        ),
      ),
    );

    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: enabled && !onBox
          ? SilverSweepBorder(radius: 14, strokeWidth: 1, child: body)
          : DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: enabled
                      ? ink.withValues(alpha: 0.5)
                      : SilverEdge.silver.withValues(alpha: 0.2),
                ),
              ),
              child: body,
            ),
    );
  }
}
