import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/candidate_repository_mock.dart';

import '../../contract/candidate_repository_contract.dart';

void main() {
  runCandidateRepositoryContract(
    'MockCandidateRepository',
    MockCandidateRepository.new,
    teamId: 't-thunder',
    position: 'DF',
    // 시드에 GK 후보를 한 명도 안 둔다 — 「없음」 갈래를 반드시 밟는다.
    emptyPosition: 'GK',
    unknownPosition: 'PG', // 농구 포지션 — 축구 팀엔 없다
    foreignTeamId: 't-bears',
    cardSlugWithVideo: 'kim-abc1',
    cardSlugWithoutVideo: 'line-3a92',
  );

  group('MockCandidateRepository 고유 규칙', () {
    /// 🔴 계약 테스트에 두지 않는다 — Mock 에만 있는 의무다. 즉시 성공하면
    /// 로딩 화면을 아예 안 만들게 된다.
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await MockCandidateRepository().candidates('t-thunder',
          positionCode: 'DF');

      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(200));
    });

    /// 🔴 화면이 세 갈래(등급 있음 · 등급 모름 · 카드 없음)를 다 그려 보게
    /// 시드를 섞어 둔다. 한 갈래만 있으면 나머지 둘은 실서버에서 처음 만난다.
    test('시드에 등급·검수 전·카드 없음이 모두 있다', () async {
      final list =
          await MockCandidateRepository().candidates('t-thunder',
              positionCode: 'DF');

      expect(list.any((c) => c.grade != null && c.provisional == false), isTrue);
      expect(list.any((c) => c.provisional == true), isTrue);
      expect(list.any((c) => !c.hasCard), isTrue);
      expect(list.any((c) => c.notes.length == 1), isTrue);
    });
  });
}
