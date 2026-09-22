import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../card/data/card_providers.dart';
import '../../../card/data/card_repository.dart';
import '../../../card/data/models/player_card.dart';

void showTitlesSheet(BuildContext context, PlayerCard card) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => _TitlesSheet(card: card),
  );
}

/// 호칭 — **사람이 직접 적는다** (2026-09-16 결정, 미결 `paik` 36번).
///
/// 🔴 **방향이 뒤집힌 자리다.** 원래는 분석이 붙이는 값이었고(계약 4장
/// 「호칭은 미부여 방식으로만 작동한다」) 화면은 읽기만 했다. 팀이 다시
/// 정하면서 사람이 적게 됐다 — 근거는 *「참이든 거짓이든 경기 후 리뷰로
/// 남겨지니까 상관없다」* 이고, 신뢰는 호칭이 아니라 리뷰가 떠받친다는 뜻이다.
///
/// 🔴 **분류(강점·활동)를 안 받는다** — 자유 입력이라 분류를 매길 사람이 없다.
/// 읽는 쪽도 안 쓴다.
///
/// 🔴 **부여된 호칭은 여기 안 끌어온다** — 사람이 지울 수 있는 값이 아니다.
/// 가르는 기준은 `code` 가 `custom:` 으로 시작하는가다(`CardTitle.isCustom`).
/// ⚠️ **`category` 가 `null` 인지로 가르지 않는다** — 옛 적재분에도 `null` 이
/// 있을 수 있어서, 그걸로 가르면 부여된 옛 호칭을 여기로 끌어와 **저장하는
/// 순간 지워 버린다.**
class _TitlesSheet extends ConsumerStatefulWidget {
  const _TitlesSheet({required this.card});

  final PlayerCard card;

  @override
  ConsumerState<_TitlesSheet> createState() => _TitlesSheetState();
}

class _TitlesSheetState extends ConsumerState<_TitlesSheet> {
  late final List<TextEditingController> _fields = _seed();

  bool _busy = false;
  String? _error;

  /// 직접 적은 것만 칸에 채우고, **빈 칸 하나를 늘 남긴다** — 「추가」 단추를
  /// 따로 두지 않는다(웹과 같은 방식).
  List<TextEditingController> _seed() {
    final mine = [
      for (final t in widget.card.titles)
        if (t.isCustom) t.label,
    ];
    final values = [...mine, if (mine.length < kMaxTitles) ''];
    return [
      for (final v in values.take(kMaxTitles)) TextEditingController(text: v),
    ];
  }

  @override
  void dispose() {
    for (final c in _fields) {
      c.dispose();
    }
    super.dispose();
  }

  void _onChanged(int i) {
    // 마지막 칸을 채우면 빈 칸을 하나 더 내준다(상한까지).
    if (i == _fields.length - 1 &&
        _fields[i].text.trim().isNotEmpty &&
        _fields.length < kMaxTitles) {
      setState(() => _fields.add(TextEditingController()));
    }
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      /* 🔴 **앞뒤 공백을 털고 빈 것을 버린다.** 서버도 같은 정리를 하지만,
         여기서 안 하면 「빈 칸 하나를 늘 남긴다」 때문에 매번 빈 글자가
         섞여 나간다. */
      final next = [
        for (final c in _fields)
          if (c.text.trim().isNotEmpty) c.text.trim(),
      ];
      await ref.read(cardRepositoryProvider).updateCard(titles: next);
      // 프로필의 호칭 줄이 같은 provider 를 보므로 다시 읽게 한다.
      ref.invalidate(myCardProvider);
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
          const Text('호칭'),
          const SizedBox(height: 12),
          for (var i = 0; i < _fields.length; i += 1)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: TextField(
                key: Key('profile-title-$i'),
                controller: _fields[i],
                enabled: !_busy,
                // 🔴 20자까지 — 넘기면 서버가 422 다. 여기서 막아 준다.
                maxLength: kMaxTitleLen,
                decoration: InputDecoration(
                  labelText: '호칭 ${i + 1}',
                  hintText: '예: 시야가 넓은',
                  counterText: '',
                ),
                onChanged: (_) => _onChanged(i),
              ),
            ),
          Text(
            '$kMaxTitleLen자까지 · $kMaxTitles개까지. 비우면 지워집니다.',
            style: TextStyle(
              color: Theme.of(context).hintColor,
              fontSize: 12,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              key: const Key('profile-titles-error'),
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('profile-titles-save'),
            onPressed: _busy ? null : _save,
            child: _busy
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('저장'),
          ),
        ],
      ),
    );
  }
}
