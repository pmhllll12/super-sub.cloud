import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/squad_repository.dart';

/// SquadRepository 의 모든 구현체가 지켜야 하는 계약.
///
/// 🔴 프로토콜의 성질만 둔다 — 구현체별 의무는 각자의 테스트 파일로.
///
/// [teamWithSquad] 는 스쿼드가 **있는** 팀, [teamWithoutSquad] 는 팀은 있으나
/// 스쿼드를 **아직 안 만든** 팀이다.
void runSquadRepositoryContract(
  String name,
  SquadRepository Function() build, {
  required String teamWithSquad,
  required String teamWithoutSquad,
}) {
  group('$name — SquadRepository 계약', () {
    late SquadRepository repo;

    setUp(() => repo = build());

    test('스쿼드를 읽는다', () async {
      final squad = await repo.squadOf(teamWithSquad);

      expect(squad, isNotNull);
      expect(squad!.teamId, equals(teamWithSquad));
      expect(squad.publicSlug, isNotEmpty);
    });

    /// 🔴 빈 스쿼드를 돌려주면 「만들지 않은 것」과 「비어 있는 것」이 같아
    /// 보인다 — 계약이 404 SQUAD_NOT_FOUND 를 내는 이유가 그것이다.
    test('아직 안 만든 스쿼드는 예외가 아니라 null 이다', () async {
      expect(await repo.squadOf(teamWithoutSquad), isNull);
    });
  });
}
