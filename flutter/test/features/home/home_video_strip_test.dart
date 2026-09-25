import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/home/presentation/widgets/home_video_strip.dart';
import 'package:super_sub/features/video/data/models/public_video.dart';
import 'package:super_sub/features/video/data/video_providers.dart';

/// 🔴 **실패를 감추지 않는다** (2026-09-25, 사용자: 「아니 대체 왜 영상
/// 홈페이지에서 안보이냐고」).
///
/// 그날 실측: `/videos/public` 이 **30초를 넘겨도 답이 없었고**(`/regions` 는
/// 0.5초에 답했다), 화면은 그냥 **빈 자리**만 그렸다. `.value` 는 오류일 때도
/// `null` 이라 「아직 오는 중」과 「못 받았다」가 같아 보인 것이다.
///
/// ⚠️ **원인은 서버였다.** 그래도 앱이 「안 나온다」를 말없이 삼키면 어느 쪽
/// 문제인지 아무도 모른다 — 그래서 **말하고, 다시 시킬 길을 준다.**
Future<void> _pump(
  WidgetTester tester,
  Future<List<PublicVideo>> Function() load,
) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [publicVideosProvider.overrideWith((_) => load())],
      child: const MaterialApp(
        home: Scaffold(
          backgroundColor: Colors.black,
          body: HomeVideoStrip(height: 200),
        ),
      ),
    ),
  );
  await tester.pump();
}

void main() {
  testWidgets('못 받으면 그 사실을 말하고 다시 시킬 수 있다', (tester) async {
    await _pump(
      tester,
      () async => throw const ApiException('서버 응답이 너무 늦습니다'),
    );
    // 오류가 provider 를 타고 오도록 한 프레임 더 흘린다.
    await tester.pump();

    expect(find.byKey(const Key('home-videos-failed')), findsOneWidget);
  });

  /// 🔴 **한 편도 없는 것은 오류가 아니다** — 그때는 조용히 자리만 지킨다.
  testWidgets('비어 있으면 아무 말도 안 한다', (tester) async {
    await _pump(tester, () async => const <PublicVideo>[]);
    await tester.pump();

    expect(find.byKey(const Key('home-videos-failed')), findsNothing);
  });
}
