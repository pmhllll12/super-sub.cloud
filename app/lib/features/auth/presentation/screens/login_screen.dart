import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/mock/mock_db.dart';
import '../../../../core/widgets/refractive_glass.dart';
import '../../../../core/widgets/sheet_drag_physics.dart';
import '../../../intro/presentation/screens/glitch_intro_screen.dart'
    show kIntroInkColor;
import '../session_controller.dart';

/// 접힘 상태에서 보이는 시트 높이 — 손잡이와 힌트, 이름이 들어간다.
const double _kSheetCollapsed = 96.0;

/// 시트 윗모서리 반지름. **클립과 셰이더가 같은 값을 봐야** 굴절이 모서리에서
/// 어긋나지 않는다.
const double _kSheetRadius = 28.0;

/// 사진 위에 얹히는 글자색.
const Color _kOnPhoto = Color(0xFFFFFFFF);

const String _kHintUp = '위로 올려 로그인';
const String _kHintDown = '아래로 내려 닫기';

/// 사진 한 장 위로 유리 시트가 올라오는 로그인 화면.
///
/// 유리는 `com.sumworship`에서 가져왔다. **잉크와 반대 경로다** —
/// `ImageFilter.shader`는 Impeller 전용이라 `GlassShader.isSupported`(그 안에
/// `ImageFilter.isShaderFilterSupported`)로 반드시 막아야 하고, 좌표계도
/// 화면의 **물리 픽셀**이다. 그 환산은 `refractive_glass.dart`의 렌더 객체가
/// 혼자 한다 — 여기서는 논리 픽셀만 넘긴다.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _email = TextEditingController();
  final _password = TextEditingController();

  /// 시트 진행도 0(접힘)~1(펼침). **유리의 세기가 곧 이 값이다** — 늘 켜 두면
  /// 접힌 상태에서도 화면 아래에 뿌연 띠가 남는다.
  late final AnimationController _sheet = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 340),
  );

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _sheet.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _onDragUpdate(DragUpdateDetails d, SheetDragPhysics physics) {
    _sheet.value = physics.advance(_sheet.value, d.delta.dy);
  }

  void _onDragEnd(DragEndDetails d, SheetDragPhysics physics) {
    final expand = physics.shouldExpand(
      _sheet.value,
      d.velocity.pixelsPerSecond.dy,
    );
    _sheet.animateTo(expand ? 1.0 : 0.0, curve: Curves.easeOutCubic);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // **사진 뒤에 깔리는 색이다.** 밝은 색을 두면 사진이 풀리기 전 한
      // 프레임이 인트로의 잉크 구멍으로 비쳐 번쩍인다 — 잉크와 같은 색이면
      // 그 순간이 안 보인다.
      backgroundColor: kIntroInkColor,
      resizeToAvoidBottomInset: false,
      body: LayoutBuilder(
        builder: (context, constraints) {
          final expanded = constraints.biggest.height;
          final physics = SheetDragPhysics(
            travel: expanded - _kSheetCollapsed,
          );
          return GestureDetector(
            behavior: HitTestBehavior.opaque,
            onVerticalDragUpdate: (d) => _onDragUpdate(d, physics),
            onVerticalDragEnd: (d) => _onDragEnd(d, physics),
            child: Stack(
              fit: StackFit.expand,
              children: [
                const Positioned.fill(
                  child: Image(
                    image: AssetImage('assets/images/player_mono.jpg'),
                    fit: BoxFit.cover,
                  ),
                ),
                _sheetLayer(expanded, physics.travel),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _sheetLayer(double expanded, double travel) {
    return AnimatedBuilder(
      animation: _sheet,
      // **시트 몸통을 `child`로 빼면 안 된다.** 그러면 한 번만 지어 두고 자리만
      // 옮기는데, 굴절 유리는 자기 화면 자리를 **페인트할 때** 읽는다. 다시
      // 칠해지지 않으면 옛 자리를 문 채 그려져 올릴 때마다 깜빡인다.
      builder: (context, _) => Positioned(
        left: 0,
        right: 0,
        bottom: -travel * (1 - _sheet.value),
        height: expanded,
        child: _sheetBody(),
      ),
    );
  }

  Widget _sheetBody() {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(
        top: Radius.circular(_kSheetRadius),
      ),
      child: LayoutBuilder(
        builder: (context, box) => RefractiveGlass(
          notch: GlassNotch(
            left: 0,
            right: box.maxWidth,
            depth: box.maxHeight,
            radius: _kSheetRadius,
            pill: true,
          ),
          strength: _sheet,
          child: _sheetColumn(),
        ),
      ),
    );
  }

  Widget _sheetColumn() {
    final p = _sheet.value;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 14),
        Center(
          child: Container(
            width: 44,
            height: 4,
            decoration: BoxDecoration(
              color: _kOnPhoto.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
        const SizedBox(height: 10),
        // 글자 둘을 **같은 자리에 겹쳐** 교차시킨다. 따로 두면 글자가 바뀔 때
        // 아래 이름이 위아래로 튄다.
        SizedBox(
          height: 18,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Opacity(opacity: 1 - p, child: const _Hint(_kHintUp)),
              Opacity(opacity: p, child: const _Hint(_kHintDown)),
            ],
          ),
        ),
        const SizedBox(height: 8),
        const Center(
          child: Text(
            'SUPERSUB',
            style: TextStyle(
              fontFamily: 'Rubik',
              fontVariations: [FontVariation('wght', 900)],
              fontSize: 30,
              height: 1,
              letterSpacing: 1.4,
              color: _kOnPhoto,
            ),
          ),
        ),
        // 접혀 있을 때는 폼이 안 보여야 한다. 시트가 절반쯤 올라온 뒤부터
        // 떠오르게 한다.
        Expanded(
          child: Opacity(
            opacity: ((p - 0.35) / 0.65).clamp(0.0, 1.0),
            child: _form(),
          ),
        ),
      ],
    );
  }

  Widget _form() {
    final notifier = sessionControllerProvider.notifier;
    return SingleChildScrollView(
      padding: EdgeInsets.only(
        left: 28,
        right: 28,
        top: 28,
        bottom: MediaQuery.of(context).viewInsets.bottom + 28,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _field(
            key: const Key('login-email'),
            controller: _email,
            label: '이메일',
            keyboardType: TextInputType.emailAddress,
          ),
          const SizedBox(height: 14),
          _field(
            key: const Key('login-password'),
            controller: _password,
            label: '비밀번호',
            obscure: true,
          ),
          if (_error != null) ...[
            const SizedBox(height: 14),
            Text(
              _error!,
              style: const TextStyle(color: Color(0xFFFF8A80), fontSize: 13),
            ),
          ],
          const SizedBox(height: 22),
          FilledButton(
            key: const Key('login-submit'),
            style: FilledButton.styleFrom(
              // 브랜드색을 그대로 주 버튼에 쓴다. 민트가 밝아 글자는 어둡게.
              backgroundColor: kIntroInkColor,
              foregroundColor: const Color(0xFF0E2A14),
              minimumSize: const Size.fromHeight(52),
            ),
            onPressed: _busy
                ? null
                : () => _run(
                      () => ref
                          .read(notifier)
                          .login(_email.text, _password.text),
                    ),
            child: _busy
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('로그인'),
          ),
          if (kDebugMode) ...[
            const SizedBox(height: 28),
            Divider(color: _kOnPhoto.withValues(alpha: 0.2)),
            const SizedBox(height: 10),
            Text(
              '개발용 바로 진입',
              style: TextStyle(
                color: _kOnPhoto.withValues(alpha: 0.7),
                fontSize: 12,
                letterSpacing: 0.4,
              ),
            ),
            const SizedBox(height: 10),
            _DevLoginButton(
              label: '개인 사용자 (데이터 있음)',
              userId: MockDb.playerId,
              busy: _busy,
              onTap: (id) => _run(() => ref.read(notifier).loginAs(id)),
            ),
            _DevLoginButton(
              label: '팀 관리자',
              userId: MockDb.managerId,
              busy: _busy,
              onTap: (id) => _run(() => ref.read(notifier).loginAs(id)),
            ),
            _DevLoginButton(
              label: '신규 가입자 (데이터 0건)',
              userId: MockDb.newbieId,
              busy: _busy,
              onTap: (id) => _run(() => ref.read(notifier).loginAs(id)),
            ),
          ],
        ],
      ),
    );
  }

  Widget _field({
    required Key key,
    required TextEditingController controller,
    required String label,
    bool obscure = false,
    TextInputType? keyboardType,
  }) {
    final line = _kOnPhoto.withValues(alpha: 0.35);
    return TextField(
      key: key,
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboardType,
      enabled: !_busy,
      style: const TextStyle(color: _kOnPhoto),
      cursorColor: _kOnPhoto,
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: _kOnPhoto.withValues(alpha: 0.7)),
        enabledBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: line),
        ),
        focusedBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: _kOnPhoto),
        ),
      ),
    );
  }
}

class _Hint extends StatelessWidget {
  const _Hint(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Text(
        text,
        textAlign: TextAlign.center,
        style: TextStyle(
          color: _kOnPhoto.withValues(alpha: 0.75),
          fontSize: 13,
          letterSpacing: 0.3,
        ),
      );
}

class _DevLoginButton extends StatelessWidget {
  const _DevLoginButton({
    required this.label,
    required this.userId,
    required this.busy,
    required this.onTap,
  });

  final String label;
  final String userId;
  final bool busy;
  final void Function(String userId) onTap;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        foregroundColor: _kOnPhoto,
        side: BorderSide(color: _kOnPhoto.withValues(alpha: 0.3)),
      ),
      onPressed: busy ? null : () => onTap(userId),
      child: Text(label),
    );
  }
}
