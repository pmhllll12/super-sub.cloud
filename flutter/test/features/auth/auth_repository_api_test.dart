import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/data/auth_repository_api.dart';
import 'package:super_sub/features/auth/data/token_store.dart';

/// 🔴 **`http.Response(문자열, …)` 을 쓰지 않는다.** 헤더에 `charset` 이 없으면
/// `http` 가 **latin1 로** 인코딩해서, 한글이 든 본문은 만들 때부터
/// `Invalid argument (string): Contains invalid characters` 로 터진다
/// (2026-09-17에 걸렸다). 진짜 FastAPI 도 `application/json` 만 주고 charset 을
/// 안 붙이므로 **바이트로 주고받는 쪽이 실제와 같다** — 같은 이유로 구현체도
/// `response.body` 가 아니라 `bodyBytes` 를 UTF-8 로 푼다.
http.Response jsonRes(Map<String, dynamic> body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

const _me = {
  'id': 'u1',
  'email': 'demo@supersub.test',
  'nickname': '데모',
  'created_at': '2026-09-01T00:00:00Z',
};

/// **앱을 껐다 켜도 로그인이 유지된다** (미결 `min` 25번, 2026-09-17).
///
/// 🔴 **계약 시험(`test/contract/`)에 두지 않는다.** 저장은 이 구현체의
/// 의무다 — Mock 은 백엔드 없이 도는 것이라 **일부러 메모리에만** 둔다.
/// 계약에 섞으면 Mock 이 통과할 수 없는 조건이 된다(폴더 `CLAUDE.md` 의
/// 「프로토콜의 성질만 둔다」).
///
/// 🔴 **진짜 저장소는 여기서 못 쓴다** — Keystore·Keychain 은 플러그인 채널이
/// 필요해 단위 시험에서 안 돈다. [InMemoryTokenStore] 를 물려 **「새
/// 인스턴스에서도 돌아온다」**는 성질만 본다. 그 성질이 항목이 요구한 전부다
/// (「로그인 → 앱 강제 종료 → 재실행 → 홈으로 바로」).
void main() {
  /// 앱을 새로 켠 셈 — 저장소는 그대로 두고 리포지토리만 새로 만든다.
  ApiAuthRepository relaunch(TokenStore store, http.Client client) =>
      ApiAuthRepository(tokens: store, client: client);

  /// 로그인·`/me` 에 답하는 가짜 서버. 토큰이 [accepts] 와 다르면 401 이다.
  http.Client serverWith({String token = 'tok-1', String? accepts}) {
    final good = accepts ?? token;
    return MockClient((req) async {
      if (req.url.path.endsWith('/auth/login')) {
        return jsonRes({'access_token': token}, 200);
      }
      if (req.url.path.endsWith('/me')) {
        if (req.headers['Authorization'] != 'Bearer $good') {
          return jsonRes({
            'error': {'code': 'UNAUTHORIZED', 'message': '토큰이 유효하지 않습니다'},
          }, 401);
        }
        return jsonRes(_me, 200);
      }
      return jsonRes({}, 404);
    });
  }

  test('로그인하면 앱을 다시 켜도 세션이 돌아온다', () async {
    final store = InMemoryTokenStore();
    final client = serverWith();
    await relaunch(
      store,
      client,
    ).login(email: 'demo@supersub.test', password: 'pw');

    // 🔴 여기가 이 항목의 전부다 — 새 인스턴스(=앱 재실행)에서도 들어와야 한다.
    final session = await relaunch(store, client).restoreSession();
    expect(session, isNotNull);
    expect(session!.user.email, equals('demo@supersub.test'));
  });

  test('로그아웃하면 다시 켜도 안 돌아온다', () async {
    final store = InMemoryTokenStore();
    final client = serverWith();
    final repo = relaunch(store, client);
    await repo.login(email: 'demo@supersub.test', password: 'pw');
    await repo.logout();

    expect(await relaunch(store, client).restoreSession(), isNull);
    // 🔴 저장소까지 비어야 한다 — 남아 있으면 다음에 켤 때 되살아난다.
    expect(await store.read(), isNull);
  });

  test('로그인한 적이 없으면 복원할 것이 없다', () async {
    expect(
      await relaunch(InMemoryTokenStore(), serverWith()).restoreSession(),
      isNull,
    );
  });

  /// 🔴 못 쓰는 토큰(만료·폐기)은 그 자리에서 버린다 — 안 버리면 켤 때마다
  /// 같은 실패를 되풀이하고, 화면은 「로그인 안 됨」인데 저장소만 찬 어긋난
  /// 상태가 남는다.
  test('저장된 토큰이 더는 안 통하면 비우고 로그인 화면으로 보낸다', () async {
    final store = InMemoryTokenStore();
    await store.write('낡은-토큰');

    final session = await relaunch(
      store,
      serverWith(accepts: '새-토큰'),
    ).restoreSession();

    expect(session, isNull);
    expect(await store.read(), isNull);
  });

  /// 복원한 세션으로 이어지는 요청에도 저장해 둔 토큰이 실려야 한다 —
  /// 안 실리면 홈까지는 들어가고 그다음부터 전부 401 이 된다.
  test('복원한 뒤의 요청에도 저장된 토큰이 실린다', () async {
    final store = InMemoryTokenStore();
    await store.write('tok-저장됨');
    final seen = <String?>[];
    final client = MockClient((req) async {
      seen.add(req.headers['Authorization']);
      return jsonRes(_me, 200);
    });

    await relaunch(store, client).restoreSession();
    expect(seen, contains('Bearer tok-저장됨'));
  });

  test('토큰이 없으면 서버를 아예 안 부른다', () async {
    var calls = 0;
    final client = MockClient((req) async {
      calls++;
      return jsonRes({}, 200);
    });
    await relaunch(InMemoryTokenStore(), client).restoreSession();
    expect(calls, isZero);
  });

  /// 🔴 한글 문구가 **안 깨져서** 온다 — 서버가 charset 을 안 붙여도
  /// 바이트를 UTF-8 로 푼다(`_decode`). 이걸 놓치면 오류 문구와 닉네임이
  /// 뭉개진 글자로 보인다.
  test('서버가 준 한글 문구가 안 깨진다', () async {
    final client = MockClient(
      (req) async => jsonRes({
        'error': {
          'code': 'INVALID_CREDENTIALS',
          'message': '이메일 또는 비밀번호가 올바르지 않습니다',
        },
      }, 401),
    );
    await expectLater(
      relaunch(
        InMemoryTokenStore(),
        client,
      ).login(email: 'demo@supersub.test', password: '틀림'),
      throwsA(
        isA<AuthException>().having(
          (e) => e.message,
          'message',
          '이메일 또는 비밀번호가 올바르지 않습니다',
        ),
      ),
    );
  });
}
