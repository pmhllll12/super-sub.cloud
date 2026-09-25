import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/match_prefs.dart';

void main() {
  group('TimeSlot', () {
    test('한 줄로 읽는다', () {
      expect(const TimeSlot(day: 6, from: '09:00', to: '11:00').text,
          '토 09:00~11:00');
    });

    /// 🔴 **끝이 닿기만 한 것은 안 겹친 것이다** — `09:00~11:00` 과
    /// `11:00~13:00` 은 함께 뛸 시간이 0분이다.
    test('끝이 닿기만 하면 안 겹친다', () {
      const a = TimeSlot(day: 6, from: '09:00', to: '11:00');
      const b = TimeSlot(day: 6, from: '11:00', to: '13:00');

      expect(a.overlaps(b), isFalse);
    });

    test('겹치면 겹친 것이다', () {
      const a = TimeSlot(day: 6, from: '09:00', to: '12:00');
      const b = TimeSlot(day: 6, from: '11:00', to: '13:00');

      expect(a.overlaps(b), isTrue);
    });

    test('요일이 다르면 안 겹친다', () {
      const a = TimeSlot(day: 6, from: '09:00', to: '12:00');
      const b = TimeSlot(day: 0, from: '09:00', to: '12:00');

      expect(a.overlaps(b), isFalse);
    });
  });

  group('고를 수 있는 시각', () {
    /// 🔴 **24:00 이 끝에 있어야 한다** — 없으면 밤 경기의 끝을 23:30 까지
    /// 밖에 못 적는다.
    test('06:00 부터 24:00 까지 30분 단위다', () {
      expect(kHours.first, '06:00');
      expect(kHours.last, '24:00');
      expect(kHours, contains('06:30'));
      expect(kHours, hasLength(37));
    });
  });

  group('요일 이름', () {
    /// 🔴 화면의 `day` 는 `DateTime.weekday` 가 아니라 **0=일** 기준이다 —
    /// 계약(0=월)과 어긋나는 지점이라 여기서 못 박는다.
    test('0 이 일요일이다', () {
      expect(kDays[0], '일');
      expect(kDays[6], '토');
    });
  });
}
