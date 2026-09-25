import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/match_providers.dart';
import '../../data/models/open_match.dart';
import '../../data/regions.dart';
import '../../match_prefs.dart';
import '../widgets/slot_editor.dart';
import 'sheet_skin.dart';

/// 「사람을 찾는 팀」 — 웹 `TeamSeek.tsx` 를 옮긴 것이다.
///
/// 🔴 **팀 없는 사람의 입구다.** `GET /matches` 는 **팀 id 를 몰라도 되는
/// 유일한 경로**라(계약 3-4절), 이것이 없으면 용병이 지원할 경기를 찾을
/// 방법이 아예 없다.
///
/// 🔴 **조건은 내 것이다** — 팀 조건과 **저장소가 다르다**(계약 3-13절).
/// 같은 사람이 팀장이면서 팀원일 수 있어 절대 안 섞는다. 여기에만 **내 자리**가
/// 있고, 그 자리가 곧 남의 AI 추천 판에 뜨는 첫 하드 필터다.
/// 🔴 **시트가 아니라 판 안에 바로 선다** (2026-09-25 사용자: 「굳이 한 번
/// 더 눌러서 팀 찾아야 해? 그냥 팀원 누르자마자 ... 그 판에 설정 할 수 있게」).
/// 「팀원」을 누르면 그 자리가 곧 이 판이다 — 한 번 더 누르게 하지 않는다.
class TeamSeekPanel extends ConsumerStatefulWidget {
  const TeamSeekPanel({super.key});

  @override
  ConsumerState<TeamSeekPanel> createState() => _TeamSeekPanelState();
}

class _TeamSeekPanelState extends ConsumerState<TeamSeekPanel> {
  bool? _editing;
  MatchPrefs? _prefs;

  /// 목록을 좁히는 지역. `null` 이면 전체다.
  String? _region;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(myPrefsProvider);
    final prefs = _prefs ?? async.value;
    /* 🔴 **목록이 먼저다** (2026-09-25 정정 — 사용자: 「다 지우면 모든 팀들이
       나와야지」). 조건은 **좁히는 것**이지 들어가는 문이 아니다.

       ⚠️ 전에는 조건이 없으면 폼을 먼저 띄웠는데, 그러면 **다 지운 사람이
       목록을 못 본다.** 게다가 「셋 다 차야 저장」이라 지운 것을 저장할 길이
       없어서, 다른 데 갔다 오면 옛 값이 되살아났다. */
    final editing = _editing ?? false;

