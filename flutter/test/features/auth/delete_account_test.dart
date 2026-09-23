import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/data/auth_repository_api.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/data/token_store.dart';

http.Response jsonRes(Map<String, dynamic> body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

void main() {
  group('ApiAuthRepository 탈퇴', () {
    /// 🔴 **구글로만 가입한 계정에는 확인할 비밀번호가 없다.** 빈 문자열을
    /// 실으면 서버가 「틀린 비밀번호」로 읽어 **탈퇴할 방법이 사라진다**
    /// (계약 2장).
    test('비밀번호가 비어 있으면 본문을 아예 안 보낸다', () async {
      String? body;
      String? method;
      final repo = ApiAuthRepository(api: ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          method = req.method;
          body = req.body;
          return http.Response('', 204);
        }),
      ));

      await repo.deleteAccount();

      expect(method, 'DELETE');
      expect(body, isEmpty);
    });

    test('비밀번호가 있으면 실어 보낸다', () async {
      String? body;
      final repo = ApiAuthRepository(api: ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          body = req.body;
          return http.Response('', 204);
        }),
      ));

      await repo.deleteAccount(password: 'pw-1');

      expect(jsonDecode(body!), {'password': 'pw-1'});
    });

    /// 🔴 **계정이 사라졌는데 토큰이 남으면** 다음에 켤 때 그 토큰으로
    /// 되돌아가 401 만 돈다.
    test('끝나면 토큰을 지운다', () async {
      final tokens = InMemoryTokenStore();
      final api = ApiClient(
        tokens: tokens,
        client: MockClient((_) async => http.Response('', 204)),
      );
      await api.useToken('tok-1');

      await ApiAuthRepository(api: api).deleteAccount(password: 'pw');

      expect(await tokens.read(), isNull);
    });

    /// 🔴 **틀린 비밀번호는 그대로 올린다** — 삼키면 화면이 탈퇴된 줄 안다.
    test('401 이면 던지고 토큰을 안 지운다', () async {
      final tokens = InMemoryTokenStore();
      final api = ApiClient(
        tokens: tokens,
        client: MockClient((_) async => jsonRes({
              'error': {
                'code': 'INVALID_CREDENTIALS',
                'message': '비밀번호가 틀렸습니다',
              },
            }, 401)),
      );
      await api.useToken('tok-1');

      await expectLater(
        ApiAuthRepository(api: api).deleteAccount(password: 'wrong'),
        throwsA(isA<AuthException>()),
      );
      expect(await tokens.read(), equals('tok-1'));
    });
  });

  group('MockAuthRepository 탈퇴', () {
    /// 🔴 **계정과 파생 데이터가 함께 사라진다**(SEC-006). Mock 이 사용자만
    /// 지우면 탈퇴 뒤 「없는 사람의 카드」가 남는 상태를 앱에서 못 밟는다.
    test('카드·영상·소속이 함께 사라진다', () async {
      final db = MockDb();
      final repo = MockAuthRepository(db);
      await repo.loginAs(MockDb.playerId);

      // 지워질 것이 실제로 있는 상태인지 먼저 확인한다.
      expect(db.cards.any((c) => c.id == 'pc-${MockDb.playerId}'), isTrue);
      expect(db.videosOf(MockDb.playerId), isNotEmpty);

      await repo.deleteAccount();

      expect(db.users.any((u) => u.id == MockDb.playerId), isFalse);
      expect(db.cards.any((c) => c.id == 'pc-${MockDb.playerId}'), isFalse);
      expect(db.videosOf(MockDb.playerId), isEmpty);
      expect(
        db.teamMembers.any((m) => m.userId == MockDb.playerId),
        isFalse,
      );
    });

    test('로그인 안 했으면 던진다', () async {
      await expectLater(
        MockAuthRepository(MockDb()).deleteAccount(),
        throwsA(isA<AuthException>()),
      );
    });

    /// 🔴 남의 것은 안 건드린다 — 탈퇴가 DB 를 통째로 비우면 안 된다.
    test('남의 카드는 그대로다', () async {
      final db = MockDb();
      final repo = MockAuthRepository(db);
      await repo.loginAs(MockDb.playerId);

      await repo.deleteAccount();

      expect(db.cards.any((c) => c.id == 'pc-${MockDb.managerId}'), isTrue);
      expect(db.users.any((u) => u.id == MockDb.managerId), isTrue);
    });
  });
}
