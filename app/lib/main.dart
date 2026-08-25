import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/widgets/glass_shader.dart';
import 'core/widgets/ink_bleed.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // **앱이 뜨기 전에 잉크 지도와 셰이더를 실어 둔다.**
  //
  // 인트로는 첫 프레임부터 잉크를 그린다. 여기서 안 기다리면 로딩이 끝날
  // 때까지 InkBleedPainter가 물러섬 경로(밋밋한 색 페이드)로 떨어져, 잉크가
  // 번지는 게 안 보이고 화면이 그냥 색으로 덮인 것처럼 보인다.
  //
  // 실패해도 예외를 밖으로 내보내지 않는다 — 못 쓰면 그 물러섬 경로로 돈다.
  await InkBleedShader.load();
  // 굴절 유리. **잉크와 다른 경로다** — ImageFilter.shader는 Impeller
  // 전용이라, load() 자체가 isShaderFilterSupported를 먼저 본다. 못 쓰는
  // 기기에서는 조용히 비워 두고 쓰는 쪽이 흐림 유리로 물러선다.
  await GlassShader.load();
  await _hideNavigationBar();
  runApp(const ProviderScope(child: SuperSubApp()));
}

/// 기기의 하단 내비게이션 바를 감춘다. 상태 바(시계·배터리)는 남긴다.
///
/// 인트로의 잉크도, 로그인의 사진도 화면 끝까지 간다. 그 아래에 시스템 바가
/// 띠로 남아 있으면 화면이 잘려 보인다.
///
/// **감추기만 하면 한 번 올린 뒤 계속 떠 있다.** 사용자가 아래에서 쓸어
/// 올리면 안드로이드가 바를 되돌려 놓고 그대로 두기 때문이다. 그래서 그
/// 변화를 듣고 잠시 뒤 다시 감춘다 — 올린 사람은 쓸 수 있고, 손을 떼면
/// 화면이 원래대로 돌아온다.
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
