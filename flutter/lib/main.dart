import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/widgets/glass_shader.dart';
import 'core/widgets/ink_bleed.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // **여기서 기다리지 않는다.** 예전에는 잉크 지도(1.35MB)를 다 읽고 runApp을
  // 불렀는데, 그동안 Flutter가 첫 프레임을 못 그려 안드로이드 창 배경이 2~3초
  // 그대로 보였다. 창 배경을 인트로 색에 맞춰 가리는 방법도 있지만, 그러면
  // Flutter UI 뒤(최근 앱 목록·화면 전환)까지 그 색이 된다.
  //
  // 대신 앱을 곧바로 띄우고, 인트로가 자기 애니메이션을 지도가 준비된 뒤에
  // 시작한다(`GlitchIntroScreen`). 첫 프레임부터 인트로의 판이 화면을 채우므로
  // 창 배경은 순간만 스친다.
  unawaited(InkBleedShader.load());
  unawaited(GlassShader.load());

  await _hideNavigationBar();
  /* 🔴 **다시 켜질 때마다 도로 감춘다.** 앨범·카메라를 다녀오거나 앱을
     잠깐 나갔다 오면 안드로이드가 바를 되돌려 놓는다 — 그때 다시 안 감추면
     **하단 바가 그대로 남는다**(사용자: 「왜 또 하단바 또 생기게 했어?」).
     리스너는 앱이 사는 동안 살아 있어야 하므로 일부러 안 치운다. */
  AppLifecycleListener(onResume: _hideNavigationBar);
  runApp(const ProviderScope(child: SuperSubApp()));
}

/// 기기의 **하단 내비게이션 바만** 감춘다. 🔴 **상태 바(시계·배터리)는
/// 남긴다**(2026-09-22, 사용자 요청).
///
/// 인트로의 잉크도, 로그인의 사진도 화면 끝까지 간다. 그 아래에 시스템 바가
/// 띠로 남아 있으면 화면이 잘려 보인다.
///
/// 🔴 **`immersiveSticky` 를 쓰지 않는다**(2026-09-22에 썼다가 되돌렸다).
/// 그쪽은 바가 나타날 때 레이아웃을 안 밀어서 좋지만 **상태 바까지 같이
/// 감춘다** — 둘을 따로 못 고른다. 시계를 남기는 쪽을 골랐다.
///
/// **감추기만 하면 한 번 올린 뒤 계속 떠 있다.** 사용자가 아래에서 쓸어
/// 올리면 안드로이드가 바를 되돌려 놓고 그대로 두기 때문이다. 그래서 그
/// 변화를 듣고 잠시 뒤 다시 감춘다.
Future<void> _hideNavigationBar() async {
  await SystemChrome.setEnabledSystemUIMode(
    SystemUiMode.manual,
    overlays: [SystemUiOverlay.top],
  );
  SystemChrome.setSystemUIChangeCallback((visible) async {
    if (!visible) return;
    await Future<void>.delayed(const Duration(seconds: 3));
    await SystemChrome.setEnabledSystemUIMode(
      SystemUiMode.manual,
      overlays: [SystemUiOverlay.top],
    );
  });
}