    /* ⚠️ **검정 면을 깔지 않는다** (2026-09-25 정정 — 사용자: 「대체 검정
       판은 또 왜 쳐 넣은거야?」). 이 자리는 홈의 유리 판 **안**이라 뒤가
       이미 서 있다 — 한 겹 더 깔면 그 자리만 딴 재질로 읽힌다. */
    return Padding(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
            child: Text(
              editing ? '내 경기 조건' : '사람을 찾는 팀',
              style: const TextStyle(
                color: kSheetOn,
                fontSize: 15,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: async.isLoading && _prefs == null
                ? const Center(child: SheetSpinner())
                : editing
                    ? _MyPrefsForm(
                        initial: prefs ?? const MatchPrefs(),
                        onDone: _save,
                      )
                    : _OpenMatchList(
                        region: _region,
                        onRegion: (r) => setState(() => _region = r),
                        onEdit: () => setState(() => _editing = true),
                      ),
          ),
        ],
      ),
    );
  }

  Future<void> _save(MatchPrefs next) async {
    try {
      await ref.read(matchRepositoryProvider).saveMyPrefs(next);
      if (!mounted) return;
      setState(() {
        _prefs = next;
        _editing = false;
      });
      /* 🔴 **provider 도 새로 읽게 둔다** — 지역 알약이 조건에서 오므로,
         안 그러면 지운 지역이 알약으로 남는다. */
      ref.invalidate(myPrefsProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}

// ── 내 조건 ───────────────────────────────────────────────────────────────

class _MyPrefsForm extends ConsumerStatefulWidget {
  const _MyPrefsForm({required this.initial, required this.onDone});

  final MatchPrefs initial;
  final ValueChanged<MatchPrefs> onDone;

  @override
  ConsumerState<_MyPrefsForm> createState() => _MyPrefsFormState();
}

class _MyPrefsFormState extends ConsumerState<_MyPrefsForm> {
  late final List<String> _regions = [...widget.initial.regions];
  late final List<TimeSlot> _times = [...widget.initial.times];
  late final List<String> _positions = [...widget.initial.positions];
  final _region = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _region.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final codes = ref.watch(matchPositionsProvider).value ?? const [];

    return ListView(
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
                controller: _region,
                onChanged: (v) => setState(() => _query = v.trim()),
                style: const TextStyle(color: kSheetBoxInk, fontSize: 14.5),
                cursorColor: kSheetBoxInk,
                decoration: sheetInput('동네 이름을 적으세요'),
              ),
              for (final r in searchRegions(_query, limit: 5))
                if (!_regions.contains(r))
                  InkWell(
                    key: Key('seek-region-$r'),
                    onTap: () => setState(() {
                      _regions.add(r);
                      _region.clear();
                      _query = '';
                    }),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 9),
                      child: Text(
                        r,
                        style: TextStyle(
                          color: kSheetBoxInk.withValues(alpha: 0.8),
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ),
              if (_regions.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final r in _regions)
                        _Chip(
                          dropKey: Key('seek-drop-region-$r'),
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
              /* 🔴 **고르는 칸은 팀 조건 폼과 한 벌이다**(`slot_editor.dart`).
                 여기엔 한때 **고를 칸이 아예 없었고** 토요일 09:00~11:00 이
                 박혀 있었다 — 사용자가 「왜 토요일과 시간대가 고정이야」로
                 잡았다(2026-09-25). */
              for (var i = 0; i < _times.length; i++)
                SlotEditor(
                  removeKey: Key('seek-drop-time-$i'),
                  slot: _times[i],
                  onChanged: (v) => setState(() => _times[i] = v),
                  onRemove: () => setState(() => _times.removeAt(i)),
                ),
              _Outline(
                key: const Key('seek-add-time'),
                label: '+ 시간 추가',
                // 🔴 첫 값은 **오늘 요일 · 다음 칸**이다(요일을 안 박는다).
                onTap: () => setState(() => _times.add(defaultSlot())),
              ),
            ],
          ),
        ),
        _Field(
          /* 🔴 **여기에만 있는 칸이다.** 팀 조건에는 자리가 없다(계약이 개인
             조건에만 둔다) — 여기 올린 자리가 곧 남의 AI 추천 판에 뜨는 첫
             하드 필터다. */
          label: '내 자리',
          child: Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final p in codes)
                _PosChip(
                  key: Key('seek-pos-${p.label}'),
                  label: p.label,
                  on: _positions.contains(p.label),
                  onTap: () => setState(() {
                    _positions.contains(p.label)
                        ? _positions.remove(p.label)
                        : _positions.add(p.label);
                  }),
                ),
            ],
          ),
        ),
        const SizedBox(height: 6),
        /* 🔴 **비어 있어도 저장된다** (2026-09-25 사용자: 「설정 다 지웠어도
           저장할 수 있게 해야지」). 전에는 셋이 다 차야 눌렸고, 그래서 **지운
           것을 저장할 길이 없었다** — 다른 데 갔다 오면 옛 값이 되살아났다. */
        _Primary(
          label: '저장',
          enabled: true,
          onTap: () => widget.onDone(
            MatchPrefs(
              regions: _regions,
              times: _times,
              positions: _positions,
            ),
          ),
        ),
        const Padding(
          padding: EdgeInsets.only(top: 10),
          child: Text(
            '비워 두면 좁히지 않고 전부 보여 줍니다.',
            style: TextStyle(color: kSheetOnDim, fontSize: 12.5),
          ),
        ),
      ],
    );
  }
}

// ── 사람을 찾는 팀 ─────────────────────────────────────────────────────────

class _OpenMatchList extends ConsumerWidget {
  const _OpenMatchList({
    required this.region,
    required this.onRegion,
    required this.onEdit,
  });

