import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../profile/presentation/widgets/player_card_view.dart';
import '../../board_geometry.dart';
import '../../data/models/squad.dart';
import '../../seats_from_squad.dart';

const Color _kOnDark = Color(0xFFFFFFFF);
const Color _kInk = Color(0xFF0B0B0B);

/// 홈의 스쿼드 판 — 웹 홈 첫 화면의 그 판(`SquadPanel.tsx`)을 폰 세로에 맞춰
/// 옮긴 **첫 단계**다. 판 크기(3:3 · 5:5 · 7:7), 경기장 선, 포지션 자리대로 선
/// 카드(내 카드 + 빈 자리)까지.
///
/// ⚠️ **아직 안 옮긴 것**(웹에는 있다):
/// - 빈 자리(+) → AI 추천 · 지인 찾기. 폰에서는 옆 판이 아니라 **아래 시트**로
///   연다(`www/docs/2026-08-31-앱-이식-지침.md` §4). 지금은 [onSeatTap] 만 부른다
/// - 카드 끌어 옮기기 · 빼기(⊗) · 포지션 직접 정하기
class SquadBoard extends StatefulWidget {
  const SquadBoard({
    super.key,
    required this.cardSeed,
    required this.onSeatTap,
    this.squad,
    this.mySlug,
    this.mateCardBuilder,
    this.onSeatMoved,
    this.onSeatRemoved,
  });

  /// 내 카드 붓자국의 씨앗 — 🔴 **카드의 `public_slug`** 여야 웹과 같은 무늬가
  /// 나온다. 카드가 아직 없으면 `null` 이고, 그러면 판에 내 카드를 안 그린다.
  final String? cardSeed;

  /// 서버 스쿼드. `null` 이면 아직 안 만들었거나 안 불러온 것이다 — 둘 다
  /// 「자리가 전부 비어 있다」로 그린다.
  final Squad? squad;

  /// 내 카드의 공개 슬러그 — **어느 등재가 나인지** 가리는 열쇠다.
  final String? mySlug;

  /// 그 슬러그의 남의 카드를 그려 준다. 아직 안 왔으면 `null` 을 돌려주고,
  /// 그때 판은 **이름표로 물러난다**(판 전체를 로딩으로 덮지 않는다).
  final Widget? Function(String slug, double width)? mateCardBuilder;

  /// 빈 자리를 눌렀다. 인자는 그 자리.
  final ValueChanged<SquadSlot> onSeatTap;

  /// 카드를 **다른 칸으로 옮겼다**. `memberId` 는 그 자리 등재의 id,
  /// `positionCode` 는 **놓인 행이 뜻하는 포지션**이다.
  ///
  /// 🔴 **`null` 이면 아예 못 집는다** — 주장이 아니면 옮겨도 403 이라,
  /// 끌린 뒤 되돌아가는 것보다 못 집게 하는 편이 낫다.
  final void Function(
    String memberId,
    String positionCode,
    int col,
    int row,
  )? onSeatMoved;

  /// 그 자리 사람을 **판에서 뺐다**(⊗). 인자는 등재 id 와 카드 슬러그다 —
  /// 슬러그는 팀에서도 내보낼 때 주인을 알아내는 데 쓴다.
  ///
  /// 🔴 **`null` 이면 ⊗ 를 안 그린다**(주장이 아니다).
  final void Function(String memberId, String? cardSlug)? onSeatRemoved;

  @override
  State<SquadBoard> createState() => _SquadBoardState();
}

class _SquadBoardState extends State<SquadBoard> {
  /// 사람이 알약으로 고른 크기. 🔴 **이것이 서버 값을 이긴다** — 안 그러면
  /// 판을 3:3 으로 바꾼 직후 스쿼드가 다시 도착하면서 5:5 로 되돌아간다.
  SquadSize? _picked;

  /// 서버가 모르는 값·`null` 을 주면 기본 판(5:5)이다.
  SquadSize get _size => _picked ?? squadSizeOf(widget.squad?.formation);

  // 판 안 여백 — 위는 머리글(MY SQUAD · 크기) 자리, 아래는 이름표가 선을 물지
  // 않을 만큼. 웹(46 · 22 · 8)보다 옆을 줄였다 — 폰 폭에서 카드가 한 치라도 크게.
  static const double _padTop = 44;
  static const double _padSide = 12;
  static const double _padBottom = 6;
  static const double _labelH = 14;
  static const double _labelGap = 3;

  /// 지금 집혀 있는 자리(`area`). `null` 이면 아무것도 안 집었다.
  String? _dragging;

  /// 집은 카드가 손끝을 따라간 거리.
  Offset _dragOffset = Offset.zero;

  /// 손끝이 지금 가리키는 칸 — 놓을 자리를 미리 보여 준다.
  ({int col, int row})? _hoverCell;

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

        // 🔴 자리 계산은 순수 함수 한 곳이다 — 판이 스스로 배치를 정하면
        //    웹과 갈린다(`seats_from_squad.dart` 의 세 단계).
        final seats = seatsFromSquad(widget.squad, _size, mySlug: widget.mySlug);

