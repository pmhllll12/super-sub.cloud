import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/intro/presentation/intro_gate.dart';

void main() {
  testWidgets('로그인하지 않았으면 로그인 화면으로 간다', (tester) async {
    // 인트로를 끈다 — 이 테스트가 보는 것은 라우터의 착지지 연출이 아니다.
    await tester.pumpWidget(ProviderScope(
      overrides: [
        introEnabledProvider.overrideWithValue(false),
        /* 🔴 **저장소를 갈아 끼운다**(2026-09-17). 진짜 저장소는
           Keystore·Keychain 이라 플랫폼 채널로 오가는데, 위젯 시험의 가짜
           시계에서는 그 응답이 **영영 안 온다** — 세션 복원이 안 끝나 라우터가
           첫 화면에 멈춘다. 비어 있는 저장소 = 「로그인한 적 없음」이라
           이 시험이 보려는 상황 그대로다. */
        tokenStoreProvider.overrideWithValue(InMemoryTokenStore()),
      ],
      child: const SuperSubApp(),
    ));
    /* 세션 복원이 이제 저장소를 한 번 들렀다 온다 — 그 비동기 한 칸 때문에
       프레임이 하나 더 필요하다(미결 `min` 25번). */
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('로그인'), findsWidgets);
  });
}
