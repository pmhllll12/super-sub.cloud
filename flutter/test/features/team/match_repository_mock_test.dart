import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/match_repository_mock.dart';

import '../../contract/match_repository_contract.dart';

void main() {
  runMatchRepositoryContract(
    'MockMatchRepository',
    MockMatchRepository.new,
    myTeamId: 't-thunder',
    teamWithoutPrefs: 't-bears',
    knownRegion: '서울 강남구',
    incomingId: 'tmr-incoming',
  );

  group('MockMatchRepository 고유 규칙', () {
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await MockMatchRepository().regions();

      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(200));
    });

    /// 🔴 **시연용 자동 수락.** 심사에서 상대 기기로 수락을 눌러 줄 사람이
    /// 없다 — 웹의 `DEMO_ACCEPT_MS` 와 같은 결이고, 걷어낼 때도 같이 걷는다.
    test('몇 초 뒤 상대가 수락한다', () async {
      final repo = MockMatchRepository();
      final list = await repo.candidates('t-thunder');
      final made = await repo.requestMatch(
        't-thunder',
        targetTeamId: list.first.teamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '강남 풋살장',
      );

      expect(made.isPending, isTrue);

      await Future<void>.delayed(kDemoAcceptAfter + const Duration(seconds: 1));
      final after = (await repo.requests('t-thunder'))
          .firstWhere((r) => r.id == made.id);

      expect(after.isAccepted, isTrue);
      expect(after.matchId, isNotNull, reason: '수락되면 경기가 생긴다');
    });

    /// 🔴 **가짜인 것은 가짜라고 적는다** (2026-09-25 사용자 요청: 「팀
    /// 매칭이나 선수 꺼에서 mock 은 따로 mock 이라고 넣어줘. 그래야 그거 넣고
    /// 빠르게 시험하지」).
    ///
    /// 진짜 서버 값과 섞이면 **무엇을 보고 있는지 모른 채** 판단하게 된다 —
    /// 실제로 상대 팀 이름이 가짜인 것을 한참 못 알아봤다.
    test('가짜 팀은 이름에 mock 이 붙는다', () async {
      final list = await MockMatchRepository().candidates('t-thunder');

      expect(list.every((t) => t.name.contains('mock')), isTrue,
          reason: list.map((t) => t.name).join(' · '));
    });

    /// 🔴 시연에서 「비슷한 팀」이 비어 있으면 아무것도 못 보여 준다.
    test('시드 팀이 여럿이고 근거가 붙어 있다', () async {
      final list = await MockMatchRepository().candidates('t-thunder');

      expect(list.length, greaterThanOrEqualTo(3));
      expect(list.any((t) => t.reasons.isNotEmpty), isTrue);
    });
  });
}