        final boardSize = Size(w, h);

        return Stack(
          children: [
            Positioned.fill(
              child: CustomPaint(painter: _PitchPainter()),
            ),
            // 놓을 칸 미리보기 — 집고 있는 동안만.
            if (_hoverCell != null)
              Positioned(
                left: _padSide + _hoverCell!.col * cellW + (cellW - cardW) / 2,
                top: _padTop +
                    _hoverCell!.row * cellH +
                    (cellH - cardH - _labelGap - _labelH) / 2,
                width: cardW,
                height: cardH,
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(cardW * 24 / 380),
                      border: Border.all(color: AppTheme.seed, width: 2),
                      color: AppTheme.seed.withValues(alpha: 0.14),
                    ),
                  ),
                ),
              ),
            Positioned(
              top: 12,
              left: 16,
              right: 12,
              child: _head(),
            ),
            for (final slot in seats.slots)
              Positioned(
                key: ValueKey('squad-seat-${slot.area}'),
                left: _padSide + slot.col * cellW + (cellW - cardW) / 2,
                top: _padTop +
                    slot.row * cellH +
                    (cellH - cardH - _labelGap - _labelH) / 2,
                width: cardW,
                child: _draggable(slot, cardW, seats, boardSize),
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
              onTap: () => setState(() => _picked = size),
            ),
          ),
      ],
    );
  }

  /// 그 자리를 **집을 수 있는가** — 옮길 수 있는 사람이고 등재가 있어야 한다.
  ///
  /// 🔴 빈 자리는 못 집는다(옮길 등재가 없다). 주장이 아니면
  /// [SquadBoard.onSeatMoved] 가 `null` 이라 아무것도 못 집는다.
  bool _canDrag(SquadSlot slot, SeatAssignment seats) =>
      widget.onSeatMoved != null && seats.memberIds.containsKey(slot.area);

  /// 자리 하나를 **길게 눌러 집고 끌 수 있게** 감싼다.
  ///
  /// 🔴 **길게 눌러야 집힌다.** 폰에서는 판이 스크롤·시트와 섞일 수 있어, 바로
  /// 끌리면 판을 내리려다 카드를 옮기게 된다(웹은 마우스라 그 문제가 없다).
  Widget _draggable(
    SquadSlot slot,
    double cardW,
    SeatAssignment seats,
    Size boardSize,
  ) {
    final seat = _seat(slot, cardW, seats);
    if (!_canDrag(slot, seats)) return seat;

    final dragging = _dragging == slot.area;
    return GestureDetector(
      key: Key('squad-drag-${slot.area}'),
      behavior: HitTestBehavior.deferToChild,
      onLongPressStart: (_) {
        // 집혔다는 것을 손끝으로 알린다 — 화면만 바뀌면 놓치기 쉽다.
        HapticFeedback.mediumImpact();
        setState(() {
          _dragging = slot.area;
          _dragOffset = Offset.zero;
          _hoverCell = (col: slot.col, row: slot.row);
        });
      },
      onLongPressMoveUpdate: (d) {
        if (_dragging != slot.area) return;
        setState(() {
          _dragOffset = d.offsetFromOrigin;
          _hoverCell = cellAt(
            d.localPosition + _cellCenterOf(slot, boardSize),
            boardSize,
            padTop: _padTop,
            padSide: _padSide,
            padBottom: _padBottom,
          );
        });
      },
      onLongPressEnd: (_) => _dropAt(slot, seats),
      onLongPressCancel: _cancelDrag,
      child: Transform.translate(
        offset: dragging ? _dragOffset : Offset.zero,
        child: Transform.scale(
          // 집힌 카드는 살짝 뜬다 — 「지금 이걸 들고 있다」가 보여야 한다.
          scale: dragging ? 1.08 : 1,
          child: seat,
        ),
      ),
    );
  }

  /// 그 자리 카드의 **왼쪽 위**가 판 안에서 어디인가 — 손끝 좌표를 판 좌표로
  /// 옮길 때 쓴다(`onLongPressMoveUpdate` 의 `localPosition` 은 카드 기준이다).
  Offset _cellCenterOf(SquadSlot slot, Size boardSize) => cellOrigin(
        slot.col,
        slot.row,
        boardSize,
        padTop: _padTop,
        padSide: _padSide,
        padBottom: _padBottom,
      );

  void _cancelDrag() {
    if (_dragging == null) return;
    setState(() {
      _dragging = null;
      _dragOffset = Offset.zero;
      _hoverCell = null;
    });
  }

  /// 손을 뗐다 — 놓을 수 있으면 알리고, 아니면 제자리로 돌아간다.
  void _dropAt(SquadSlot slot, SeatAssignment seats) {
    final cell = _hoverCell;
    final memberId = seats.memberIds[slot.area];
    _cancelDrag();
    if (cell == null || memberId == null) return;
    // 제자리면 아무 일도 안 한다 — 서버를 괜히 부르지 않는다.
    if (cell.col == slot.col && cell.row == slot.row) return;
    /* 🔴 **이미 찬 칸에는 못 놓는다.** 서로 자리를 바꾸려면 등재 둘을 한 번에
       고쳐야 하는데 계약에 그런 경로가 없다 — 한쪽씩 보내면 중간에 **같은 칸에
       둘**이 되어 서버가 막는다. 제자리로 돌려보낸다. */
    final taken = seats.slots.any(
      (s) => s.area != slot.area && s.col == cell.col && s.row == cell.row &&
          (s.mine || seats.mates.containsKey(s.area)),
    );
    if (taken) {
      HapticFeedback.lightImpact();
      return;
    }
    widget.onSeatMoved!(
      memberId,
      // 🔴 포지션은 **놓인 행**이 정한다 — 계약이 position_code 를 늘 요구한다.
      positionOfRow(cell.row),
      cell.col,
      cell.row,
    );
  }

  /// 자리는 셋으로 갈린다 — **내 카드 · 남의 카드 · 빈 자리.**
  Widget _seat(SquadSlot slot, double cardW, SeatAssignment seats) {
    final Widget card;
    if (slot.mine && widget.cardSeed != null) {
      card = PlayerCardView(width: cardW, seed: widget.cardSeed!);
    } else if (seats.mates.containsKey(slot.area)) {
      final slug = seats.slugs[slot.area];
      final mate =
          slug == null ? null : widget.mateCardBuilder?.call(slug, cardW);
      // 🔴 카드가 아직 안 왔거나 슬러그가 없으면 **이름표로 물러난다.** 판
      //    전체를 로딩으로 덮지 않는다 — 나머지 자리는 이미 그릴 수 있다.
      card = mate ?? _nameplate(slot, cardW, seats);
    } else {
      card = GestureDetector(
        key: Key('squad-add-${slot.area}'),
        onTap: () => widget.onSeatTap(slot),
        // 가운데 + — 카드 제 크기(380 폭) 기준 120 이다(웹 `.ss-squad-plus`).
        child: BlankPlayerCardView(
          width: cardW,
          child: const Icon(Icons.add, size: 150, color: _kInk),
        ),
      );
    }
    /* 🔴 **내 카드에는 ⊗ 가 없다**(웹, 2026-09-17 사용자 판단). 내 카드는
       옮기기만 한다 — 스스로를 빼면 주장이 팀에서 나가는 셈이라 서버도
       409 LAST_OWNER 로 막는다. 남의 카드만 ⊗ 로 뺀다.
       🔴 **주장에게만 그린다** — `onSeatRemoved` 가 null 이면 안 그린다. */
    final removable = !slot.mine &&
        widget.onSeatRemoved != null &&
        seats.memberIds.containsKey(slot.area);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (removable)
          Stack(
            clipBehavior: Clip.none,
            children: [
              card,
              Positioned(
                top: -6,
                right: -6,
                child: _RemoveButton(
                  key: Key('squad-remove-${slot.area}'),
                  onTap: () => widget.onSeatRemoved!(
                    seats.memberIds[slot.area]!,
                    seats.slugs[slot.area],
                  ),
                ),
              ),
            ],
          )
        else
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

  /// 카드가 아직 없을 때 그 자리 사람의 **이름만** 세운다.
  ///
  /// 🔴 **글자 크기 40 은 카드 제 크기(380 폭) 기준이다** — `BlankPlayerCardView`
  /// 안은 통째로 줄어들므로 여기에 화면 픽셀을 넣으면 작은 판에서 글자만 커진다.
  Widget _nameplate(SquadSlot slot, double cardW, SeatAssignment seats) {
    // 수락 대기중이면 흐리게 — 「아직 안 온 사람」이다.
    final ready = seats.ready[slot.area] ?? true;
    return BlankPlayerCardView(
      width: cardW,
      child: Opacity(
        opacity: ready ? 1 : 0.45,
        child: Text(
          seats.mates[slot.area]!,
          key: Key('squad-mate-${slot.area}'),
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 40,
            fontWeight: FontWeight.w700,
            color: _kInk,
          ),
        ),
      ),
    );
  }
}

/// 카드를 판에서 빼는 ⊗ — 카드 오른쪽 위 모서리에 걸친다.
///
/// 🔴 **누르는 자리를 카드보다 크게 잡는다.** 판의 카드는 폰에서 아주 작아서
/// 보이는 크기 그대로 두면 손가락으로 못 누른다(최소 40×40).
class _RemoveButton extends StatelessWidget {
  const _RemoveButton({super.key, required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '판에서 빼기',
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: SizedBox(
          width: 40,
          height: 40,
          child: Center(
            child: Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: _kInk.withValues(alpha: 0.82),
                shape: BoxShape.circle,
                border: Border.all(color: _kOnDark, width: 1.5),
              ),
              child: const Icon(Icons.close, size: 14, color: _kOnDark),
            ),
          ),
        ),
      ),
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
