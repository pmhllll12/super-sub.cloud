import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../profile/presentation/widgets/player_card_view.dart';
import '../data/card_providers.dart';
import '../data/card_repository.dart';
import '../data/models/player_card.dart';
import '../data/pick_photo.dart';

/// 카드 꾸미기 — 웹 `app/(app)/me/card`(`CardEditor.tsx`)를 폰에 맞춰 옮긴 것.
///
/// 웹은 카드 옆에 조작 칸을 세로로 세우는데, 폰에는 옆으로 펼 자리가 없어
/// **위는 미리보기 · 아래는 탭**으로 쌓는다(이식 지침 §2-2).
///
/// 🔴 **저장은 전체 값을 보낸다** — 계약이 부분 병합을 안 하고 거부한다.
///
/// 🔴 **사진은 「저장」을 눌러야 붙는다.** 고르면 S3 로 올라가 **키만** 손에
/// 들어오고, 그 키는 `style.photo_key` 로 저장될 때 카드에 붙는다(계약 3-5절).
/// 올리기만 하고 나가면 아무 일도 안 난다 — 그 사이를 화면이 말해 준다.
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

  /// 방금 고른 사진의 **로컬 경로** — 올라가기 전에도 보여 준다.
  String? _localPhoto;

  /// 사진을 올리는 중인가. 그동안 저장을 막는다 — 🔴 키가 아직 없어서
  /// 저장하면 **사진이 안 남는다.**
  bool _photoBusy = false;

  /// 사진 쪽 사유 — 형식 · 올리기 실패.
  String? _photoNote;

  @override
  void dispose() {
    _tagline.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        backgroundColor: _kBg,
        appBar: AppBar(
          backgroundColor: _kBg,
          foregroundColor: _kOn,
          title: const Text('카드 꾸미기'),
          actions: [
            TextButton(
              key: const Key('card-editor-save'),
              /* 🔴 **사진이 올라가는 동안 저장을 막는다.** 그 사이에 누르면
                 키가 아직 없어서 **사진만 쏙 빠진 채로 저장된다** — 사람은
                 저장이 됐다고 믿는다. */
              onPressed: (_busy || _photoBusy) ? null : _save,
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
              Tab(key: Key('card-editor-tab-photo'), text: '사진'),
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
                // 방금 고른 사진이 서버 주소를 이긴다 — 안 그러면 골라도 안 바뀐다.
                photoImage:
                    _localPhoto == null ? null : FileImage(File(_localPhoto!)),
              ),
            ),
            Expanded(
              child: TabBarView(
                children: [_colors(), _photo(), _text(), _mark()],
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

  /// 사진 — 놓는 방법 · 고르기 · 자리.
  Widget _photo() {
    final hasPhoto = _localPhoto != null || widget.card.photoUrl != null;
    /* 🔴 **아직 안 올라간 상태를 말해 준다.** 고른 그림은 보이는데 키가 없으면
       저장해도 사진이 안 남는다 — 말 안 해 주면 「저장했는데 사라졌다」가 된다.
       (`_localPhoto` 가 있는데 `photoKey` 가 없다 = 그 상태다.) */
    final notUploaded =
        _localPhoto != null && _style.photoKey == null && !_photoBusy;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        /* 🔴 두 길을 **먼저** 고르게 한다 — 누끼를 따야 하는지가 사진을
           준비하는 방법을 통째로 바꾼다(웹과 같은 순서). */
        Row(
          children: [
            Expanded(
              child: _ModeChip(
                chipKey: const Key('card-editor-mode-cutout'),
                label: '사람만 오려서',
                on: _style.mode == CardMode.cutout,
                onTap: () => setState(
                  () => _style = _style.copyWith(mode: CardMode.cutout),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _ModeChip(
                chipKey: const Key('card-editor-mode-full'),
                label: '사진 그대로',
                on: _style.mode == CardMode.full,
                onTap: () => setState(
                  () => _style = _style.copyWith(mode: CardMode.full),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          _style.mode == CardMode.cutout
              ? '배경을 지운 그림(PNG)이면 카드에 자연스럽게 섭니다.'
              : '오려 내지 않은 사진을 그대로 깝니다 — 로고와 PLAYER CARD 만 위에 얹힙니다.',
          style: TextStyle(color: _kOn.withValues(alpha: 0.65), fontSize: 12),
        ),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          key: const Key('card-editor-photo-pick'),
          icon: const Icon(Icons.photo_library, size: 18),
          label: Text(
            _photoBusy
                ? '올리는 중…'
                : hasPhoto
                    ? '다른 사진으로'
                    : '사진 고르기',
          ),
          style: OutlinedButton.styleFrom(
            foregroundColor: _kOn,
            side: BorderSide(color: _kOn.withValues(alpha: 0.4)),
            minimumSize: const Size.fromHeight(44),
          ),
          onPressed: _photoBusy ? null : _pickPhoto,
        ),
        if (_photoNote != null) ...[
          const SizedBox(height: 10),
          Text(
            _photoNote!,
            key: const Key('card-editor-photo-note'),
            style: const TextStyle(color: Color(0xFFFFB4A9), fontSize: 12),
          ),
        ],
        if (notUploaded) ...[
          const SizedBox(height: 10),
          Text(
            '아직 안 올라갔습니다 — 다시 골라 주세요.',
            key: const Key('card-editor-photo-pending'),
            style: TextStyle(color: _kOn.withValues(alpha: 0.65), fontSize: 12),
          ),
        ],
        if (hasPhoto) ...[
          const SizedBox(height: 8),
          _Slider(
            label: '크기',
            value: _style.photoScale,
            // 웹과 같은 범위.
            min: 0.4,
            max: 2,
            onChanged: (v) =>
                setState(() => _style = _style.copyWith(photoScale: v)),
          ),
          _Slider(
            label: '좌우',
            value: _style.photoX,
            min: -50,
            max: 50,
            onChanged: (v) =>
                setState(() => _style = _style.copyWith(photoX: v)),
          ),
          _Slider(
            label: '위아래',
            value: _style.photoY,
            min: -50,
            max: 50,
            onChanged: (v) =>
                setState(() => _style = _style.copyWith(photoY: v)),
          ),
        ],
      ],
    );
  }

  Future<void> _pickPhoto() async {
    setState(() => _photoNote = null);
    final PickedPhoto? picked;
    try {
      picked = await ref.read(photoPickerProvider).fromGallery();
    } catch (e) {
      setState(() => _photoNote = '사진을 고르지 못했습니다: $e');
      return;
    }
    if (picked == null) return; // 고르다 말았다 — 오류가 아니다.

    /* 🔴 **폰 앨범은 HEIC 도 내준다** — 서버는 셋만 받으므로 여기서 막는다.
       안 막으면 올라가다 422 로 죽고, 사람은 한참 기다린 뒤에 거절을 본다. */
    final bad = checkCardPhoto(picked.file);
    if (bad != null) {
      setState(() => _photoNote = bad);
      return;
    }

    /* 🔴 **미리보기부터 켜고 키는 비운다.** 옛 사진의 키가 남아 있으면
       올리기가 실패했을 때 **새 그림 + 옛 키**로 저장돼, 내가 보는 카드와
       남이 보는 카드가 갈린다(웹이 같은 주석을 남겼다). */
    setState(() {
      _localPhoto = picked!.path;
      _style = _style.copyWith(clearPhotoKey: true);
      _photoBusy = true;
    });

    try {
      final key =
          await ref.read(cardRepositoryProvider).uploadCardPhoto(picked.file);
      if (!mounted) return;
      setState(() => _style = _style.copyWith(photoKey: key));
    } catch (e) {
      if (mounted) setState(() => _photoNote = '사진을 올리지 못했습니다 — $e');
    } finally {
      if (mounted) setState(() => _photoBusy = false);
    }
  }

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
const Color _kSeed = Color(0xFF70ED88);

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

/// 「사람만 오려서」 · 「사진 그대로」 — 둘 중 하나.
class _ModeChip extends StatelessWidget {
  const _ModeChip({
    required this.chipKey,
    required this.label,
    required this.on,
    required this.onTap,
  });

  final Key chipKey;
  final String label;
  final bool on;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: on,
      button: true,
      child: Material(
        color: on ? _kSeed.withValues(alpha: 0.2) : Colors.transparent,
        borderRadius: BorderRadius.circular(999),
        child: InkWell(
          key: chipKey,
          borderRadius: BorderRadius.circular(999),
          onTap: onTap,
          child: Container(
            height: 38,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: on ? _kSeed : _kOn.withValues(alpha: 0.25),
              ),
            ),
            child: Text(
              label,
              style: TextStyle(
                color: on ? _kSeed : _kOn.withValues(alpha: 0.7),
                fontSize: 13,
                fontWeight: on ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

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
