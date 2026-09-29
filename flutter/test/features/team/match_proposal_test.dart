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

  /* 🔴 **조건 밖의 날짜** (2026-09-29 사용자 지적: 「다음주일 수도 있고
     다음달일 수도 있는거잖아」). 조건은 매주 반복이라 [proposalsFrom] 은
     「다음에 오는 그 요일」 한 번만 만든다 — 2주 뒤·다음 달로 갈 길이 없었다. */
  group('Proposal.custom', () {
    test('고른 시각을 그대로 들고 있다', () {
      final p = Proposal.custom(DateTime(2026, 11, 15, 14, 30));

      expect(p.at, DateTime(2026, 11, 15, 14, 30));
      expect(p.isCustom, isTrue);
    });

    /// 🔴 **끝 시각을 지어내지 않는다** — 계약이 `played_at` 하나만 받으므로
    /// 끝은 어차피 안 나간다. 없는 값을 적으면 상대가 약속으로 읽는다.
    test('이름에 끝 시각이 없다', () {
      final p = Proposal.custom(DateTime(2026, 11, 15, 14, 30));

      expect(p.label, '일 11/15 14:30');
      expect(p.label, isNot(contains('~')));
    });

    /// 추천은 `isCustom` 이 거짓이라 화면이 둘을 가를 수 있다.
    test('조건에서 나온 것과 구별된다', () {
      final from = proposalsFrom(
        const [TimeSlot(day: 6, from: '11:00', to: '13:00')],
        _fri,
      ).single;

      expect(from.isCustom, isFalse);
    });
  });

  group('withCustom', () {
    final base = proposalsFrom(
      const [TimeSlot(day: 6, from: '11:00', to: '13:00')], // 토 9/26
      _fri,
    );

    test('고른 것이 없으면 추천 그대로다', () {
      expect(withCustom(base, null), same(base));
    });

    /// 🔴 **고른 값이 목록 안에 있어야 `DropdownButton` 이 그린다.**
    test('끼워 넣고 날짜 순으로 세운다', () {
      final early = Proposal.custom(DateTime(2026, 9, 25, 20, 0)); // 오늘 밤
      final list = withCustom(base, early);

      expect(list.length, 2);
      expect(list.first.at, early.at, reason: '이른 것이 앞이다');
    });

    test('다음 달도 들어간다', () {
      final far = Proposal.custom(DateTime(2026, 11, 15, 14, 0));
      final list = withCustom(base, far);

      expect(list.last.at.month, 11);
    });

    /// 🔴 **같은 시각이면 추천 쪽을 남긴다** — 끝 시각까지 있어 더 많은 것을
    /// 말해 준다. 둘 다 두면 같은 시각이 두 줄로 보인다.
    test('같은 시각이면 추천이 이긴다', () {
      final same_ = Proposal.custom(base.single.at);
      final list = withCustom(base, same_);

      expect(list.length, 1);
      expect(list.single.isCustom, isFalse);
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
