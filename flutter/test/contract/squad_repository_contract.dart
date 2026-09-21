import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/squad_repository.dart';

/// SquadRepository 의 모든 구현체가 지켜야 하는 계약.
///
/// 🔴 프로토콜의 성질만 둔다 — 구현체별 의무는 각자의 테스트 파일로.
///
/// [teamWithSquad] 는 스쿼드가 **있는** 팀, [teamWithoutSquad] 는 팀은 있으나
/// 스쿼드를 **아직 안 만든** 팀이다.
/// [cardIdToEnlist] 는 아직 등재되지 않은 카드의 id,
/// [freeSeat]·[takenSeat] 은 [teamWithSquad] 의 판에서 빈 칸과 이미 찬 칸이다.
void runSquadRepositoryContract(
  String name,
  SquadRepository Function() build, {
  required String teamWithSquad,
  required String teamWithoutSquad,
  required String cardIdToEnlist,
  required (int, int) freeSeat,
  required (int, int) takenSeat,
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

    test('카드를 판에 앉히면 바뀐 스쿼드 전체가 돌아온다', () async {
      final before = (await repo.squadOf(teamWithSquad))!.members.length;

      final squad = await repo.enlist(
        teamWithSquad,
        playerCardId: cardIdToEnlist,
        positionCode: 'FW',
        gridCol: freeSeat.$1,
        gridRow: freeSeat.$2,
      );

      expect(squad.members, hasLength(before + 1));
      final seated =
          squad.members.firstWhere((m) => m.playerCardId == cardIdToEnlist);
      expect(seated.gridCol, freeSeat.$1);
      expect(seated.gridRow, freeSeat.$2);
      expect(seated.positionCode, 'FW');
    });

    /// 🔴 스쿼드당 카드 1회(부록 D.7). 두 번 앉히면 같은 사람이 판에 둘이 된다.
    test('같은 카드를 두 번 앉히지 못한다', () async {
      await repo.enlist(
        teamWithSquad,
        playerCardId: cardIdToEnlist,
        positionCode: 'FW',
        gridCol: freeSeat.$1,
        gridRow: freeSeat.$2,
      );

      await expectLater(
        repo.enlist(
          teamWithSquad,
          playerCardId: cardIdToEnlist,
          positionCode: 'MF',
          gridCol: null,
          gridRow: null,
        ),
        throwsA(anything),
      );
    });

    /// 🔴 이미 찬 칸에는 못 놓는다 — 같은 칸에 둘이 서면 카드가 겹쳐 사라진다.
    test('이미 찬 칸에는 못 앉힌다', () async {
      await expectLater(
        repo.enlist(
          teamWithSquad,
          playerCardId: cardIdToEnlist,
          positionCode: 'GK',
          gridCol: takenSeat.$1,
          gridRow: takenSeat.$2,
        ),
        throwsA(anything),
      );
    });

    test('등재의 자리와 포지션을 바꾼다', () async {
      final seated = await repo.enlist(
        teamWithSquad,
        playerCardId: cardIdToEnlist,
        positionCode: 'FW',
        gridCol: freeSeat.$1,
        gridRow: freeSeat.$2,
      );
      final memberId =
          seated.members.firstWhere((m) => m.playerCardId == cardIdToEnlist).id;

      final moved = await repo.moveSeat(
        teamWithSquad,
        memberId: memberId,
        positionCode: 'MF',
        gridCol: 0,
        gridRow: 1,
      );

      final after = moved.members.firstWhere((m) => m.id == memberId);
      expect(after.gridCol, 0);
      expect(after.gridRow, 1);
      expect(after.positionCode, 'MF');
    });

    /// 🔴 칸을 둘 다 비우면 등재는 남기고 판에서만 뺀다.
    test('칸을 비우면 등재는 남고 판에서만 빠진다', () async {
      final seated = await repo.enlist(
        teamWithSquad,
        playerCardId: cardIdToEnlist,
        positionCode: 'FW',
        gridCol: freeSeat.$1,
        gridRow: freeSeat.$2,
      );
      final memberId =
          seated.members.firstWhere((m) => m.playerCardId == cardIdToEnlist).id;

      final moved = await repo.moveSeat(
        teamWithSquad,
        memberId: memberId,
        positionCode: 'FW',
        gridCol: null,
        gridRow: null,
      );

      final after = moved.members.firstWhere((m) => m.id == memberId);
      expect(after.hasSeat, isFalse);
    });

    test('남의 등재는 못 옮긴다', () async {
      await expectLater(
        repo.moveSeat(
          teamWithSquad,
          memberId: 'sm-남의것-0000',
          positionCode: 'MF',
          gridCol: 0,
          gridRow: 1,
        ),
        throwsA(anything),
      );
    });
  });
}
