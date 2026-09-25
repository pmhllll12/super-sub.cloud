import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/match_providers.dart';
import '../../data/models/open_match.dart';
import '../../data/regions.dart';
import '../../match_prefs.dart';
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
Future<void> showTeamSeekSheet(BuildContext context) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _TeamSeekSheet(),
    );

class _TeamSeekSheet extends ConsumerStatefulWidget {
  const _TeamSeekSheet();

  @override
  ConsumerState<_TeamSeekSheet> createState() => _TeamSeekSheetState();
}

class _TeamSeekSheetState extends ConsumerState<_TeamSeekSheet> {
  bool? _editing;
  MatchPrefs? _prefs;

  /// 목록을 좁히는 지역. `null` 이면 전체다.
  String? _region;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(myPrefsProvider);
    final prefs = _prefs ?? async.value;
    // 🔴 `null` 과 빈 조건을 가른다 — 「처음이라 물어야 하는가」가 그 차이다.
    final editing = _editing ?? (async.hasValue && prefs == null);

    return SheetShell(
      title: editing ? '내 경기 조건' : '사람을 찾는 팀',
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

  /// 🔴 **셋 다 있어야 찾을 수 있다** — 자리를 안 고르면 어느 모집에 맞는지
  /// 알 수가 없다(팀 조건은 둘만 본다 — 거기엔 자리가 없다).
  bool get _ready =>
      _regions.isNotEmpty && _times.isNotEmpty && _positions.isNotEmpty;

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
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          _times[i].text,
                          style: const TextStyle(
                            color: kSheetBoxInk,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: () => setState(() => _times.removeAt(i)),
                        icon: const Icon(Icons.close,
                            size: 18, color: kSheetBoxInk),
                      ),
                    ],
                  ),
                ),
              _Outline(
                key: const Key('seek-add-time'),
                label: '+ 시간 추가',
                // 토요일 09:00~11:00 — 팀 조건 폼과 같은 첫 값이다.
                onTap: () => setState(() => _times
                    .add(const TimeSlot(day: 6, from: '09:00', to: '11:00'))),
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
        _Primary(
          label: '팀 찾기',
          enabled: _ready,
          onTap: () => widget.onDone(
            MatchPrefs(
              regions: _regions,
              times: _times,
              positions: _positions,
            ),
          ),
        ),
        if (!_ready)
          const Padding(
            padding: EdgeInsets.only(top: 10),
            child: Text(
              '동네 · 시간 · 자리를 하나씩은 골라야 찾을 수 있습니다.',
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
              _Outline(label: '설정 수정', onTap: onEdit),
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
                  ),
          ),
        ),
      ],
    );
  }
}

class _MatchRow extends StatelessWidget {
  const _MatchRow({required this.match});

  final OpenMatch match;

  @override
  Widget build(BuildContext context) {
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
        ],
      ),
    );
  }
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
            Text(label,
                style: const TextStyle(color: kSheetBoxInk, fontSize: 12.5)),
            const SizedBox(width: 3),
            GestureDetector(
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
