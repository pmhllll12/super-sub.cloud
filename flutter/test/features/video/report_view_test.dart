import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/models/video_report.dart';
import 'package:super_sub/features/video/presentation/widgets/report_view.dart';

/* 🔴 **리포트가 두 바탕에서 산다** (2026-09-24). 원래는 어두운 바탕 전용이었고
   프로필의 리포트 화면(`report_screen.dart`, 바탕 `#14201A`)과 웹이 그 전제를
   나눠 썼다. 앱의 「영상 분석」 화면이 리포트를 **흰 판**에 쓰기로 하면서
   갈래가 생겼다 — **사용자가 그 갈림을 알고 골랐다**(「갈려져도 괜찮지 않아?
   그 흰색 판에 리포트가 쓰여야지」).

   이 시험이 지키는 것: **글자색이 바탕을 따라 실제로 뒤집히는가.** 안 뒤집히면
   한쪽에서 글자가 통째로 안 보이는데, `analyze` 도 시험도 아무 말을 안 한다. */

VideoReport _report() => const VideoReport(
  summary: '디딤발이 단단합니다.',
  points: [ReportPoint(title: '단단한 축', evidence: '무릎이 덜 흔들렸습니다.')],
  scenes: [ReportScene(at: '0:07', what: '디딤발이 먼저 닿습니다.')],
  radar: [
    RadarAxis(name: '디딤발 무릎 굽히기', stat: 72),
    RadarAxis(name: '차는 다리 뻗기', stat: 55),
    RadarAxis(name: '상체 기울기', stat: 61),
  ],
  totalScore: 74,
  overallGrade: 'B',
  savedAt: '2026-09-24',
);

Future<void> _pump(WidgetTester tester, {required bool onPaper}) =>
    tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          backgroundColor: onPaper ? Colors.white : const Color(0xFF14201A),
          body: SingleChildScrollView(
            child: ReportView(report: _report(), onPaper: onPaper),
          ),
        ),
      ),
    );

/// 그 글자의 색 — 없으면 시험이 거기서 멈춘다.
Color _colorOf(WidgetTester tester, String text) {
  final t = find.text(text);
  expect(t, findsOneWidget, reason: '「$text」이 화면에 없다');
  return tester.widget<Text>(t).style!.color!;
}

/// 흰 바탕에서 읽히는가 — 대충이라도 어두워야 한다.
bool _darkEnough(Color c) => c.computeLuminance() < 0.4;

void main() {
  testWidgets('어두운 바탕에서는 글자가 밝다', (tester) async {
    await _pump(tester, onPaper: false);

    expect(_colorOf(tester, '디딤발이 단단합니다.').computeLuminance(), greaterThan(0.6));
    expect(_colorOf(tester, '74점').computeLuminance(), greaterThan(0.6));
  });

  testWidgets('흰 바탕에서는 글자가 어둡다', (tester) async {
    await _pump(tester, onPaper: true);

    expect(_darkEnough(_colorOf(tester, '디딤발이 단단합니다.')), isTrue, reason: '총평');
    expect(_darkEnough(_colorOf(tester, '74점')), isTrue, reason: '오버롤 점수');
    expect(_darkEnough(_colorOf(tester, '이렇게 본 장면')), isTrue, reason: '머리글');
    expect(_darkEnough(_colorOf(tester, '무릎이 덜 흔들렸습니다.')), isTrue, reason: '근거');
    expect(_darkEnough(_colorOf(tester, '디딤발이 먼저 닿습니다.')), isTrue, reason: '장면');
  });

  /* 🔴 **초록을 그대로 못 쓴다.** `#70ED88` 은 흰 판 위에서 대비가 2:1 도 안
     나와서 **칭호와 장면 시각이 사라진다.** 같은 계열에서 어둡게 내린 값을
     쓰는데, 그걸 안 지키면 여기서 걸린다. */
  testWidgets('흰 바탕에서는 칭호·시각의 초록도 어둡게 내려간다', (tester) async {
    await _pump(tester, onPaper: true);

    expect(_darkEnough(_colorOf(tester, '단단한 축')), isTrue, reason: '칭호');
    expect(_darkEnough(_colorOf(tester, '0:07')), isTrue, reason: '장면 시각');
    expect(_darkEnough(_colorOf(tester, 'B')), isTrue, reason: '등급 칩');
  });

  /* 🔴 **축 색은 안 뒤집는다.** 여섯 색은 색각 이상 검사를 통과한 한 벌이라
     바탕이 바뀌었다고 손대면 **그 검사를 다시 해야 한다.** 작은 글자에 쓰는
     [axisInk] 만 방향을 바꾼다. */
  testWidgets('축 팔레트 자체는 바탕과 무관하다', (tester) async {
    expect(axisColor(0), kAxisColors[0]);
    // 흰 바탕에서는 어둡게, 어두운 바탕에서는 밝게 — 방향이 반대다.
    expect(
      axisInk(0, onPaper: true).computeLuminance(),
      lessThan(axisInk(0).computeLuminance()),
    );
  });
}
