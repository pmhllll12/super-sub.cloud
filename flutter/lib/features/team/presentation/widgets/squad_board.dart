import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../profile/presentation/widgets/player_card_view.dart';

/// 판의 크기 — 3:3 · 5:5 · 7:7.
enum SquadSize {
  three('3 : 3'),
  five('5 : 5'),
  seven('7 : 7');

  const SquadSize(this.label);

  final String label;
}

/// 판 위의 자리. [col]·[row] 는 3열 × 4행 격자 칸이고, **행이 포지션**이다
/// (0 FW · 1 MF · 2 DF · 3 GK — 웹 `lib/pitchGrid.ts` 의 `ROW_POS`).
class SquadSlot {
  const SquadSlot(this.area, this.col, this.row, {this.mine = false});

  /// 역할+번호(`fw1` · `mf2` …). 🔴 크기를 바꿔도 같은 이름이 같은 자리를
  /// 가리켜야 한다 — 웹 `FORMATIONS` 주석과 같은 이유.
  final String area;
  final int col;
  final int row;

  /// 내 카드가 처음 서는 자리.
  final bool mine;

  String get position => const ['FW', 'MF', 'DF', 'GK'][row];
}

/// 크기마다의 포메이션 — 웹 `SquadPanel.tsx` 의 `FORMATIONS` 를 그대로 옮겼다.
/// 위가 공격, 아래가 골키퍼다.
const Map<SquadSize, List<SquadSlot>> kFormations = {
  // 1-1-1
  SquadSize.three: [
    SquadSlot('fw1', 1, 0, mine: true),
    SquadSlot('mf1', 1, 1),
    SquadSlot('gk', 1, 3),
  ],
  // 1-2-1 — 풋살 5인.
  SquadSize.five: [
    SquadSlot('fw1', 1, 0, mine: true),
    SquadSlot('mf1', 0, 1),
    SquadSlot('mf2', 2, 1),
    SquadSlot('df1', 1, 2),
    SquadSlot('gk', 1, 3),
  ],
  // 2-3-1
  SquadSize.seven: [
    SquadSlot('fw1', 1, 0, mine: true),
    SquadSlot('mf1', 0, 1),
    SquadSlot('mf2', 1, 1),
    SquadSlot('mf3', 2, 1),
    SquadSlot('df1', 0, 2),
    SquadSlot('df2', 2, 2),
    SquadSlot('gk', 1, 3),
  ],
};

const Color _kOnDark = Color(0xFFFFFFFF);
const Color _kInk = Color(0xFF0B0B0B);

/// 홈의 스쿼드 판 — 웹 홈 첫 화면의 그 판(`SquadPanel.tsx`)을 폰 세로에 맞춰
/// 옮긴 **첫 단계**다. 판 크기(3:3 · 5:5 · 7:7), 경기장 선, 포지션 자리대로 선
/// 카드(내 카드 + 빈 자리)까지.
///
/// ⚠️ **아직 안 옮긴 것**(웹에는 있다):
/// - 서버 스쿼드(`GET /teams/{id}/squad`) — 지금은 내 카드 말고 전부 빈 자리다
/// - 빈 자리(+) → AI 추천 · 지인 찾기. 폰에서는 옆 판이 아니라 **아래 시트**로
///   연다(`www/docs/2026-08-31-앱-이식-지침.md` §4). 지금은 [onSeatTap] 만 부른다
/// - 카드 끌어 옮기기 · 빼기(⊗) · 포지션 직접 정하기
class SquadBoard extends StatefulWidget {
  const SquadBoard({
    super.key,
    required this.cardSeed,
    required this.onSeatTap,
  });

  /// 내 카드 붓자국의 씨앗 — `PlayerCardView.seed` 참고.
  final String cardSeed;

  /// 빈 자리를 눌렀다. 인자는 그 자리.
  final ValueChanged<SquadSlot> onSeatTap;

  @override
  State<SquadBoard> createState() => _SquadBoardState();
}

class _SquadBoardState extends State<SquadBoard> {
  /// 처음 여는 크기 — 풋살 5인(웹과 같다).
  SquadSize _size = SquadSize.five;

  // 판 안 여백 — 위는 머리글(MY SQUAD · 크기) 자리, 아래는 이름표가 선을 물지
  // 않을 만큼. 웹(46 · 22 · 8)보다 옆을 줄였다 — 폰 폭에서 카드가 한 치라도 크게.
  static const double _padTop = 44;
  static const double _padSide = 12;
  static const double _padBottom = 6;
  static const double _labelH = 14;
  static const double _labelGap = 3;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        final w = box.maxWidth;
        final h = box.maxHeight;
        final cellW = (w - _padSide * 2) / 3;
        final cellH = (h - _padTop - _padBottom) / 4;
        // 카드는 칸에 들어가는 가장 큰 3 : 4.1 — 세로는 이름표 · 칸 사이 틈을,
        // 가로는 옆 칸과의 틈을 뺀다.
        final byHeight = (cellH - _labelH - _labelGap - 6) * 3 / 4.1;
        final byWidth = cellW - 10;
        // 판이 아주 낮으면(키보드 · 작은 창) 음수가 나온다 — 0 에서 멈춘다.
        final cardW = (byHeight < byWidth ? byHeight : byWidth).clamp(0.0, double.infinity);
        final cardH = cardW * 4.1 / 3;

