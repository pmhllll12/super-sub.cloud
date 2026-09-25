import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/match_prefs.dart';
import 'package:super_sub/features/team/match_proposal.dart';

/// 2026-09-25 는 **금요일**이다.
final _fri = DateTime(2026, 9, 25, 10, 0);

void main() {
  group('nextOccurrence', () {
    test('이번 주에 아직 안 온 요일이면 이번 주다', () {
      // 토(6) 11:00 — 금요일에서 보면 내일이다.
      final at = nextOccurrence(
        const TimeSlot(day: 6, from: '11:00', to: '13:00'),
        _fri,
      );

      expect(at, DateTime(2026, 9, 26, 11, 0));
    });

    test('이미 지난 요일이면 다음 주다', () {
      // 화(2) — 금요일에서 보면 지났다.
      final at = nextOccurrence(
        const TimeSlot(day: 2, from: '11:00', to: '13:00'),
        _fri,
      );

      expect(at, DateTime(2026, 9, 29, 11, 0));
    });

    /// 🔴 **오늘이라도 시각이 지났으면 다음 주다.** 지난 시각으로 신청하면
    /// 서버가 받아 줘도 아무도 못 뛴다.
    test('오늘인데 시각이 지났으면 다음 주 같은 요일이다', () {
      // 금(5) 09:00 — 지금은 10:00 이다.
      final at = nextOccurrence(
        const TimeSlot(day: 5, from: '09:00', to: '11:00'),
        _fri,
      );

      expect(at, DateTime(2026, 10, 2, 9, 0));
    });

    test('오늘이고 시각이 아직이면 오늘이다', () {
      final at = nextOccurrence(
        const TimeSlot(day: 5, from: '18:00', to: '20:00'),
        _fri,
      );

      expect(at, DateTime(2026, 9, 25, 18, 0));
    });

    test('30분 단위도 그대로 산다', () {
      final at = nextOccurrence(
        const TimeSlot(day: 6, from: '11:30', to: '13:00'),
        _fri,
      );

      expect(at.minute, 30);
    });
  });

  group('proposalsFrom', () {
    /// 🔴 순서는 **실제 날짜 순**이다 — 조건에 적힌 순서가 아니다.
    test('이른 날짜부터 온다', () {
      final list = proposalsFrom(const [
        TimeSlot(day: 0, from: '09:00', to: '11:00'), // 일 → 9/27
        TimeSlot(day: 6, from: '11:00', to: '13:00'), // 토 → 9/26
      ], _fri);

      expect(list.map((p) => p.at.day).toList(), [26, 27]);
    });

    test('읽을 수 있는 이름이 붙는다', () {
      final list = proposalsFrom(
        const [TimeSlot(day: 6, from: '11:00', to: '13:00')],
        _fri,
      );

      expect(list.single.label, '토 09/26 11:00~13:00');
    });

    /// 🔴 **조건이 없으면 빈 목록이다.** 아무 시각이나 채워 넣으면 아무도
    /// 못 뛰는 경기가 잡힌다.
    test('조건이 없으면 빈 목록이다', () {
      expect(proposalsFrom(const [], _fri), isEmpty);
    });
  });

  group('toPlayedAt', () {
    /// 🔴 **UTC 로 바꾸지 않는다.** 사람이 고른 것은 **그 지역 시각의 11시**다 —
    /// UTC 로 보내면 「토 11:00」이 「토 02:00」으로 저장된다.
    test('고른 시각이 그대로 남는다', () {
      final s = toPlayedAt(DateTime(2026, 9, 26, 11, 0));

      expect(s, startsWith('2026-09-26T11:00:00'));
    });

    test('시간대 오프셋이 붙는다', () {
      final s = toPlayedAt(DateTime(2026, 9, 26, 11, 0));

      // `+09:00` 처럼 부호와 네 자리가 끝에 온다.
      expect(RegExp(r'[+-]\d{2}:\d{2}$').hasMatch(s), isTrue, reason: s);
    });
  });
}
