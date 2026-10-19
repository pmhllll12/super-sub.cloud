/// 앱을 켤 때 **인사말이 서버를 안 기다린다** (2026-09-25 사용자 지적:
/// 「안녕하세요, 닉네임 그거랑 손 아이콘도 왜 바로바로 안나오냐」).
///
/// 🔴 **원인은 서버가 느린 것이 아니라 앱이 안 저장한 것이었다.** 토큰은
/// 기기에 남기면서 **사용자는 메모리에만** 들고 있어서, 앱을 끄면 사라지고
/// 켤 때마다 `GET /me` 를 기다렸다. 실서버 기준선이 0.6~4.6초라 그만큼
/// 인사말·손·카드가 통째로 비어 있었다.
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/features/auth/data/auth_repository_api.dart';
import 'package:super_sub/features/auth/data/token_store.dart';

const _me = {
  'id': 'u-1',
  'email': 'a@b.c',
  'nickname': '백성검',
  'created_at': '2026-09-03T00:00:00Z',
  'is_nickname_searchable': true,
  'teams': <dynamic>[],
};

http.Client loginServer({Map<String, dynamic> me = _me}) => MockClient((
  req,
) async {
  if (req.url.path.endsWith('/auth/login')) {
    return http.Response(jsonEncode({'access_token': 'tok-1'}), 200);
  }
  return http.Response(jsonEncode(me), 200, headers: _json);
});

const _json = {'content-type': 'application/json; charset=utf-8'};

void main() {
  group('세션 캐시', () {
    /// 🔴 **이 시험이 회귀를 잡는 자리다.** `/me` 가 영영 안 오는 서버를 물려도
    /// 복원이 끝나야 한다 — 기다리면 여기서 타임아웃으로 걸린다.
    test('저장해 둔 사용자가 있으면 GET /me 를 안 기다린다', () async {
      final store = InMemoryTokenStore();

      // 1) 한 번 로그인해 둔다 — 여기서 사용자가 기기에 남아야 한다.
      await ApiAuthRepository(
        tokens: store,
        client: loginServer(),
      ).login(email: 'a@b.c', password: 'pw');

      // 2) 앱을 껐다 켠 셈 — 리포지토리는 새것, 저장소는 그대로.
      //    서버는 `/me` 에 **영영 안 답한다.**
      final hung = Completer<http.Response>();
      final restored = await ApiAuthRepository(
        tokens: store,
        client: MockClient((req) => hung.future),
      ).restoreSession().timeout(const Duration(seconds: 2));

      expect(restored, isNotNull);
      expect(restored!.user.nickname, '백성검');
    });

    /// 🔴 **저장해 둔 값은 낡을 수 있다** — 웹에서 닉네임을 바꿨을 수 있다.
    /// 그래서 즉시 보여 주고 **뒤에서 새로 고친다.**
    test('돌려준 뒤 서버 값으로 새로 고친다', () async {
      final store = InMemoryTokenStore();
      await ApiAuthRepository(
        tokens: store,
        client: loginServer(),
      ).login(email: 'a@b.c', password: 'pw');

      final repo = ApiAuthRepository(
        tokens: store,
        client: loginServer(me: {..._me, 'nickname': '새이름'}),
      );
      expect((await repo.restoreSession())!.user.nickname, '백성검');

      // 새로 고치면 서버 값이 온다.
      expect((await repo.refreshMe()).nickname, '새이름');
      expect((await repo.restoreSession())!.user.nickname, '새이름');
    });

    /// 🔴 **로그아웃하면 사용자도 지운다** — 안 지우면 다음에 켤 때
    /// **로그아웃한 사람의 인사말**이 뜬다(토큰만 지우던 때의 함정).
    test('로그아웃하면 저장해 둔 사용자도 사라진다', () async {
      final store = InMemoryTokenStore();
      final repo = ApiAuthRepository(tokens: store, client: loginServer());
      await repo.login(email: 'a@b.c', password: 'pw');
      await repo.logout();

      final after = await ApiAuthRepository(
        tokens: store,
        client: MockClient((req) async => http.Response('', 401)),
      ).restoreSession();

      expect(after, isNull);
    });

    /// 🔴 **토큰이 없으면 저장해 둔 사용자도 안 쓴다.** 토큰만 지워진 상태에서
    /// 프로필로 로그인 상태를 만들면 **아무 요청도 못 하는 유령 세션**이 된다.
    test('토큰이 없으면 저장해 둔 사용자가 있어도 로그아웃이다', () async {
      final store = InMemoryTokenStore();
      final repo = ApiAuthRepository(tokens: store, client: loginServer());
      await repo.login(email: 'a@b.c', password: 'pw');
      await store.clear(); // 토큰만 날아간 상황

      final after = await ApiAuthRepository(
        tokens: store,
        client: MockClient((req) async => http.Response('', 401)),
      ).restoreSession();

      expect(after, isNull);
    });
  });
}
