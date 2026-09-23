import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/team_repository.dart';

/// TeamRepository 의 모든 구현체가 지켜야 하는 계약.
///
/// 🔴 여기에는 **프로토콜의 성질만** 둔다. Mock 전용 의무(지연 하한)는
/// 구현체별 파일로 내린다.
///
/// 🔴 **두 시점으로 나눠 받는다.** 「주장이라 해체는 되는데 나가기는 안 되는」
/// 것과 「팀원이라 그 반대인」 것을 **한 사람으로는 못 잰다** — 같은 팀에서
/// 두 역할을 동시에 가질 수 없기 때문이다.
///
/// [asOwner] 는 [teamId] 의 **주장**으로, [asMember] 는 같은 팀의 **팀원**으로
/// 보는 구현체를 만든다.
void runTeamRepositoryContract(
  String name, {
  required TeamRepository Function() asOwner,
  required TeamRepository Function() asMember,
  required String teamId,
}) {
  group('$name — TeamRepository 계약', () {
    late TeamRepository repo;

    setUp(() => repo = asOwner());

    test('팀을 만들면 내가 주장이다', () async {
      final made = await repo.createTeam(name: '새 팀', region: '서울 마포구');

      expect(made.name, '새 팀');
      expect(made.region, '서울 마포구');
      // 🔴 만든 사람이 owner 로 함께 들어간다(계약).
      expect(made.isOwner, isTrue);
    });

    /// 🔴 **목록에 없는 지역을 받으면** 저장은 되는데 남의 검색에 안 뜨는
    /// 팀이 된다 — 지역 거르기가 글자 비교라서다.
    test('목록에 없는 지역은 거부한다', () async {
      await expectLater(
        repo.createTeam(name: '새 팀', region: '화성 어딘가'),
        throwsA(anything),
      );
    });

    test('빈 이름은 거부한다', () async {
      await expectLater(
        repo.createTeam(name: '   ', region: '서울 마포구'),
        throwsA(anything),
      );
    });

    test('너무 긴 이름은 거부한다 — 조용히 자르지 않는다', () async {
      await expectLater(
        repo.createTeam(name: '가' * (kMaxTeamName + 1), region: '서울 마포구'),
        throwsA(anything),
      );
    });

    test('보낸 것만 바뀐다 — 이름만 고치면 지역은 그대로', () async {
      final before = await repo.updateTeam(teamId, region: '서울 송파구');

      final after = await repo.updateTeam(teamId, name: '이름만');

      expect(after.name, '이름만');
      expect(after.region, equals(before.region));
    });

    /// 🔴 **주장은 못 나간다** — 남은 사람들의 팀이 주인 없이 남는다.
    test('주장은 나갈 수 없다', () async {
      await expectLater(repo.leaveTeam(teamId), throwsA(anything));
    });

    test('팀원은 나갈 수 있다', () async {
      await asMember().leaveTeam(teamId);
    });

    test('주장이 아니면 해체할 수 없다', () async {
      await expectLater(asMember().disbandTeam(teamId), throwsA(anything));
    });

    test('주장이 아니면 고칠 수 없다', () async {
      await expectLater(
        asMember().updateTeam(teamId, name: '남의 팀'),
        throwsA(anything),
      );
    });

    test('주장은 해체할 수 있다', () async {
      await repo.disbandTeam(teamId);
    });
  });
}
