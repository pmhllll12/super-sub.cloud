import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/data/models/team_membership.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../team/data/regions.dart';
import '../../../team/data/team_providers.dart';
import '../../../team/data/team_repository.dart';

/// 팀을 만들거나 고친다. [team] 이 `null` 이면 만들기.
void showTeamSheet(BuildContext context, {TeamMembership? team}) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => _TeamSheet(team: team),
  );
}

class _TeamSheet extends ConsumerStatefulWidget {
  const _TeamSheet({this.team});

  final TeamMembership? team;

  @override
  ConsumerState<_TeamSheet> createState() => _TeamSheetState();
}

class _TeamSheetState extends ConsumerState<_TeamSheet> {
  late final _name = TextEditingController(text: widget.team?.name ?? '');
  late final _region = TextEditingController(text: widget.team?.region ?? '');

  bool _busy = false;
  String? _error;

  bool get _editing => widget.team != null;

  @override
  void dispose() {
    _name.dispose();
    _region.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final repo = ref.read(teamRepositoryProvider);
      if (_editing) {
        await repo.updateTeam(
          widget.team!.teamId,
          name: _name.text.trim(),
          region: _region.text.trim(),
        );
      } else {
        await repo.createTeam(
          name: _name.text.trim(),
          region: _region.text.trim(),
        );
      }
      /* 🔴 **소속은 `GET /me` 가 준다** — 팀을 만들거나 고쳤으면 그쪽을 다시
         읽어야 프로필의 「소속」 칸이 따라온다. 화면이 제 목록을 따로 들고
         있으면 서버와 두 벌이 된다. */
      await ref.read(sessionControllerProvider.notifier).refreshMe();
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(_editing ? '팀 고치기' : '팀 만들기'),
          const SizedBox(height: 12),
          TextField(
            key: const Key('team-name'),
            controller: _name,
            enabled: !_busy,
            maxLength: kMaxTeamName,
            decoration: const InputDecoration(
              labelText: '팀 이름',
              counterText: '',
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          _RegionField(
            controller: _region,
            enabled: !_busy,
            onChanged: () => setState(() {}),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              key: const Key('team-error'),
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('team-save'),
            /* 🔴 **지역이 목록의 값일 때만 눌린다.** 자유롭게 적은 값을 받으면
               저장은 되는데 **남의 검색에서 이 팀이 빠진다** — 지역 거르기가
               글자 비교라서다. 그래서 보내기 전에 막는다. */
            onPressed: (_busy ||
                    _name.text.trim().isEmpty ||
                    !isRegion(_region.text))
                ? null
                : _save,
            child: _busy
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(_editing ? '저장' : '만들기'),
          ),
        ],
      ),
    );
  }
}

/// 지역 칸 — **적는 것은 자유지만 고르는 것은 목록에서**.
///
/// 🔴 웹 `RegionField` 와 같은 판단이다. 「강남」·「강남구」·「서울 강남구」가
/// 다 다른 값으로 저장되면 대조가 통째로 깨진다.
class _RegionField extends StatelessWidget {
  const _RegionField({
    required this.controller,
    required this.enabled,
    required this.onChanged,
  });

  final TextEditingController controller;
  final bool enabled;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    final picked = isRegion(controller.text);
    final hits = searchRegions(controller.text, limit: 8);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          key: const Key('team-region'),
          controller: controller,
          enabled: enabled,
          decoration: InputDecoration(
            labelText: '지역',
            hintText: '예: 서울 마포구',
            // 🔴 왜 아무거나 못 쓰는지 말해 준다 — 안 말하면 「왜 저장이 안
            //    되지」로 읽힌다.
            helperText: picked ? null : '아래에서 골라 주세요',
            suffixIcon: picked ? const Icon(Icons.check, size: 18) : null,
          ),
          onChanged: (_) => onChanged(),
        ),
        // 고른 뒤에는 후보를 접는다 — 다 고르고도 목록이 남아 있으면 판이 길다.
        if (enabled && !picked)
          Wrap(
            spacing: 6,
            children: [
              for (final r in hits)
                ActionChip(
                  key: Key('team-region-$r'),
                  label: Text(r, style: const TextStyle(fontSize: 12)),
                  onPressed: () {
                    controller.text = r;
                    onChanged();
                  },
                ),
            ],
          ),
      ],
    );
  }
}
