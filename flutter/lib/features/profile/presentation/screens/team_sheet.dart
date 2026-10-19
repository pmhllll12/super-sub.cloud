import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/data/models/team_membership.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../team/data/regions.dart';
import '../../../team/data/team_providers.dart';
import '../../../team/data/team_repository.dart';

/// 팀을 만들거나 고치는 폼. [team] 이 `null` 이면 만들기.
///
/// 🔴 **바텀시트가 아니라 제자리에서 펼쳐진다**(2026-09-22, 사용자 요청:
/// 「웹처럼 판이 아래로 자연스럽고 부드럽게 열리면서」). 시트는 화면을 덮어
/// **어느 팀을 고치는 중인지**가 안 보인다 — 웹의 `ss-profile-form-fold` 와
/// 같은 자리다.
class TeamForm extends ConsumerStatefulWidget {
  const TeamForm({super.key, this.team, required this.onDone});

  final TeamMembership? team;

  /// 저장이 끝났거나 접을 때.
  final VoidCallback onDone;

  @override
  ConsumerState<TeamForm> createState() => _TeamFormState();
}

class _TeamFormState extends ConsumerState<TeamForm> {
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
      if (mounted) widget.onDone();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
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
          const SizedBox(height: 12),
          /* 🔴 **세로로 쌓는다**(2026-09-22). 반쪽 폭에서 둘을 한 줄에 두면
             단추가 너무 좁아 **글자가 한 자씩 세로로 쌓인다**(사용자가 호칭
             폼에서 잡아 준 그것). */
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                child: FilledButton(
                  key: const Key('team-save'),
                  /* 🔴 **지역이 목록의 값일 때만 눌린다.** 자유롭게 적은
                     값을 받으면 저장은 되는데 **남의 검색에서 이 팀이
                     빠진다** — 지역 거르기가 글자 비교라서다. */
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
              ),
              TextButton(
                key: const Key('team-cancel'),
                onPressed: _busy ? null : widget.onDone,
                child: const Text('취소'),
              ),
            ],
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
///
/// 🔴 **처음에는 후보를 안 쏟는다**(2026-09-22, 사용자 지적: 「애초부터 지역
/// 주르륵 박혀있는데 이거 너무 길어서 어차피 보기도 힘들잖아」). 60개를 미리
/// 깔면 폼이 화면을 넘겨 **정작 쳐야 할 칸이 안 보인다.** 한 글자만 쳐도
/// 후보가 서너 개로 좁혀지므로, 적기 시작한 뒤에 보여 준다.
class _RegionField extends StatelessWidget {
  const _RegionField({
    required this.controller,
    required this.enabled,
    required this.onChanged,
  });

  final TextEditingController controller;
  final bool enabled;
  final VoidCallback onChanged;

  /// 좁은 판이라 넷이면 두 줄이다. 더 내면 폼이 길어진다.
  static const _maxHits = 4;

  @override
  Widget build(BuildContext context) {
    final typed = controller.text.trim();
    final picked = isRegion(controller.text);
    // 적기 전에는 안 보여 준다 — 고른 뒤에도 접는다.
    final hits = (typed.isEmpty || picked)
        ? const <String>[]
        : searchRegions(typed, limit: _maxHits);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          key: const Key('team-region'),
          controller: controller,
          enabled: enabled,
          decoration: InputDecoration(
            labelText: '지역',
            hintText: '예: 마포',
            /* 🔴 왜 아무거나 못 쓰는지 말해 준다 — 안 말하면 「왜 저장이 안
               되지」로 읽힌다. */
            helperText: picked
                ? null
                : typed.isEmpty
                    ? '동네를 적으면 후보가 나옵니다'
                    : hits.isEmpty
                        ? '그런 동네가 목록에 없습니다'
                        : '아래에서 골라 주세요',
            helperMaxLines: 2,
            suffixIcon: picked ? const Icon(Icons.check, size: 18) : null,
          ),
          onChanged: (_) => onChanged(),
        ),
        if (enabled && hits.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final r in hits)
                  ActionChip(
                    key: Key('team-region-$r'),
                    label: Text(
                      r,
                      softWrap: false,
                      style: const TextStyle(fontSize: 11),
                    ),
                    visualDensity: VisualDensity.compact,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    onPressed: () {
                      controller.text = r;
                      onChanged();
                    },
                  ),
              ],
            ),
          ),
      ],
    );
  }
}
