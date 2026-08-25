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
  runApp(const ProviderScope(child: SuperSubApp()));
}
