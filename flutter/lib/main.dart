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

  await _hideSystemBars();
  runApp(const ProviderScope(child: SuperSubApp()));
}

/// 기기의 시스템 바를 감춘다 — 아래에서 쓸어 올리면 잠깐 나왔다 저절로 들어간다.
///
/// 인트로의 잉크도, 로그인의 사진도 화면 끝까지 간다. 그 아래에 시스템 바가
/// 띠로 남아 있으면 화면이 잘려 보인다.
///
/// 🔴 **`immersiveSticky` 다 — 손으로 되감추지 않는다** (2026-09-22, 사용자
/// 요청). 전에는 `manual` + `setSystemUIChangeCallback` + 3초 타이머로 같은
/// 것을 흉내 냈는데, `manual` 에서 바가 나타나면 **아래 여백(inset)이 생겨
/// 화면 레이아웃이 3초 동안 들썩였다.** `immersiveSticky` 는 바가 화면을
/// **덮어서** 나타나므로 레이아웃이 안 흔들리고, 되감추는 것도 OS 가 한다.
///
/// ⚠️ **상태 바(시계·배터리)도 같이 감춰진다** — `immersiveSticky` 는 둘을
/// 따로 못 고른다. 시계를 남겨야 하면 옛 `manual` 방식으로 돌아가야 하고,
/// 그러면 위 들썩임이 같이 돌아온다(사용자가 알고 고른 것이다).
Future<void> _hideSystemBars() async {
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
}
