import 'package:flutter/material.dart';

import '../../../profile/presentation/widgets/player_card_view.dart';
import '../../data/models/squad.dart';
import '../../seats_from_squad.dart';

/// **읽기 전용 판** — 대기 화면이 두 팀을 위아래로 세울 때 쓴다.
///
/// 🔴 **`SquadBoard` 를 재사용하지 않는다.** 그쪽은 끌어 옮기기·빼기·크기
/// 바꾸기를 들고 있어서, 남의 팀 판을 그리는 자리에 두면 **만질 수 있는
/// 것처럼 보인다.** 자리 계산(`seatsFromSquad`)만 나눠 쓴다 — 그래야 우리
/// 판이 홈에서와 같은 배치로 선다.
///
/// 🔴 **웹처럼 나란히 두지 않는다**(2026-09-25 사용자 요청: 「위아래로 판
/// 둘로」). 폰 폭에 판 둘을 가로로 놓으면 카드가 손톱만 해진다.
class ReadOnlyPitch extends StatelessWidget {
  const ReadOnlyPitch({
    super.key,
    required this.title,
    this.squad,

    /// 판을 **못 읽었을 때** 자리에 세울 이름들(「FC 강남 선수 1」…).
    ///
    /// 🔴 **이름을 지어내는 것이 아니다** — 「아직 못 읽었다」가 드러나야 해서
    /// 팀 이름 + 번호로 둔다. 진짜 판이 오면 [squad] 가 이긴다.
    this.placeholders = const [],
    this.lineColor = const Color(0x40FFFFFF),
    this.labelColor = const Color(0xFFFFFFFF),
    this.cardBuilder,
  });

  final String title;
  final Squad? squad;
  final List<String> placeholders;
  final Color lineColor;
  final Color labelColor;

  /// 그 슬러그의 **진짜 선수 카드**를 그려 준다. 아직 안 왔으면 `null` 을
  /// 돌려주고, 그때 자리는 **빈 카드 + 이름**으로 물러난다(홈 판과 같다).
  ///
  /// 🔴 **이름 상자는 물러남이지 기본형이 아니다**(2026-09-25 사용자가 두 번
  /// 짚었다: 「실제 카드들이 나와야 한다고」).
  final Widget? Function(String slug, double width)? cardBuilder;

  @override
  Widget build(BuildContext context) {
    final seats = seatsFromSquad(squad, squadSizeOf(squad?.formation));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text(
            title,
            style: TextStyle(
              color: labelColor,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ),
        AspectRatio(
          // 격자 3열 × 4행 — 홈 판과 같은 비율이라 배치가 눈에 익는다.
          aspectRatio: 3 / 3.4,
          child: LayoutBuilder(
            key: const Key('waiting-pitch'),
            builder: (context, box) {
              final cellW = box.maxWidth / 3;
              final cellH = box.maxHeight / 4;

              return Stack(
                children: [
                  Positioned.fill(
                    child: CustomPaint(painter: _LinePainter(lineColor)),
                  ),
                  for (var i = 0; i < seats.slots.length; i++)
                    Positioned(
                      left: seats.slots[i].col * cellW,
                      top: seats.slots[i].row * cellH,
                      width: cellW,
                      height: cellH,
                      child: _Seat(
                        name: seats.mates[seats.slots[i].area] ??
                            (seats.slots[i].mine
                                ? '나'
                                : (i < placeholders.length
                                    ? placeholders[i]
                                    : null)),
                        slug: seats.slugs[seats.slots[i].area],
                        position: seats.slots[i].position,
                        labelColor: labelColor,
                        cardBuilder: cardBuilder,
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _Seat extends StatelessWidget {
  const _Seat({
    required this.name,
    required this.slug,
    required this.position,
    required this.labelColor,
    required this.cardBuilder,
  });

  final String? name;
  final String? slug;
  final String position;
  final Color labelColor;
  final Widget? Function(String slug, double width)? cardBuilder;

  @override
  Widget build(BuildContext context) {
    if (name == null) {
      // 빈 자리 — 포지션만 옅게 둔다.
      return Center(
        child: Text(
          position,
          style: TextStyle(
            color: labelColor.withValues(alpha: 0.28),
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 1,
          ),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, box) {
        /* 칸 안에 들어가는 가장 큰 3 : 4.1 — 홈 판과 같은 비율이다.
           🔴 **빼는 것을 다 빼야 한다**: 이름 줄(12) · 그 위 틈(3) · 이 칸의
           위아래 안여백(3+3). 하나라도 빠뜨리면 그만큼 넘친다. */
        const labelH = 12.0;
        const gaps = 3.0 + 3.0 + 3.0;
        final byHeight = (box.maxHeight - labelH - gaps) * 3 / 4.1;
        final byWidth = box.maxWidth - 6;
        /* 🔴 **내림한다.** 카드 높이는 `cardW * 4.1 / 3` 으로 되살아나므로,
           소수점이 남으면 반올림 한 픽셀에 넘친다(실제로 1px 넘쳤다). */
        final cardW = (byHeight < byWidth ? byHeight : byWidth)
            .clamp(0.0, double.infinity)
            .floorToDouble();

        final built =
            slug == null ? null : cardBuilder?.call(slug!, cardW);

        return Padding(
          padding: const EdgeInsets.all(3),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              /* 🔴 **진짜 카드가 먼저다.** 못 읽었을 때만 빈 카드에 이름을
                 쓴다 — 홈 판(`SquadBoard`)이 하는 물러남과 같다. */
              built ??
                  BlankPlayerCardView(
                    width: cardW,
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: Text(
                          name!,
                          maxLines: 2,
                          textAlign: TextAlign.center,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 30,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF0B0B0B),
                          ),
                        ),
                      ),
                    ),
                  ),
              const SizedBox(height: 3),
              // 🔴 **높이를 못 박는다** — 글꼴에 따라 글자 줄 높이가 달라져
              //    위 계산과 어긋나면 그만큼 넘친다.
              SizedBox(
                height: labelH,
                child: Text(
                  position,
                  style: TextStyle(
                    color: labelColor.withValues(alpha: 0.55),
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// 경기장 선 — 가운데 줄과 원, 양 끝 골 상자. 홈 판과 같은 인상이면 된다.
class _LinePainter extends CustomPainter {
  const _LinePainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    canvas.drawRect(Offset.zero & size, p);
    canvas.drawLine(
      Offset(0, size.height / 2),
      Offset(size.width, size.height / 2),
      p,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      size.width * 0.16,
      p,
    );
    final boxW = size.width * 0.44;
    final boxH = size.height * 0.13;
    canvas.drawRect(
      Rect.fromLTWH((size.width - boxW) / 2, 0, boxW, boxH),
      p,
    );
    canvas.drawRect(
      Rect.fromLTWH((size.width - boxW) / 2, size.height - boxH, boxW, boxH),
      p,
    );
  }

  @override
  bool shouldRepaint(_LinePainter old) => old.color != color;
}
