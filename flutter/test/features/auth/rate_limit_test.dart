import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/data/rate_limit.dart';
import 'package:super_sub/features/auth/presentation/rate_limit_controller.dart';

void main() {
  group('isRateLimited · retryAfterSeconds', () {
    test('code가 TOO_MANY_REQUESTS가 아니면 false·null', () {
      const err = AuthException('아무 실패', code: 'INVALID_CREDENTIALS');
      expect(isRateLimited(err), isFalse);
      expect(retryAfterSeconds(err), isNull);
    });

    test('AuthException이 아니면 false·null', () {
      expect(isRateLimited(Exception('x')), isFalse);
      expect(retryAfterSeconds(Exception('x')), isNull);
    });

    test('retryAfter가 있으면 그 값을 쓴다', () {
      const err = AuthException(
        '너무 잦음',
        code: 'TOO_MANY_REQUESTS',
        retryAfter: 7,
      );
      expect(isRateLimited(err), isTrue);
      expect(retryAfterSeconds(err), 7);
    });

    test('retryAfter가 없거나 0 이하면 최소 1초', () {
      const noHeader = AuthException('너무 잦음', code: 'TOO_MANY_REQUESTS');
      const zero = AuthException(
        '너무 잦음',
        code: 'TOO_MANY_REQUESTS',
        retryAfter: 0,
      );
      expect(retryAfterSeconds(noHeader), 1);
      expect(retryAfterSeconds(zero), 1);
    });
  });

  group('RateLimitController', () {
    test('429가 아니면 잠그지 않는다', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final locked = container
          .read(rateLimitControllerProvider.notifier)
          .lockFrom(const AuthException('아무 실패'));

      expect(locked, isFalse);
      expect(container.read(rateLimitControllerProvider), 0);
    });

    testWidgets('429면 잠그고, 매초 줄어들다가 0에서 멎는다', (tester) async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final locked = container.read(rateLimitControllerProvider.notifier).lockFrom(
            const AuthException(
              '너무 잦음',
              code: 'TOO_MANY_REQUESTS',
              retryAfter: 2,
            ),
          );

      expect(locked, isTrue);
      expect(container.read(rateLimitControllerProvider), 2);

      await tester.pump(const Duration(seconds: 1));
      expect(container.read(rateLimitControllerProvider), 1);

      await tester.pump(const Duration(seconds: 1));
      expect(container.read(rateLimitControllerProvider), 0);

      // 0에서 더 지나도 음수로 내려가지 않는다.
      await tester.pump(const Duration(seconds: 1));
      expect(container.read(rateLimitControllerProvider), 0);
    });
  });

  group('rateLimitNote', () {
    test('0이면 null, 양수면 안내 문구', () {
      expect(rateLimitNote(0), isNull);
      expect(rateLimitNote(3), '요청이 너무 잦습니다. 3초 뒤에 다시 시도해 주세요.');
    });
  });
}