  final String? region;
  final ValueChanged<String?> onRegion;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(openMatchesProvider(OpenMatchQuery(region: region)));
    final mine = ref.watch(myPrefsProvider).value?.regions ?? const <String>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
          child: Row(
            children: [
              _Outline(label: '설정', onTap: onEdit),
              const SizedBox(width: 8),
              /* 🔴 **지역은 서버로 보낸다** — 받아 놓고 화면에서 거르면 다음
                 쪽을 못 가져온다(목록이 페이지로 온다). */
              Expanded(
                child: SizedBox(
                  height: 34,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      _FilterChip(
                        label: '전체',
                        on: region == null,
                        onTap: () => onRegion(null),
                      ),
                      for (final r in mine) ...[
                        const SizedBox(width: 6),
                        _FilterChip(
                          key: Key('seek-filter-$r'),
                          label: r,
                          on: region == r,
                          onTap: () => onRegion(r),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: async.when(
            loading: () => const Center(child: SheetSpinner()),
            error: (e, _) => Center(
              child: SheetMessage(title: '경기를 불러오지 못했습니다', detail: '$e'),
            ),
            data: (list) => list.isEmpty
                ? const Center(
                    child: SheetMessage(
                      title: '지금 사람을 찾는 팀이 없습니다',
                      detail: '동네를 넓히거나 조금 뒤에 다시 보세요.',
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
                    itemCount: list.length,
                    itemBuilder: (_, i) => _MatchRow(match: list[i]),
                    // 🔴 위 `_MatchRow` 가 제 지원 상태를 들고 있다.
                  ),
          ),
        ),
      ],
    );
  }
}

/// 🔴 **지원 상태를 줄마다 들고 있다** (2026-09-25 사용자 요청: 「사람을
/// 찾는팀 지원 단추 하고」).
///
/// ⚠️ **다시 열면 잊는다.** `GET /matches` 의 한 줄에는 **내가 지원했는지**가
/// 안 실려 온다(계약 3-4절). 경기마다 `GET …/applications` 를 한 번씩 부르면
/// 목록 하나에 왕복이 스무 번이라 그 길로 가지 않았다.
/// 🔴 **서버가 `my_application` 을 실어 주면** 이 상태를 걷고 그 값을 쓴다 —
/// 미결 항목에 올려 둔다.
class _MatchRow extends ConsumerStatefulWidget {
  const _MatchRow({required this.match});

  final OpenMatch match;

  @override
  ConsumerState<_MatchRow> createState() => _MatchRowState();
}

class _MatchRowState extends ConsumerState<_MatchRow> {
  /// 낸 지원의 id — 있으면 「지원함」이다. 무르려면 이 값이 있어야 한다.
  String? _applicationId;

  /// 이미 지원한 것이 **확인됐지만 id 를 모를 때** 참(409 `ALREADY_APPLIED`).
  /// 🔴 그때는 무를 길이 없다 — 지원 id 를 서버가 안 알려 주기 때문이다.
  bool _alreadyApplied = false;

  bool _busy = false;
  String? _error;

  Future<void> _apply() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final made =
          await ref.read(matchRepositoryProvider).apply(widget.match.id);
      if (mounted) setState(() => _applicationId = made.id);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        /* 🔴 **막힌 까닭을 그대로 말한다.** 셋이 아주 다른 상황이라
           「지원하지 못했습니다」 하나로 뭉뚱그리면 무엇을 해야 할지 모른다. */
        _error = switch (e.code) {
          'ALREADY_APPLIED' => '이미 지원한 경기입니다.',
          'TEAM_MEMBER_CANNOT_APPLY' => '내가 속한 팀의 경기입니다.',
          'PAST_MATCH' => '이미 지난 경기입니다.',
          _ => e.message,
        };
        if (e.code == 'ALREADY_APPLIED') _alreadyApplied = true;
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _withdraw() async {
    final id = _applicationId;
    if (id == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(matchRepositoryProvider)
          .withdraw(widget.match.id, applicationId: id);
      // 🔴 **행을 지운 것이라 다시 지원할 수 있다**(계약 A-1).
      if (mounted) setState(() => _applicationId = null);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final match = widget.match;
    final at = DateTime.tryParse(match.playedAt);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: kSheetBox,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            match.teamName,
            style: const TextStyle(
              color: kSheetBoxInk,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            [
              match.region,
              if (at != null)
                '${at.month}월 ${at.day}일 '
                    '${at.hour.toString().padLeft(2, '0')}:'
                    '${at.minute.toString().padLeft(2, '0')}',
              match.place,
            ].where((s) => s.isNotEmpty).join(' · '),
            style: TextStyle(
              color: kSheetBoxInk.withValues(alpha: 0.65),
              fontSize: 12.5,
            ),
          ),
          /* 🔴 **찾는 자리를 서버가 준 이름 그대로** 적는다 — 약칭으로
             「골키퍼」를 지어내지 않는다(약칭이 종목을 넘나든다).
             ⚠️ **빈 배열도 정상이다** — 팀 대 팀으로 잡힌 경기는 모집이
             없다(계약 3-15절). 그때는 아무것도 안 그린다. */
          if (match.needs.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 9),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final n in match.needs)
                    _NeedChip(text: '${n.positionLabel} ${n.headCount}자리'),
                ],
              ),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                _error!,
                style: const TextStyle(color: Color(0xFFB42318), fontSize: 12),
              ),
            ),
          const SizedBox(height: 10),
          /* 🔴 **오른쪽 끝에 붙인다** — 줄의 내용은 왼쪽에서 읽고, 하는 일은
             오른쪽에서 누른다(이 시트의 다른 줄들과 같은 자리다). */
          Align(
            alignment: Alignment.centerRight,
            child: _applicationId != null
                ? _ApplyPill(
                    pillKey: Key('seek-withdraw-${match.id}'),
                    label: _busy ? '무르는 중…' : '지원 취소',
                    filled: false,
                    onTap: _busy ? null : _withdraw,
                  )
                : _ApplyPill(
                    pillKey: Key('seek-apply-${match.id}'),
                    label: _alreadyApplied
                        ? '지원함'
                        : _busy
                            ? '보내는 중…'
                            : '지원하기',
                    filled: true,
                    // 🔴 이미 지원했으면 **누를 것이 없다**(무를 id 를 모른다).
                    onTap: _busy || _alreadyApplied ? null : _apply,
                  ),
          ),
        ],
      ),
    );
  }
}

