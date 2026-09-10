import 'auth_repository.dart';

/// **요청이 너무 잦아 거부된 것인가** — 429 `TOO_MANY_REQUESTS`(계약 SEC-009).
///
/// 🔴 **status 가 아니라 `code` 로 가른다.** 같은 429 라도 다른 제한이 생길 수
/// 있고, 계약이 클라이언트는 `code` 로 분기한다고 정했다. 웹의
/// `isRateLimited`(`www/src/lib/api/client.ts`)와 같은 성질이다.
bool isRateLimited(Object? err) =>
    err is AuthException && err.code == 'TOO_MANY_REQUESTS';

/// 429 거부에서 **몇 초 기다려야 하는가.** 429 가 아니면 `null`.
///
/// 🔴 **서버가 값을 안 줬으면 `0` 이 아니라 최소 1초를 준다** — 0 이면 잠금이
/// 곧바로 풀려 「429 직후 재요청이 안 나간다」는 성질이 깨진다.
int? retryAfterSeconds(Object? err) {
  if (!isRateLimited(err)) return null;
  final secs = (err as AuthException).retryAfter;
  return secs != null && secs > 0 ? secs : 1;
}
