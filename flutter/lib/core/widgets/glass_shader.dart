import 'dart:ui' as ui;

/// 유리 셰이더를 한 번만 로드해 들고 있는다.
///
/// `ImageFilter.shader`는 Impeller에서만 동작한다. 아니면 UnsupportedError를
/// 던지므로, 쓰는 쪽은 반드시 [isSupported]를 먼저 본다.
class GlassShader {
  GlassShader._();

  static ui.FragmentProgram? _program;

  /// Impeller가 아니거나 아직 로드 전이면 거짓이다.
  static bool get isSupported =>
      ui.ImageFilter.isShaderFilterSupported && _program != null;

  static ui.FragmentProgram? get program => _program;

  /// 앱 시작 때 한 번 부른다. 실패해도 예외를 밖으로 내보내지 않는다 —
  /// 셰이더가 없으면 부르는 쪽이 기존 흐림 유리로 물러선다.
  static Future<void> load() async {
    if (_program != null) return;
    if (!ui.ImageFilter.isShaderFilterSupported) return;
    try {
      _program = await ui.FragmentProgram.fromAsset('shaders/liquid_glass.frag');
    } catch (_) {
      _program = null;
    }
  }
}