        return Stack(
          children: [
            Positioned.fill(
              child: CustomPaint(painter: _PitchPainter()),
            ),
            Positioned(
              top: 12,
              left: 16,
              right: 12,
              child: _head(),
            ),
            for (final slot in kFormations[_size]!)
              Positioned(
                key: ValueKey('squad-seat-${slot.area}'),
                left: _padSide + slot.col * cellW + (cellW - cardW) / 2,
                top: _padTop +
                    slot.row * cellH +
                    (cellH - cardH - _labelGap - _labelH) / 2,
                width: cardW,
                child: _seat(slot, cardW),
              ),
          ],
        );
      },
    );
  }

  Widget _head() {
    return Row(
      children: [
        // 좁은 폰(폭 360)에서는 크기 알약 셋이 우선이다 — 머리글이 밀려나면
        // 흐리게 잘린다. 알약이 잘리면 무엇을 고르는지 모른다.
        const Expanded(
          child: Text(
            'MY SQUAD',
            maxLines: 1,
            softWrap: false,
            overflow: TextOverflow.fade,
            style: TextStyle(
              color: _kOnDark,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 12 * 0.14,
            ),
          ),
        ),
        for (final size in SquadSize.values)
          Padding(
            padding: const EdgeInsets.only(left: 3),
            child: _SizeChip(
              key: Key('squad-size-${size.name}'),
              label: size.label,
              selected: size == _size,
              onTap: () => setState(() => _size = size),
            ),
          ),
      ],
    );
  }

  Widget _seat(SquadSlot slot, double cardW) {
    final card = slot.mine
        ? PlayerCardView(width: cardW, seed: widget.cardSeed)
        : GestureDetector(
            key: Key('squad-add-${slot.area}'),
            onTap: () => widget.onSeatTap(slot),
            // 가운데 + — 카드 제 크기(380 폭) 기준 120 이다(웹 `.ss-squad-plus`).
            child: BlankPlayerCardView(
              width: cardW,
              child: const Icon(Icons.add, size: 150, color: _kInk),
            ),
          );
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        card,
        const SizedBox(height: _labelGap),
        SizedBox(
          height: _labelH,
          child: Text(
            slot.position,
            style: const TextStyle(
              color: _kOnDark,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1,
              height: 1.3,
            ),
          ),
        ),
      ],
    );
  }
}

/// 판 크기 알약 — 흰 바탕에 어두운 글자, 고른 것은 민트 바탕에 검은 글자.
/// 🔴 민트 글자를 흰 바탕에 두면 대비가 모자라 안 읽힌다(웹 주석과 같다).
class _SizeChip extends StatelessWidget {
  const _SizeChip({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
          decoration: BoxDecoration(
            color: selected ? AppTheme.seed : const Color(0xFFFFFFFF),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected ? AppTheme.seed : _kInk.withValues(alpha: 0.24),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              letterSpacing: 0,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
              color: selected ? _kInk : _kInk.withValues(alpha: 0.62),
            ),
          ),
        ),
      ),
    );
  }
}

/// 경기장 선 — 웹 `.ss-squad-pitch` 의 SVG(100×140)를 판 크기에 **늘여** 그린다
/// (`preserveAspectRatio="none"` — 원이 타원이 되지만 위아래 빈 띠가 안 생긴다).
/// 🔴 바깥 테두리만 온전한 흰색이고 안쪽 선은 30% 다 — 카드 · 이름표가 얹히는
/// 바탕이라 같은 무게면 서로를 갉아먹는다(웹 주석).
class _PitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    double x(double v) => v * size.width / 100;
    double y(double v) => v * size.height / 140;
    Rect r(double l, double t, double w, double h) =>
        Rect.fromLTWH(x(l), y(t), x(w), y(h));

    final inner = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = _kOnDark.withValues(alpha: 0.3);
    final edge = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..color = _kOnDark;

    canvas
      ..drawLine(Offset(x(1), y(70)), Offset(x(99), y(70)), inner)
      ..drawOval(Rect.fromCenter(center: Offset(x(50), y(70)), width: x(28), height: y(28)), inner)
      ..drawOval(
        Rect.fromCenter(center: Offset(x(50), y(70)), width: x(2.4), height: y(2.4)),
        Paint()..color = _kOnDark.withValues(alpha: 0.3),
      )
      ..drawRect(r(27, 1, 46, 20), inner)
      ..drawRect(r(38, 1, 24, 9), inner)
      ..drawRect(r(27, 119, 46, 20), inner)
      ..drawRect(r(38, 130, 24, 9), inner)
      ..drawRect(r(1, 1, 98, 138), edge);
  }

  @override
  bool shouldRepaint(_PitchPainter old) => false;
}
