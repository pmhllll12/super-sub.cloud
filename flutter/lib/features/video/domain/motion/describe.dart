/// 비교 문장을 **코드 규칙으로** 쓴다 (2026-09-14 결정 — Gemini 없이).
///
/// 🔴 숫자는 입력 그대로다 — **지어낼 여지가 없다.** 웹
/// `www/src/lib/motion/describe.ts` 를 문구 한 글자까지 그대로 옮겼다.
/// 두 화면이 같은 영상에 다른 말을 하면 그게 곧 버그다.
library;

import 'angles.dart';
import 'motion.dart';

/// 이보다 작은 차이는 「비슷함」 — 검출의 흔들림이 몇 도는 된다.
const int kSimilarDeg = 5;

/// `more` 는 **내 값이 선수보다 클 때**의 말이다 — 값이 크다는 뜻이 항목마다 다르다.
const Map<Metric, ({String more, String less})> _phrase = {
  Metric.plantKneeFlexion: (
    more: '디딤발 무릎을 {d}° 덜 굽혔습니다',
    less: '디딤발 무릎을 {d}° 더 굽혔습니다',
  ),
  Metric.swingKneeExtension: (
    more: '차는 다리를 {d}° 더 폈습니다',
    less: '차는 다리를 {d}° 덜 폈습니다',
  ),
  Metric.trunkLean: (
    more: '상체가 차는 방향으로 {d}° 더 기울었습니다',
    less: '상체가 차는 방향으로 {d}° 덜 기울었습니다',
  ),
  Metric.followThrough: (
    more: '차는 다리를 {d}° 더 높이 들었습니다',
    less: '차는 다리를 {d}° 덜 높이 들었습니다',
  ),
};

String describeLine(MetricRow r) {
  final d = r.user - r.player;
  final base = '${r.label} 선수 ${r.player}° · 나 ${r.user}°';
  if (d.abs() < kSimilarDeg) return '$base — 비슷합니다';
  final p = _phrase[r.metric]!;
  final phrase = d > 0 ? p.more : p.less;
  return '$base — ${phrase.replaceAll('{d}', '${d.abs()}')}';
}

/// 한 순간의 줄들.
class MomentLines {
  const MomentLines({required this.key, required this.lines});
  final MomentKey key;
  final List<String> lines;
}

class ComparisonText {
  const ComparisonText({required this.moments, required this.summary});
  final List<MomentLines> moments;
  final String summary;
}

/// 순간마다의 행들 — 비교의 입력.
class MomentMetrics {
  const MomentMetrics({required this.key, required this.metrics});
  final MomentKey key;
  final List<MetricRow> metrics;
}

/// 세 순간의 행을 문장으로. 총평은 **가장 큰 차이 하나**를 짚는다.
ComparisonText describeComparison(List<MomentMetrics> input) {
  ({MomentKey key, MetricRow row, int gap})? biggest;
  var measured = 0;

  final moments = [
    for (final m in input)
      () {
        for (final row in m.metrics) {
          measured += 1;
          final gap = (row.user - row.player).abs();
          if (gap >= kSimilarDeg && (biggest == null || gap > biggest!.gap)) {
            biggest = (key: m.key, row: row, gap: gap);
          }
        }
        return MomentLines(
          key: m.key,
          lines: m.metrics.isEmpty
              ? const ['이 순간은 잴 수 없었습니다']
              : [for (final r in m.metrics) describeLine(r)],
        );
      }(),
  ];

  final top = biggest;
  final summary = measured == 0
      ? '잴 수 있는 순간이 없어 비교하지 못했습니다.'
      : top == null
      ? '세 순간 모두 선수와 비슷합니다.'
      : '가장 큰 차이는 ${top.key.label}의 ${top.row.label}입니다'
            ' — 선수 ${top.row.player}° · 나 ${top.row.user}°(${top.gap}° 차이).';

  return ComparisonText(moments: moments, summary: summary);
}
