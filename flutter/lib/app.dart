import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'core/widgets/design_canvas.dart';
import 'features/intro/presentation/intro_gate.dart';

/// 시스템 글꼴 배율의 상한 — 🔴 **1.2 는 타협이다.**
///
/// 막지 않는 것이 접근성에는 옳지만, 그러려면 화면마다 글자 크기를 따라
/// 늘어나게 고쳐야 한다. 이 앱은 `fontSize` 가 대부분 **고정 논리 픽셀**이라
/// (2026-09-29 기준 211곳 중 폭에 비례하는 것은 16곳뿐) 칸이 안 늘어나고
/// 버튼 글자가 넘친다.
///
/// ⛔ **화면을 손보기 전에 이 상한을 올리거나 걷지 말 것** — 사용자가
/// 실기기에서 잡은 「글자나 버튼 모든게 커지는」 깨짐이 그대로 돌아온다.
const double kMaxTextScale = 1.2;

/// 폰 설정의 글꼴 배율을 [kMaxTextScale] 까지로 자른다.
///
/// 🔴 **줄이지는 않는다**(아래 한계 1) — 작게 쓰는 사람에게 억지로 키우면
/// 그쪽 화면이 깨진다.
TextScaler clampTextScale(TextScaler system) =>
    system.clamp(minScaleFactor: 1, maxScaleFactor: kMaxTextScale);

class SuperSubApp extends ConsumerWidget {
  const SuperSubApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Super-Sub',
      // 디버그 빌드 오른쪽 위의 빨간 띠를 감춘다.
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      routerConfig: ref.watch(routerProvider),
      // 인트로는 라우트가 아니라 모든 라우트 위에 얹는 겹이다 —
      // 이유는 IntroGate의 주석 참고.
      builder: (context, child) {
        final content = child ?? const SizedBox();
        final inner =
            ref.watch(introEnabledProvider) ? IntroGate(child: content) : content;

        /* 🔴 **시스템 글꼴 배율에 상한을 둔다** (2026-09-29 사용자 지적:
           「좀 작은 휴대폰들은 글자나 버튼 모든게 커지거나」).

           폰 설정에서 글씨를 크게 해 둔 사람은 앱 글자가 **그 배율 그대로**
           커진다(2배로 두면 앱도 2배). 이 앱은 `fontSize` 가 대부분 **고정
           논리 픽셀**이라 칸이 그만큼 안 늘어나고, 버튼 글자가 넘치거나
           줄이 겹친다.

           🔴 **1.2 는 타협이다.** 막지 않는 것이 접근성에는 옳지만, 그러려면
           화면마다 글자 크기를 따라 늘어나게 고쳐야 한다. 그 전까지는 「읽을
           만하면서 안 깨지는」 선에서 자른다.
           ⚠️ 시력이 나쁜 사람이 3배로 키워도 앱은 1.2배까지만 커진다 —
           화면을 글자 크기에 맞춰 손보면 그때 이 상한을 올리거나 걷는다. */
        final mq = MediaQuery.of(context);
        return MediaQuery(
          data: mq.copyWith(textScaler: clampTextScale(mq.textScaler)),
          /* 🔴 **도면을 통째로 늘였다 줄인다** — 머리말은 [DesignCanvas] 다.
             ⛔ 화면마다 따로 줄이는 방식으로 되돌리지 말 것 — 요소마다 비율이
             갈려서 사용자가 물렸다(2026-09-29). */
          child: DesignCanvas(child: inner),
        );
      },
    );
  }
}
