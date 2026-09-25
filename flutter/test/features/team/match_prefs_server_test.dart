import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/match_prefs.dart';
import 'package:super_sub/features/team/match_prefs_server.dart';

const _regions = [
  RefItem(id: 'r-gangnam', label: '서울 강남구'),
  RefItem(id: 'r-yeongdeungpo', label: '서울 영등포구'),
];

const _positions = [
  RefItem(id: 'p-mf', label: 'MF'),
  RefItem(id: 'p-gk', label: 'GK'),
];

void main() {
  /// 🔴 **여기가 이 파일의 존재 이유다.** 화면은 `0=일`(달력과 같은 기준),
  /// 계약은 `0=월`이다. 한 칸 밀리면 **화면에는 아무 표시도 안 나고** 겹침
  /// 계산만 조용히 틀린다.
  group('요일', () {
    test('화면 0(일) 은 계약 6 이다', () {
      expect(
        toServerSlot(const TimeSlot(day: 0, from: '09:00', to: '11:00'))
            .weekday,
        6,
      );
    });

    test('화면 1(월) 은 계약 0 이다', () {
      expect(
        toServerSlot(const TimeSlot(day: 1, from: '09:00', to: '11:00'))
            .weekday,
        0,
      );
    });

    test('이레를 왕복해도 그대로다', () {
      for (var day = 0; day < 7; day++) {
        final slot = TimeSlot(day: day, from: '09:00', to: '11:00');
        expect(toScreenSlot(toServerSlot(slot)).day, day, reason: '$day 요일');
      }
    });
  });

  group('시각', () {
    test('계약에는 초를 붙여 보낸다', () {
      final s = toServerSlot(const TimeSlot(day: 6, from: '09:00', to: '11:30'));

      expect(s.startTime, '09:00:00');
      expect(s.endTime, '11:30:00');
    });

    /// 🔴 서버가 초를 **안 붙여** 보내도 앞 다섯 자는 같다 — 그것도 받는다.
    test('초가 있어도 없어도 읽는다', () {
      expect(
        toScreenSlot(const MatchSlot(
                weekday: 5, startTime: '09:00:00', endTime: '11:00'))
            .from,
        '09:00',
      );
    });
  });

  group('지역', () {
    test('이름을 id 로 바꿔 보낸다', () {
      final body = toServerPrefs(
        const MatchPrefs(regions: ['서울 강남구'], times: []),
        _regions,
      );

      expect(body.regionIds, ['r-gangnam']);
    });

    /// 🔴 **모르는 이름은 버린다.** 그대로 보내면 422 `UNKNOWN_REGION` 이고,
    /// 계약의 `PUT` 은 **통째로 교체**라 그 한 줄 때문에 **조건 전체가**
    /// 저장되지 않는다. 이름을 지어내지도 않는다.
    test('모르는 이름은 버린다', () {
      final body = toServerPrefs(
        const MatchPrefs(regions: ['서울 강남구', '없는동네'], times: []),
        _regions,
      );

      expect(body.regionIds, ['r-gangnam']);
    });

    /// 🔴 **모르는 id 는 이름을 지어내지 않고 뺀다** — 「알 수 없음」 같은
    /// 글자로 채우면 사용자가 그것을 고른 줄로 읽는다.
    test('모르는 id 는 뺀다', () {
      final prefs = toScreenPrefs(
        const ServerPrefs(regionIds: ['r-gangnam', 'r-없는것'], slots: []),
        _regions,
      );

      expect(prefs.regions, ['서울 강남구']);
    });
  });

  group('포지션 (내 조건에만)', () {
    /// 🔴 화면은 약칭(`MF`)을, 계약은 id 를 쓴다 — 약칭은 **종목 안에서만**
    /// 유일해서(야구 `C`=포수 · 농구 `C`=센터) 그대로 보낼 수 없다.
    test('약칭을 id 로 바꿔 보낸다', () {
      final body = toServerMemberPrefs(
        const MatchPrefs(positions: ['MF']),
        _regions,
        _positions,
      );

      expect(body.positionIds, ['p-mf']);
    });

    test('모르는 약칭은 버린다', () {
      final body = toServerMemberPrefs(
        const MatchPrefs(positions: ['MF', 'PG']),
        _regions,
        _positions,
      );

      expect(body.positionIds, ['p-mf']);
    });

    /// ⚠️ **팀 조건에는 포지션이 없다**(계약이 개인 조건에만 둔다).
    test('팀 조건으로 읽으면 포지션은 늘 비어 있다', () {
      final prefs = toScreenPrefs(
        const ServerPrefs(regionIds: [], slots: []),
        _regions,
      );

      expect(prefs.positions, isEmpty);
    });
  });

  test('한 바퀴 돌아도 같다', () {
    const before = MatchPrefs(
      regions: ['서울 강남구', '서울 영등포구'],
      times: [
        TimeSlot(day: 6, from: '09:00', to: '11:00'),
        TimeSlot(day: 0, from: '18:00', to: '20:00'),
      ],
    );

    final body = toServerPrefs(before, _regions);
    final after = toScreenPrefs(
      ServerPrefs(regionIds: body.regionIds, slots: body.slots),
      _regions,
    );

    expect(after.regions, before.regions);
    expect(after.times, before.times);
  });
}
