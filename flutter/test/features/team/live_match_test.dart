import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/match_candidate.dart';
import 'package:super_sub/features/team/live_match.dart';

final _now = DateTime(2026, 9, 25, 12, 0);

TeamMatchRequest _r({
  String status = 'accepted',
  String? matchId = 'm-1',
  String playedAt = '2026-10-03T11:00:00+09:00',
}) =>
    TeamMatchRequest(
      id: 'tmr-1',
      requesterTeamId: 't-thunder',
      targetTeamId: 't-gangnam',
      status: status,
      playedAt: playedAt,
      place: '강남 풋살장',
      matchId: matchId,
    );

void main() {
  /// 🔴 **이 판단을 두 곳에서 따로 하면 안 된다** — 웹이 세 번 신고받은
  /// 자리다(`useNotifyInbox.ts` 의 `isLiveConfirmed` 머리말). 머리칸 표시와
  /// 대기 화면이 **서로 다른 조건**을 쓰는 바람에, 「경기 완료」를 눌러도
  /// 같은 갱신이 판을 곧바로 되살렸다. 그래서 여기 한 함수뿐이다.
  group('isLiveConfirmed', () {
    test('수락됐고 경기가 있고 아직 안 지났으면 살아 있다', () {
      expect(isLiveConfirmed(_r(), now: _now), isTrue);
    });

    test('아직 수락 전이면 아니다', () {
      expect(isLiveConfirmed(_r(status: 'pending', matchId: null), now: _now),
          isFalse);
    });

    /// 🔴 **`match_id` 가 비면 물린 경기다.** 취소는 `match` 행만 지우고
    /// `status` 는 `accepted` 로 남는다(외래키가 `match_id` 만 비운다) —
    /// `status` 만 보면 취소된 경기를 계속 켠다.
    test('경기가 물렸으면 아니다', () {
      expect(isLiveConfirmed(_r(matchId: null), now: _now), isFalse);
    });

    test('이미 지난 경기는 아니다', () {
      expect(
        isLiveConfirmed(_r(playedAt: '2026-09-01T11:00:00+09:00'), now: _now),
        isFalse,
      );
    });

    /// 🔴 시각을 못 읽으면 **살아 있다고 보지 않는다** — 모르는 값으로
    /// 대기 화면을 띄우면 무엇을 기다리는지도 못 적는다.
    test('시각을 못 읽으면 아니다', () {
      expect(isLiveConfirmed(_r(playedAt: '이상한값'), now: _now), isFalse);
    });

    /// 🔴 **끝낸 경기는 안 켠다.** 서버에 「완료」 상태가 없어서 기기에
    /// 적어 둔 것을 본다 — 없으면 「경기 완료」를 눌러도 곧바로 되살아난다.
    test('끝냈다고 적어 둔 경기는 아니다', () {
      expect(isLiveConfirmed(_r(), now: _now, done: {'m-1'}), isFalse);
    });
  });

  group('firstLiveMatch', () {
    test('살아 있는 것 하나를 고른다', () {
      final live = firstLiveMatch(
        [_r(status: 'rejected', matchId: null), _r()],
        now: _now,
      );

      expect(live?.matchId, 'm-1');
    });

    test('없으면 null 이다', () {
      expect(firstLiveMatch([_r(status: 'pending', matchId: null)], now: _now),
          isNull);
    });
  });
}