/// 줄 오른쪽의 작은 알약 — 지원 / 지원 취소.
class _ApplyPill extends StatelessWidget {
  const _ApplyPill({
    required this.pillKey,
    required this.label,
    required this.filled,
    required this.onTap,
  });

  final Key pillKey;
  final String label;
  final bool filled;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Opacity(
        opacity: onTap == null ? 0.5 : 1,
        child: GestureDetector(
          key: pillKey,
          onTap: onTap,
          behavior: HitTestBehavior.opaque,
          child: Container(
            height: 34,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: filled ? kSheetGreen : Colors.transparent,
              border: Border.all(
                color: filled ? kSheetGreen : kSheetBoxInk.withValues(alpha: 0.3),
              ),
              borderRadius: BorderRadius.circular(17),
            ),
            child: Text(
              label,
              style: TextStyle(
                color: filled ? Colors.white : kSheetBoxInk,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ),
      );
}

// ── 조각들 ────────────────────────────────────────────────────────────────

class _NeedChip extends StatelessWidget {
  const _NeedChip({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: kSheetGreen.withValues(alpha: 0.1),
          border: Border.all(color: kSheetGreen.withValues(alpha: 0.5)),
        ),
        child: Text(
          text,
          style: const TextStyle(
            color: kSheetGreen,
            fontSize: 11.5,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
}

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

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.onRemove,
    this.dropKey,
  });

  final String label;
  final VoidCallback onRemove;

  /// 지우기 단추의 열쇠 — 🔴 **바깥 알약이 아니라 그 단추에 둔다**(둘 다
  /// 같은 열쇠면 시험이 어느 쪽을 누를지 모른다).
  final Key? dropKey;

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
            Text(label,
                style: const TextStyle(color: kSheetBoxInk, fontSize: 12.5)),
            const SizedBox(width: 3),
            GestureDetector(
              key: dropKey,
              onTap: onRemove,
              child: Icon(Icons.close,
                  size: 15, color: kSheetBoxInk.withValues(alpha: 0.55)),
            ),
          ],
        ),
      );
}

class _PosChip extends StatelessWidget {
  const _PosChip({
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
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            color: on ? kSheetGreen.withValues(alpha: 0.12) : null,
            border: Border.all(
              color: on ? kSheetGreen : kSheetBoxInk.withValues(alpha: 0.28),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: on ? kSheetGreen : kSheetBoxInk.withValues(alpha: 0.8),
              fontSize: 13,
              fontWeight: on ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ),
      );
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
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
        child: Container(
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: on ? kSheetSilver : kSheetEdge,
              width: kSheetEdgeWidth,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: on ? kSheetOn : kSheetOn.withValues(alpha: 0.6),
              fontSize: 12.5,
              fontWeight: on ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ),
      );
}

class _Outline extends StatelessWidget {
  const _Outline({super.key, required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: kSheetOn.withValues(alpha: 0.4)),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: kSheetOn.withValues(alpha: 0.9),
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      );
}

class _Primary extends StatelessWidget {
  const _Primary({
    required this.label,
    required this.enabled,
    required this.onTap,
  });

  final String label;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: enabled ? onTap : null,
        child: Container(
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(vertical: 13),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: enabled ? kSheetSilver : kSheetEdge,
              width: enabled ? 1 : kSheetEdgeWidth,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: enabled ? kSheetOn : kSheetOn.withValues(alpha: 0.35),
              fontSize: 14.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      );
}
