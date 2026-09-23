import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/card/data/card_providers.dart';
import 'package:super_sub/features/team/data/squad_providers.dart';
import 'package:super_sub/features/video/data/video_providers.dart';

/// 🔴 **바이트로 준다** — `http.Response(문자열, …)` 은 charset 이 없으면
/// latin1 로 인코딩해서 한글 본문이 만들 때부터 터진다
/// (`auth_repository_api_test.dart` 머리말과 같은 이유).
http.Response jsonRes(Map<String, dynamic> body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

const _me = {
  'id': 'u1',
  'email': 'demo@supersub.test',
  'nickname': '데모',
  'created_at': '2026-09-01T00:00:00Z',
};

const _card = {'id': 'c1', 'public_slug': 'demo-slug'};

/// **로그인이 저장한 토큰을 카드·영상·스쿼드 요청도 쓴다.**
///
/// 🔴 이것이 깨지면 증상이 **「카드가 없다」로 보인다** — 화면이
/// `ref.watch(myCardProvider).value` 로 읽어서 401 과 「아직 안 만듦」이
/// 똑같이 `null` 이 되기 때문이다. 2026-09-23 에 실서버에서 그렇게 드러났다:
/// `/me` 만 토큰이 실리고 `/me/card`·`/videos`·`/teams/{id}/squad` 는 전부
/// 토큰 없이 나가 401 이었다.
///
/// 원인은 `authRepositoryProvider` 가 공유 [apiClientProvider] 를 안 넘겨서
/// `ApiAuthRepository` 가 **자기만의 [ApiClient]** 를 만든 것이었다.
/// `api_client.dart` 의 `apiClientProvider` 주석이 바로 그 위험을 적어 두고도
/// 배선이 그걸 안 따랐다.
void main() {
  /// 어떤 경로에 어떤 `Authorization` 이 실려 왔는지 받아 적는 가짜 서버.
  (http.Client, Map<String, String?>) serverRecording() {
    final seen = <String, String?>{};
    final client = MockClient((req) async {
      seen[req.url.path] = req.headers['Authorization'];
      final path = req.url.path;
      if (path.endsWith('/auth/login')) {
        return jsonRes({'access_token': 'tok-1'}, 200);
      }
      if (path.endsWith('/me')) return jsonRes(_me, 200);
      if (path.endsWith('/me/card')) return jsonRes(_card, 200);
      if (path.endsWith('/videos')) {
        return http.Response.bytes(
          utf8.encode(jsonEncode(const <dynamic>[])),
          200,
        );
      }
      return jsonRes({}, 404);
    });
    return (client, seen);
  }

  ProviderContainer containerWith(http.Client client) {
    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(
          ApiClient(tokens: InMemoryTokenStore(), client: client),
        ),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  test('로그인 뒤 카드 요청에 토큰이 실린다', () async {
    final (client, seen) = serverRecording();
    final container = containerWith(client);

    await container
        .read(authRepositoryProvider)
        .login(email: 'demo@supersub.test', password: 'pw');
    await container.read(cardRepositoryProvider).myCard();

    expect(
      seen.entries.firstWhere((e) => e.key.endsWith('/me/card')).value,
      'Bearer tok-1',
      reason: '카드 요청이 토큰 없이 나가면 서버가 401 을 주고, 화면은 그것을 '
          '「카드가 없다」로 그린다',
    );
  });

  test('로그인 뒤 영상 요청에 토큰이 실린다', () async {
    final (client, seen) = serverRecording();
    final container = containerWith(client);

    await container
        .read(authRepositoryProvider)
        .login(email: 'demo@supersub.test', password: 'pw');
    await container.read(videoRepositoryProvider).myVideos();

    expect(
      seen.entries.firstWhere((e) => e.key.endsWith('/videos')).value,
      'Bearer tok-1',
    );
  });

  /// 🔴 **앱을 켠 직후의 경주.** 토큰은 저장소(Keystore)에 있고 메모리엔 아직
  /// 없다 — 전에는 세션 복원(`restoreSession`)이 `loadToken()` 을 부를 때만
  /// 올라와서, **그보다 먼저 나간 요청이 맨몸으로 나갔다.** 2026-09-23 실기기
  /// 로그가 정확히 그 모습이었다:
  ///
  ///     🔎API→ /me/card (tok=없음)   ← 홈이 켜지며 본다
  ///     🔎API→ /me      (tok=있음)   ← 세션 복원이 그 뒤에 온다
  ///     🔎API✗ 401
  ///
  /// `myCardProvider` 는 `retry` 를 꺼 둬서 이 401 이 **영구히 남는다** —
  /// 화면은 그것을 「카드가 없다」로 그리고 「카드 만들기」를 내민다.
  test('앱을 켜자마자 나간 요청도 저장소의 토큰을 싣는다', () async {
    final seen = <String, String?>{};
    final client = MockClient((req) async {
      seen[req.url.path] = req.headers['Authorization'];
      return jsonRes(_card, 200);
    });
    // 저장소에는 있고 메모리에는 없는 상태 — 앱을 막 켠 순간이다.
    final store = InMemoryTokenStore();
    await store.write('tok-저장됨');
    final api = ApiClient(tokens: store, client: client);

    // 🔴 `loadToken()` 을 **일부러 안 부른다** — 그것이 이 결함의 조건이다.
    await api.get('/me/card');

    expect(
      seen.entries.firstWhere((e) => e.key.endsWith('/me/card')).value,
      'Bearer tok-저장됨',
      reason: '세션 복원보다 먼저 나간 요청이 401 을 받으면, 화면은 그것을 '
          '「카드가 없다」로 그린다',
    );
  });

  test('인증 리포지토리와 카드 리포지토리가 같은 ApiClient 를 쓴다', () async {
    final (client, seen) = serverRecording();
    final container = containerWith(client);

    // 로그인은 인증 쪽에서, 읽기는 카드·스쿼드 쪽에서 — 토큰이 건너가야 한다.
    await container
        .read(authRepositoryProvider)
        .login(email: 'demo@supersub.test', password: 'pw');

    // 공유본에 토큰이 올라왔으면 이후 어떤 리포지토리든 실어 보낸다.
    expect(container.read(cardRepositoryProvider), isNotNull);
    expect(container.read(squadRepositoryProvider), isNotNull);
    expect(seen.keys.any((k) => k.endsWith('/auth/login')), isTrue);
  });
}
