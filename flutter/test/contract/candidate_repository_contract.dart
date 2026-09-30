import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/candidate_repository.dart';

/// CandidateRepository 의 모든 구현체가 지켜야 하는 계약 — 계약 3-14절
/// `GET /teams/{id}/squad/candidates`.
///
/// 🔴 프로토콜의 성질만 둔다 — 구현체별 의무(쿼리를 실제로 싣는가 · Mock 의
/// 지연)는 각자의 테스트 파일로.
///
/// [teamId] 는 후보가 있는 팀, [emptyPosition] 은 그 팀에서 **후보가 한 명도
/// 없는** 포지션, [unknownPosition] 은 그 팀 종목에 **없는** 포지션 코드다.
void runCandidateRepositoryContract(
  String name,
  CandidateRepository Function() build, {
  required String teamId,
  required String position,
  required String emptyPosition,
  required String unknownPosition,
  required String foreignTeamId,
  required String cardSlugWithVideo,
  required String cardSlugWithoutVideo,
}) {
  group('$name — CandidateRepository 계약', () {
    late CandidateRepository repo;

    setUp(() => repo = build());

    test('그 자리의 후보를 돌려준다', () async {
      final list = await repo.candidates(teamId, positionCode: position);

      expect(list, isNotEmpty);
      expect(list.every((c) => c.nickname.isNotEmpty), isTrue);
    });

    /// 🔴 **후보가 없는 것은 오류가 아니다.** 예외로 내면 화면이 「불러오지
    /// 못했습니다」를 띄우는데, 실제로는 조건에 맞는 사람이 없을 뿐이라
    /// 사용자가 등급 필터를 풀 생각을 못 하게 된다.
    test('후보가 없으면 예외가 아니라 빈 목록이다', () async {
      expect(
        await repo.candidates(teamId, positionCode: emptyPosition),
        isEmpty,
      );
    });

    /// 🔴 등급은 **하드 필터**다(계약). 걸러서 받는 것이지 받아서 거르는 것이
    /// 아니라, 머리말의 「N명」이 필터를 따라 움직여야 한다.
    test('등급을 주면 그 등급만 온다', () async {
      final list =
          await repo.candidates(teamId, positionCode: position, grade: 'A');

      expect(list, isNotEmpty);
      expect(list.every((c) => c.grade == 'A'), isTrue);
    });

    /// 🔴 `grade` 를 안 주면 **거르지 않는다** — 등급을 모르는 사람도 남는다.
    test('등급을 안 주면 등급 모르는 사람도 남는다', () async {
      final list = await repo.candidates(teamId, positionCode: position);

      expect(list.any((c) => c.grade == null), isTrue);
    });

    /// 🔴 **서버가 정렬한 순서 그대로**다. 두 번 불러도 같은 순서여야 화면이
    /// 다시 줄 세우지 않았다는 것이 드러난다.
    test('순서를 화면이 다시 정하지 않는다', () async {
      final first = await repo.candidates(teamId, positionCode: position);
      final again = await repo.candidates(teamId, positionCode: position);

      expect(
        again.map((c) => c.userId).toList(),
        equals(first.map((c) => c.userId).toList()),
      );
    });

    /// 🔴 후보 옆에 도는 장면 — 그 사람의 **대표 영상**이다. 여기서는 id 만
    /// 받아 앱의 포스터 경로에 넘긴다(포스터는 이미 재시도가 붙어 있다).
    test('후보의 대표 영상 id 를 얻는다', () async {
      expect(await repo.featuredVideoId(cardSlugWithVideo), isNotNull);
    });

    /// 🔴 **대표 영상이 없는 것은 오류가 아니다**(404 가 정상이다). 예외로
    /// 올리면 줄 하나 때문에 시트 전체가 오류 화면이 된다.
    test('대표 영상이 없으면 예외가 아니라 null 이다', () async {
      expect(await repo.featuredVideoId(cardSlugWithoutVideo), isNull);
    });

    test('그 종목에 없는 포지션은 예외다', () async {
      await expectLater(
        repo.candidates(teamId, positionCode: unknownPosition),
        throwsA(anything),
      );
    });

    /// 🔴 **보는 권한**이다 — 그 팀 소속이 아니면 403. (후보 범위와는 다른
    /// 이야기다: 후보는 팀 **밖에서** 찾는다.)
    test('남의 팀 후보는 못 본다', () async {
      await expectLater(
        repo.candidates(foreignTeamId, positionCode: position),
        throwsA(anything),
      );
    });
  });
}
