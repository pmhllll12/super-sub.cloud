import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/rate_limit.dart';

/// **429 뒤에는 같은 요청이 다시 안 나간다** — 계약 SEC-009, 미결 `jin` 2번.
///
/// 웹(`www/src/lib/api/rateLimit.ts`)의 `useRateLimitLock()`과 같은 자리다 —
/// 인증 화면(로그인 · 가입 · 구글 로그인)이 이 하나를 나눠 쓴다. 각자 세면
/// 한 곳만 고쳐지고, 그게 이 컨트롤러가 막으려는 것이다. 지금은 로그인
/// 화면뿐이지만, 가입 · 구글 로그인이 생기면 같은 provider 를 이어 쓴다.
///
/// 🔴 **기다릴 시간은 서버가 준 `Retry-After` 를 쓴다.** 임의의 상수를 두면
/// 필요 이상으로 기다리게 된다.
class RateLimitController extends Notifier<int> {
  Timer? _ticker;

  @override
  int build() {
    ref.onDispose(() => _ticker?.cancel());
    return 0;
  }

  /// 이 오류가 429 면 잠그고 `true` 를 돌려준다. 아니면 아무 일도 없이 `false`.
  /// 부르는 쪽은 그 결과로 **제 에러 문구를 낼지** 정한다.
  bool lockFrom(Object? err) {
    final secs = retryAfterSeconds(err);
    if (secs == null) return false;
    state = secs;
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      state = state <= 1 ? 0 : state - 1;
      if (state == 0) _ticker?.cancel();
    });
    return true;
  }
}

final rateLimitControllerProvider =
    NotifierProvider<RateLimitController, int>(RateLimitController.new);

/// 남은 초가 있으면 화면에 보여 줄 한 줄. 안 잠겼으면 `null`.
String? rateLimitNote(int secondsLeft) =>
    secondsLeft > 0 ? '요청이 너무 잦습니다. $secondsLeft초 뒤에 다시 시도해 주세요.' : null;
