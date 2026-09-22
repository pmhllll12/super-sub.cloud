import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../data/models/video_report.dart';

/// 분석 리포트를 그리는 **한 벌** — 웹 `components/analysis/ReportView.tsx`
/// 를 옮긴 것이다.
///
/// 🔴 **이 화면은 총점·오버롤 등급·레이더를 그린다.** 계약 3장 4 가 막은 것은
/// `summary` 문장 **안에** 숫자를 넣는 것뿐이다. 🔴 **카드 화면으로는 이
/// 값들을 옮기지 않는다**(부록 D.5 — 카드에 수치를 안 그린다).
class ReportView extends StatelessWidget {
  const ReportView({super.key, required this.report});

  final VideoReport report;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 옛 리포트(이 필드가 생기기 전 적재분)는 null 이라 건너뛴다.
        // 「이 선수의」가 아니라 **이 클립의** 오버롤이다.
        if (report.overallGrade != null) ...[
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              _GradeChip(grade: report.overallGrade!),
              if (report.totalScore != null) ...[
                const SizedBox(width: 10),
                Text(
                  '${report.totalScore!.round()}점',
                  style: const TextStyle(
                    color: _ink,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 14),
        ],

        Text(
          report.summary,
          style: const TextStyle(color: _ink, fontSize: 15, height: 1.5),
        ),

        if (report.points.isNotEmpty) ...[
          const SizedBox(height: 18),
          /* 🔴 **칭호와 문장을 항목마다 짝으로 그린다**(`ho` 24번) — 따로
             떼면 선수가 그 문장을 칭찬인지 지적인지 모른다. 칭호가 없는
             항목도 있고(받은 호칭만 온다), 그때는 문장만 그린다.
             🔴 여기까지 오면 이미 걸러진 뒤다 — 「미달」·흐린 칭호 같은
             표식을 따로 붙이지 않는다. */
          for (final p in report.points)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (p.title != null)
                    Container(
                      margin: const EdgeInsets.only(bottom: 4),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: _seed.withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        p.title!,
                        style: const TextStyle(
                          color: _seed,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  Text(
                    p.evidence,
                    style: TextStyle(
                      color: _ink.withValues(alpha: 0.85),
                      fontSize: 14,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
        ],

        if (report.radar.length >= 3) ...[
          const SizedBox(height: 8),
          ReportRadar(axes: report.radar),
        ],

        if (report.scenes.isNotEmpty) ...[
          const SizedBox(height: 20),
          const Text(
            '이렇게 본 장면',
            style: TextStyle(
              color: _ink,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          for (final s in report.scenes)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 44,
                    child: Text(
                      s.at,
                      style: const TextStyle(
                        color: _seed,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        fontFeatures: [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      s.what,
                      style: TextStyle(
                        color: _ink.withValues(alpha: 0.85),
                        fontSize: 13,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ],
    );
  }
}

const Color _ink = Color(0xFFFFFFFF);
const Color _seed = Color(0xFF70ED88);

/// 축의 색 — **차례가 고정**이고 **돌려 쓰지 않는다**(웹 `--ss-axis-1~6`).
///
/// 🔴 여섯을 넘는 루브릭이 오면 색을 **지어내는 것이 아니라** 그 판을 다시
/// 설계해야 한다 — 지어낸 색은 앞엣것과 구별된다는 보장이 없다. 그래서
/// 나머지 연산으로 돌리지 않고 넘치는 축은 마지막 색을 쓰되 **번호가 그
/// 둘을 가른다**(색만으로 말하지 않는 것이 이 판의 원칙이다).
///
/// 🔴 **여섯이 지금은 충분하지만 영원히는 아니다.** 축구 인스텝 슛 루브릭에
/// `deferred:` 로 빠진 항목이 둘 더 있고(임팩트 지점 · 스윙 가속 타이밍),
/// **공 검출기가 붙으면 8축이 된다.** 그때 색 둘을 미리 만들어 두면 안 된다 —
/// 여덟이 색각 이상에서 서로 구별되는지는 여덟을 다 놓고 재야 알 수 있고,
/// 기존 여섯의 간격도 다시 재야 한다. `dataviz` 검사를 여덟으로 다시 돌린다.
///
/// 이 여섯은 어두운 바탕(`--mode dark`)에서 검사를 통과했다 — 최악 인접쌍
/// ΔE 10.4(deutan), 기준 8.
const List<Color> kAxisColors = [
  Color(0xFF00AD64),
  Color(0xFF0B84FF),
  Color(0xFFD97300),
  Color(0xFF8B5CF6),
  Color(0xFFFF2D87),
  Color(0xFFAE8C00),
];

Color axisColor(int i) => kAxisColors[math.min(i, kAxisColors.length - 1)];

/// 번호 원의 **속** — 축 색 위에 검정을 겹쳐 어둡게 깐다.
///
/// 🔴 꽉 채우면 안 된다. 여섯 색은 밝기가 제각각이라(초록은 어둡고 노랑은
/// 밝다) 꽉 채우면 흰 숫자가 밝은 색 위에서 안 읽힌다 — 어둡게 깔면 **어느
/// 색이 와도** 읽히고 색은 여전히 보인다.
Color axisFill(int i) => Color.lerp(Colors.black, axisColor(i), 0.3)!;

/// 값 글자에 쓰는 축 색 — **흰 쪽으로 올린 것**이다.
///
/// 🔴 계열 색을 작은 글자에 그대로 쓰면 대비가 무너진다(어두운 축일수록
/// 심하다). 색은 살리되 읽히게 밝은 쪽으로 섞는다.
Color axisInk(int i) => Color.lerp(axisColor(i), _ink, 0.38)!;

/// 오버롤 레이더 — 항목마다 `stat`(0~100)을 축 삼아 다각형을 그린다.
///
/// 🔴 **이름을 축 끝에 놓지 않는다** — 한국어 이름은 길이가 제각각이라
/// 6축에서 서로 파고든다. 대신 **번호로 잇고** 범례에 이름을 적는다. 번호는
/// 한 글자라 길이가 일정해서 **겹침이 구조적으로 안 생긴다.**
class ReportRadar extends StatelessWidget {
  const ReportRadar({super.key, required this.axes});

  final List<RadarAxis> axes;

  @override
  Widget build(BuildContext context) {
    // 다각형이 안 되는 축 개수 — 그리지 않는다.
    if (axes.length < 3) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 🔴 그림을 **제 칸의 가운데**에 둔다. 범례와 한 덩어리로 가운데
        //    두면 그림만 보면 한쪽으로 치우친다.
        Center(
          child: SizedBox(
            width: 220,
            height: 220,
            child: CustomPaint(painter: _RadarPainter(axes)),
          ),
        ),
        const SizedBox(height: 14),
        for (var i = 0; i < axes.length; i += 1)
          Padding(
            padding: const EdgeInsets.only(bottom: 7),
            child: Row(
              children: [
                // 🔴 그림의 번호와 **같은 글자**다. 정렬하거나 뒤섞으면 짝이
                //    깨진다 — 시험이 순서를 붙든다.
                _NumDot(index: i),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    axes[i].name,
                    style: TextStyle(
                      color: _ink.withValues(alpha: 0.85),
                      fontSize: 13,
                    ),
                  ),
                ),
                Text(
                  '${axes[i].stat.round()}',
                  style: TextStyle(
                    color: axisInk(i),
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 2),
        /* 🔴 **총점은 이 값들의 평균이 아니다** — 등급의 가중합이다. 나란히
           두면 그렇게 읽히므로 캡션으로 막는다. */
        Text(
          '축은 항목별 측정값입니다 — 총점은 이 값들의 평균이 아니라 등급의 가중합입니다.',
          style: TextStyle(
            color: _ink.withValues(alpha: 0.5),
            fontSize: 11,
            height: 1.4,
          ),
        ),
      ],
    );
  }
}

/// 오버롤 등급 칩 — `S`~`F`.
class _GradeChip extends StatelessWidget {
  const _GradeChip({required this.grade});

  final String grade;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 40,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: _seed.withValues(alpha: 0.18),
        shape: BoxShape.circle,
        border: Border.all(color: _seed, width: 2),
      ),
      child: Text(
        grade,
        style: const TextStyle(
          color: _seed,
          fontSize: 19,
          fontWeight: FontWeight.w800,
          height: 1,
        ),
      ),
    );
  }
}

/// 범례의 번호 — 그림의 번호 원과 같은 모양.
class _NumDot extends StatelessWidget {
  const _NumDot({required this.index});

  final int index;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 18,
      height: 18,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: axisFill(index),
        shape: BoxShape.circle,
        border: Border.all(color: axisColor(index), width: 1.5),
      ),
      child: Text(
        '${index + 1}',
        // 🔴 **색은 고리가 입고 글자는 흰색이다.** 작은 글자에 계열 색을
        //    입히면 대비가 무너진다.
        style: const TextStyle(
          color: _ink,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          height: 1,
        ),
      ),
    );
  }
}

class _RadarPainter extends CustomPainter {
  _RadarPainter(this.axes);

  final List<RadarAxis> axes;

  @override
  void paint(Canvas canvas, Size size) {
    final n = axes.length;
    final center = Offset(size.width / 2, size.height / 2);
    /* 🔴 번호 원이 축 끝 **바깥**에 앉으므로 그만큼 그림을 안으로 들인다.
       안 그러면 12시·6시 번호가 상자 밖으로 잘린다. */
    final maxRadius = size.width / 2 - 26;
    final numRadius = maxRadius + 13;

    Offset pointAt(int i, double radius) {
      // 12시 방향부터 시계 방향.
      final angle = math.pi * 2 * i / n - math.pi / 2;
      return center +
          Offset(radius * math.cos(angle), radius * math.sin(angle));
    }

    // 기준선 — 축마다 중심에서 바깥까지. 참고용이라 값은 없다(recessive).
    final axisLine = Paint()
      ..color = _ink.withValues(alpha: 0.14)
      ..strokeWidth = 1;
    for (var i = 0; i < n; i += 1) {
      canvas.drawLine(center, pointAt(i, maxRadius), axisLine);
    }

    final verts = [
      for (var i = 0; i < n; i += 1)
        pointAt(i, axes[i].stat.clamp(0, 100) / 100 * maxRadius),
    ];

    /* 🔴 **채움과 변을 나눴다.** 변마다 색이 갈리므로 한 번에 못 그린다.
       채움은 **중립**이다 — 여섯 색이 도는 판에서 채움까지 색을 가지면
       어느 색이 어느 축인지가 흐려진다. */
    final path = Path()..addPolygon(verts, true);
    canvas.drawPath(
      path,
      Paint()..color = _ink.withValues(alpha: 0.10),
    );

    // 변 — 이웃한 두 축 색 사이의 그러데이션.
    for (var i = 0; i < n; i += 1) {
      final p = verts[i];
      final q = verts[(i + 1) % n];
      canvas.drawLine(
        p,
        q,
        Paint()
          ..strokeWidth = 2
          ..strokeCap = StrokeCap.round
          ..shader = ui.Gradient.linear(
            p,
            q,
            [axisColor(i), axisColor((i + 1) % n)],
          ),
      );
    }

    /* 🔴 번호는 **다각형 위에** 그린다 — 먼저 그리면 채움에 덮인다. 그리고
       원을 깔고 그 위에 글자를 얹는다: 축선이 번호를 가로지르면 한 자리
       숫자도 안 읽힌다. */
    for (var i = 0; i < n; i += 1) {
      final p = pointAt(i, numRadius);
      canvas.drawCircle(p, 10, Paint()..color = axisFill(i));
      canvas.drawCircle(
        p,
        10,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5
          ..color = axisColor(i),
      );
      final label = TextPainter(
        text: TextSpan(
          text: '${i + 1}',
          style: const TextStyle(
            color: _ink,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      label.paint(canvas, p - Offset(label.width / 2, label.height / 2));
    }
  }

  @override
  bool shouldRepaint(_RadarPainter old) => old.axes != axes;
}
