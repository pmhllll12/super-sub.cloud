import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/contact_repository.dart';

/// ContactRepository 의 모든 구현체가 지켜야 하는 계약 — 계약 3-12절.
///
/// 🔴 프로토콜의 성질만 둔다 — 구현체별 의무(검색어 인코딩 · Mock 지연)는
/// 각자의 테스트 파일로.
///
/// [knownNickname] 은 검색하면 나오는 사람, [strangerId] 는 아직 지인이 아닌
/// 사람, [pendingRequestId] 는 나에게 온 대기중 신청의 id 다.
void runContactRepositoryContract(
  String name,
  ContactRepository Function() build, {
  required String knownNickname,
  required String strangerId,
  required String pendingRequestId,
  required String myOwnId,
}) {
  group('$name — ContactRepository 계약', () {
    late ContactRepository repo;

    setUp(() => repo = build());

    test('수락된 지인 목록을 읽는다', () async {
      final list = await repo.contacts();

      expect(list, isNotEmpty);
      expect(list.every((c) => c.nickname.isNotEmpty), isTrue);
    });

    test('나에게 온 대기중 신청을 읽는다', () async {
      final list = await repo.requests();

      expect(list.any((r) => r.id == pendingRequestId), isTrue);
    });

    test('닉네임 일부로 찾는다', () async {
      final found = await repo.search(knownNickname.substring(0, 2));

      expect(found.any((f) => f.nickname == knownNickname), isTrue);
    });

    /// 🔴 **못 찾은 것은 오류가 아니다** — 빈 목록이다.
    test('아무도 없으면 빈 목록이다', () async {
      expect(await repo.search('없는닉네임입니다'), isEmpty);
    });

    test('지인을 신청한다', () async {
      await repo.request(strangerId);
    });

    /// 🔴 **이미 신청했거나 이미 지인이면(409) 성공으로 친다.** 사용자가 보기엔
    /// 원하던 상태(신청이 가 있다)가 이미 이뤄진 것이라, 빨간 오류를 띄우면
    /// 자기가 뭘 잘못한 줄 안다. 웹도 같은 판단이다.
    test('두 번 신청해도 실패가 아니다', () async {
      await repo.request(strangerId);
      await repo.request(strangerId);
    });

    /// 🔴 자기 자신은 다르다 — 이건 화면이 막아야 할 실수라 드러내야 한다.
    test('자기 자신에게는 못 신청한다', () async {
      await expectLater(repo.request(myOwnId), throwsA(anything));
    });

    test('받은 신청을 수락하면 목록에서 빠진다', () async {
      await repo.accept(pendingRequestId);

      final after = await repo.requests();
      expect(after.any((r) => r.id == pendingRequestId), isFalse);
    });

    test('없는 신청은 못 수락한다', () async {
      await expectLater(repo.accept('ct-없는것'), throwsA(anything));
    });
  });
}
