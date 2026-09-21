import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../profile/presentation/widgets/player_card_view.dart';
import '../data/card_providers.dart';
import '../data/models/player_card.dart';

/// 카드 꾸미기 — 웹 `app/(app)/me/card`(`CardEditor.tsx`)를 폰에 맞춰 옮긴 것.
///
/// 웹은 카드 옆에 조작 칸을 세로로 세우는데, 폰에는 옆으로 펼 자리가 없어
/// **위는 미리보기 · 아래는 탭**으로 쌓는다(이식 지침 §2-2).
///
/// 🔴 **저장은 전체 값을 보낸다** — 계약이 부분 병합을 안 하고 거부한다.
///
/// ⚠️ **사진은 아직 없다** — 올리기가 S3 사전 서명 두 단계라 따로 잡는다.
/// 이미 올린 사진은 그려지고, 자리·배율도 서버 값 그대로 유지된다.
class CardEditorScreen extends ConsumerStatefulWidget {
  const CardEditorScreen({super.key, required this.card});

  final PlayerCard card;

  @override
  ConsumerState<CardEditorScreen> createState() => _CardEditorScreenState();
}

class _CardEditorScreenState extends ConsumerState<CardEditorScreen> {
  late CardStyle _style = widget.card.style ?? defaultCardStyle;
  late final TextEditingController _tagline =
      TextEditingController(text: aliasOf(widget.card));
  bool _busy = false;

  @override
  void dispose() {
    _tagline.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        backgroundColor: _kBg,
        appBar: AppBar(
          backgroundColor: _kBg,
          foregroundColor: _kOn,
          title: const Text('카드 꾸미기'),
          actions: [
            TextButton(
              key: const Key('card-editor-save'),
              onPressed: _busy ? null : _save,
              style: TextButton.styleFrom(foregroundColor: _kOn),
              child: _busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('저장'),
            ),
          ],
          bottom: const TabBar(
            labelColor: _kOn,
            unselectedLabelColor: Color(0xB3FFFFFF),
            /* 🔴 탭을 **키로** 찾게 한다 — 라벨(「색」·「글자」)이 아래
               조작 칸의 라벨과 겹쳐서 글자로 찾으면 둘이 잡힌다. */
            tabs: [
              Tab(key: Key('card-editor-tab-colors'), text: '색'),
              Tab(key: Key('card-editor-tab-text'), text: '글자'),
              Tab(key: Key('card-editor-tab-mark'), text: '자국'),
            ],
          ),
        ),
        body: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: PlayerCardView(
                width: 180,
                seed: widget.card.publicSlug,
                alias: _tagline.text,
                style: _style,
                photoUrl: widget.card.photoUrl,
              ),
            ),
            Expanded(
              child: TabBarView(
                children: [_colors(), _text(), _mark()],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _colors() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _ColorRow(
            label: '바탕',
            value: _style.bg,
            onPick: (c) => setState(() => _style = _style.copyWith(bg: c)),
          ),
          _ColorRow(
            label: '워드마크',
            value: _style.logo,
            onPick: (c) => setState(() => _style = _style.copyWith(logo: c)),
          ),
          /* 🔴 **글자색 하나가 여러 곳을 움직인다** — 별명·획·머리글, 그리고
             워드마크 색을 따로 안 정했으면 그것까지. 자리마다 따로 칠하면
             반드시 빠지는 곳이 생긴다(웹 주석). */
          _ColorRow(
            label: '글자',
            value: _style.textColor,
            onPick: (c) =>
                setState(() => _style = _style.copyWith(textColor: c)),
          ),
        ],
      );

