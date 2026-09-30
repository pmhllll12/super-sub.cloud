import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/team/data/regions.dart';
import 'package:super_sub/features/team/data/team_repository_mock.dart';

import '../../contract/team_repository_contract.dart';

/// 🔴 **하나의 `MockDb` 를 나눠 쓴다.** 주장 시점과 팀원 시점이 **같은 팀**을
/// 봐야 하므로 저장소가 갈라지면 안 된다.
void main() {
  late MockDb db;

  setUp(() => db = MockDb());

  runTeamRepositoryContract(
    'MockTeamRepository',
    // 시드: playerId 가 t-thunder 의 주장, managerId 가 그 팀의 팀원이다.
    asOwner: () => MockTeamRepository(db, userId: MockDb.playerId),
    asMember: () => MockTeamRepository(db, userId: MockDb.managerId),
    teamId: 't-thunder',
  );

  group('MockTeamRepository 고유 규칙', () {
    test('일부러 느리다', () async {
      final started = DateTime.now();

      await MockTeamRepository(db, userId: MockDb.playerId)
          .createTeam(name: '새 팀', region: '서울 마포구');

      expect(
        DateTime.now().difference(started).inMilliseconds,
        greaterThanOrEqualTo(200),
      );
    });

    /// 🔴 해체하면 소속과 판도 함께 간다 — 남으면 **없는 팀을 가리키는 행**이 된다.
    test('해체하면 소속과 스쿼드도 사라진다', () async {
      await MockTeamRepository(db, userId: MockDb.playerId)
          .disbandTeam('t-thunder');

      expect(db.teams.any((t) => t.id == 't-thunder'), isFalse);
      expect(db.teamMembers.any((m) => m.teamId == 't-thunder'), isFalse);
      expect(db.squads.any((s) => s.teamId == 't-thunder'), isFalse);
    });

    test('소속이 아닌 팀은 건드릴 수 없다', () async {
      final repo = MockTeamRepository(db, userId: MockDb.newbieId);

      await expectLater(repo.disbandTeam('t-thunder'), throwsA(anything));
      await expectLater(repo.leaveTeam('t-thunder'), throwsA(anything));
    });

    test('앞뒤 공백은 털고 저장한다', () async {
      final made = await MockTeamRepository(db, userId: MockDb.newbieId)
          .createTeam(name: '  새 팀  ', region: '서울 마포구');

      expect(made.name, '새 팀');
    });
  });

  group('지역 목록', () {
    /// 🔴 웹 `www/src/lib/regions.ts` 와 **글자 하나까지** 같아야 한다 —
    /// 어긋나면 그 팀이 남의 검색에서 빠진다.
    test('60개이고 시·도 + 시·군·구 꼴이다', () {
      expect(kRegions, hasLength(60));
      expect(kRegions.first, '서울 강남구');
      expect(kRegions.last, '제주 제주시');
      expect(kRegions.every((r) => r.contains(' ')), isTrue);
    });

    test('isRegion 은 앞뒤 공백을 턴다', () {
      expect(isRegion('  서울 마포구 '), isTrue);
      expect(isRegion('서울 마포'), isFalse);
      expect(isRegion('강남구'), isFalse);
    });

    /// 빈 글이면 전부 준다 — 처음 열었을 때 목록이 비어 있으면 무엇을 고르는
    /// 칸인지 안 읽힌다.
    test('빈 글로 찾으면 후보가 있다', () {
      expect(searchRegions(''), isNotEmpty);
    });

    test('적은 글로 좁힌다', () {
      expect(searchRegions('마포'), ['서울 마포구']);
      expect(searchRegions('제주'), ['제주 제주시']);
    });
  });
}
