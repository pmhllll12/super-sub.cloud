/// 포스터가 **한 번 실패했다고 영영 검은 칸으로 남지 않는다**
/// (2026-09-25 사용자 지적: 「아직도 썸네일 안나오는것들 있어」).
///
/// 🔴 **원인은 서버가 아니라 앱이었다.** `videoPosterProvider` 가 재시도를 꺼
/// 두어서(`retry: (_, _) => null`), 서버가 느려 한 번 끊긴 영상은 **앱을 끌
/// 때까지** 다시 안 받았다. 화면은 `.value` 로 읽는데 그 값은 **오류일 때도
/// `null`** 이라(1.23 때 카드가 비어 보이던 것과 같은 함정) 로딩과 구별도
/// 안 되고 그냥 검게 남았다.
///
/// 🔴 **404 는 재시도하지 않는다** — 리포지토리가 그것을 `null` **값**으로
/// 바꾸므로 애초에 오류로 오지 않는다. 여기 오는 오류는 끊김·5xx 뿐이다.
library;

import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/video/data/video_providers.dart';
import 'package:super_sub/features/video/data/video_repository.dart';

void main() {
  /// 🔴 **끊김은 다시 받는다.** 서버가 캐시에 없는 장면을 뜰 때 50~60초가
  /// 걸리고(2026-09-25 실측), 그동안 끊기면 그 영상은 앱을 끌 때까지 검었다.
  test('끊기면 세 번까지 다시 받는다', () {
    final e = ApiException('서버에 연결할 수 없습니다: 끊김');

    expect(posterRetry(0, e), isNotNull);
    expect(posterRetry(1, e), isNotNull);
    expect(posterRetry(2, e), isNotNull);
    // 🔴 끝없이 매달리지 않는다 — 느린 서버를 더 때리고 배터리를 먹는다.
    expect(posterRetry(3, e), isNull);
  });

  test('다시 받을수록 뜸하게 묻는다', () {
    final e = ApiException('끊김');
    expect(posterRetry(1, e)!, greaterThan(posterRetry(0, e)!));
    expect(posterRetry(2, e)!, greaterThan(posterRetry(1, e)!));
  });

  /// 🔴 **포스터가 없는 영상은 오류가 아니라 `null` 값이다** — 리포지토리가
  /// 404 를 값으로 바꾸므로 재시도 자체가 안 걸린다(형식·길이 때문에 못 뜨는
  /// 영상을 되풀이해 묻지 않는다). 그 성질을 provider 로 확인한다.
  test('포스터가 없는 영상은 한 번만 묻는다', () async {
    final repo = _FlakyPoster(failures: 0, empty: true);
    final c = ProviderContainer(
      overrides: [videoRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(c.dispose);

    expect(await c.read(videoPosterProvider('v-1').future), isNull);
    expect(repo.calls, 1);
  });
}

/// 앞의 [failures] 번은 끊기고 그 뒤로는 그림을 주는 대역.
class _FlakyPoster implements VideoRepository {
  _FlakyPoster({required this.failures, this.empty = false});

  final int failures;
  final bool empty;
  int calls = 0;

  @override
  Future<Uint8List?> poster(String videoId) async {
    calls += 1;
    if (calls <= failures) {
      throw ApiException('서버에 연결할 수 없습니다: 끊김');
    }
    return empty ? null : Uint8List.fromList(const [1, 2, 3]);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('이 시험이 안 쓰는 자리: ${invocation.memberName}');
}
