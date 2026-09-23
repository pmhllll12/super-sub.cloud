import 'dart:async';

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

  /* 🔴 **시스템 바는 Dart 가 안 건드린다**(2026-09-22 정정).
     `SystemChrome.setEnabledSystemUIMode` 로는 「하단만 감추되, 쓸어 올리면
     **겹쳐서** 잠깐 나왔다 저절로 사라진다」가 안 나온다:

       · `manual` + `overlays: [top]` — 하단만 감추지만 바가 **자리를
         차지해서** 화면 아래가 밀린다(사용자가 실기기에서 잡았다)
       · `immersiveSticky` — 겹치고 저절로 사라지지만 **상태 바까지** 감춘다

     그래서 `MainActivity.kt` 가 안드로이드 쪽에서 직접 잡는다
     (`BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE`). 여기서 또 부르면 그것을
     덮어써서 도로 원래 문제로 돌아간다. */
  runApp(const ProviderScope(child: SuperSubApp()));
}
