import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/sport_repository.dart';

/// SportRepository의 모든 구현체가 지켜야 하는 계약.
///
/// auth 계약과 같은 규칙이다 — 여기에는 종목 조회 프로토콜의 성질만 두고,
/// 구현체 고유의 의무(Mock의 지연 하한 같은 것)는 구현체별 테스트로 내린다.
/// API가 나오면 이 파일을 ApiSportRepository에 그대로 물린다.
///
/// [build]는 매 테스트마다 깨끗한 구현체를 만들어 돌려준다.
/// [knownSportCode]는 그 구현체에 존재하는 종목 코드다.
void runSportRepositoryContract(
  String name,
  SportRepository Function() build, {
  required String knownSportCode,
}) {
  group('$name — SportRepository 계약', () {
    late SportRepository repo;

    setUp(() => repo = build());

    test('종목 목록을 돌려준다', () async {
      expect(await repo.sports(), isNotEmpty);
    });

    test('알려진 종목이 목록에 있다', () async {
      final codes = (await repo.sports()).map((s) => s.code);
      expect(codes, contains(knownSportCode));
    });

    test('종목 코드는 중복되지 않는다', () async {
      final codes = (await repo.sports()).map((s) => s.code).toList();
      expect(codes.toSet().length, equals(codes.length));
    });

    test('모든 종목은 표시할 이름을 갖는다', () async {
      for (final sport in await repo.sports()) {
        expect(sport.name, isNotEmpty);
      }
    });

    test('두 번 조회해도 같은 목록이다', () async {
      expect(await repo.sports(), equals(await repo.sports()));
    });
  });
}