  Widget _text() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            key: const Key('card-editor-tagline'),
            controller: _tagline,
            // 🔴 20자까지다 — 넘기면 서버가 422 다. 여기서 막아 준다.
            maxLength: 20,
            style: const TextStyle(color: _kOn),
            decoration: const InputDecoration(
              labelText: '카드에 넣을 한 줄',
              helperText: '비우면 글자 없이',
              labelStyle: TextStyle(color: _kOn),
              helperStyle: TextStyle(color: Color(0xB3FFFFFF)),
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          _Slider(
            label: '좌우',
            value: _style.textX,
            // 웹과 같은 범위 — 더 밀면 글자가 카드 밖으로 나간다.
            min: 6,
            max: 94,
            onChanged: (v) => setState(() => _style = _style.copyWith(textX: v)),
          ),
          _Slider(
            label: '위아래',
            value: _style.textY,
            /* 🔴 위 한계가 24 다(`TEXT_MIN_Y`) — 더 올라가면 **로고와 머리글을
               덮는다.** */
            min: 24,
            max: 94,
            onChanged: (v) => setState(() => _style = _style.copyWith(textY: v)),
          ),
        ],
      );

  Widget _mark() {
    final picking = _style.brush;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final n in kPickableMarks)
              _MarkChip(
                key: Key('card-editor-mark-$n'),
                index: n,
                selected: picking == n,
                color: _style.brushColor,
                onTap: () =>
                    setState(() => _style = _style.copyWith(brush: n)),
              ),
          ],
        ),
        const SizedBox(height: 16),
        // 🔴 「없음」을 골랐으면 조정할 것이 없다 — 웹도 이때 칸을 감춘다.
        if (picking != 1) ...[
          _ColorRow(
            label: '자국 색',
            value: _style.brushColor,
            onPick: (c) =>
                setState(() => _style = _style.copyWith(brushColor: c)),
          ),
          _Slider(
            label: '크기',
            value: _style.brushScale,
            min: 0.4,
            max: 2,
            onChanged: (v) =>
                setState(() => _style = _style.copyWith(brushScale: v)),
          ),
          _Slider(
            label: '좌우',
            value: _style.brushX,
            min: -50,
            max: 50,
            onChanged: (v) =>
                setState(() => _style = _style.copyWith(brushX: v)),
          ),
          _Slider(
            label: '위아래',
            value: _style.brushY,
            min: -50,
            max: 50,
            onChanged: (v) =>
                setState(() => _style = _style.copyWith(brushY: v)),
          ),
        ],
      ],
    );
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final text = _tagline.text.trim();
      await ref.read(cardRepositoryProvider).updateCard(
            // 🔴 비우면 **지운다** — 「안 정함」이 아니라 「일부러 지웠다」다.
            tagline: text.isEmpty ? null : text,
            clearTagline: text.isEmpty,
            style: _style,
          );
      ref.invalidate(myCardProvider);
      if (mounted) Navigator.of(context).pop();
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }
}

const Color _kBg = Color(0xFF14201A);
const Color _kOn = Color(0xFFFFFFFF);

/// 고를 수 있는 자국 번호.
///
/// 🔴 **7·8 은 목록에 자리를 두고 고르는 칸에서만 숨긴다**(웹 `HIDDEN_MARKS`).
/// 배열에서 빼면 뒤 번호가 당겨져 **그 자국을 쓰던 카드가 말없이 다른 그림**이
/// 된다 — 번호가 서버에 숫자로 저장되어 있다.
const List<int> kPickableMarks = [
  0, // 기본(절차적 붓자국)
  1, // 없음
  2, 3, 4, 5, 6,
  // 7, 8 — 숨김
  9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
];

class _MarkChip extends StatelessWidget {
  const _MarkChip({
    super.key,
    required this.index,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  final int index;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final asset = markAssetFor(index);
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 64,
        height: 64,
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: const Color(0xFF1E3029),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected ? const Color(0xFF70ED88) : Colors.transparent,
            width: 2,
          ),
        ),
        child: switch (index) {
          1 => const Center(
              child: Text('없음', style: TextStyle(color: _kOn, fontSize: 12)),
            ),
          0 => const Center(
              child: Text('기본', style: TextStyle(color: _kOn, fontSize: 12)),
            ),
          _ => asset == null
              ? const SizedBox.shrink()
              : Image.asset(
                  asset,
                  // 목록에서도 알파 마스크라 색으로 칠한다.
                  color: color,
                  colorBlendMode: BlendMode.srcIn,
                  fit: BoxFit.contain,
                ),
        },
      ),
    );
  }
}

class _ColorRow extends StatelessWidget {
  const _ColorRow({
    required this.label,
    required this.value,
    required this.onPick,
  });

  final String label;
  final Color value;
  final ValueChanged<Color> onPick;

  /// 고를 수 있는 색 — 카드가 밖으로 공유되는 물건이라 **아무 색이나** 두기보다
  /// 읽히는 조합을 추린다.
  static const _palette = [
    Color(0xFF91EA92), Color(0xFF70ED88), Color(0xFFFFFFFF),
    Color(0xFF0B0B0B), Color(0xFF1E3029), Color(0xFFFFD166),
    Color(0xFFEF476F), Color(0xFF118AB2), Color(0xFF8338EC),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: _kOn, fontSize: 13)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final c in _palette)
                GestureDetector(
                  onTap: () => onPick(c),
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: c,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: c == value
                            ? const Color(0xFF70ED88)
                            : const Color(0x33FFFFFF),
                        width: c == value ? 3 : 1,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Slider extends StatelessWidget {
  const _Slider({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.onChanged,
  });

  final String label;
  final double value;
  final double min;
  final double max;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 56,
          child: Text(label, style: const TextStyle(color: _kOn, fontSize: 13)),
        ),
        Expanded(
          child: Slider(
            // 값이 범위 밖일 수 있다(서버가 옛 값을 줄 때) — 묶는다.
            value: value.clamp(min, max),
            min: min,
            max: max,
            activeColor: const Color(0xFF70ED88),
            onChanged: onChanged,
          ),
        ),
        SizedBox(
          width: 44,
          child: Text(
            value.toStringAsFixed(max <= 2 ? 2 : 0),
            textAlign: TextAlign.right,
            style: const TextStyle(color: _kOn, fontSize: 12),
          ),
        ),
      ],
    );
  }
}
