import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/mock/mock_db.dart';
import '../../../../core/widgets/refractive_glass.dart';
import '../../../intro/presentation/brand_mark.dart';
import '../../../intro/presentation/screens/glitch_intro_screen.dart'
    show kIntroInkColor;
import '../session_controller.dart';

/// 시트 윗모서리 반지름. **클립과 셰이더가 같은 값을 봐야** 굴절이 모서리에서
/// 어긋나지 않는다.
const double _kSheetRadius = 28.0;

/// 사진 위에 얹히는 글자색.
const Color _kOnPhoto = Color(0xFFFFFFFF);

/// 사진과 유리 사이에 까는 어두운 막.
///
/// **사진이 밝다** — 흰 유니폼과 밝은 회색 배경이라, 그 위에 흰 글자를 얹으면
/// 읽히지 않는다. 유리 면(흰색)을 더 올리면 배경이 같이 밝아져 역효과다.
/// 대비를 세우는 유일한 방법은 뒤를 어둡게 하는 것이다.
///
/// 위는 옅고 아래로 갈수록 진하다 — 사진은 위쪽에서 살아 있고, 폼이 놓이는
/// 아래쪽만 충분히 어두워진다.
const LinearGradient _kPhotoScrim = LinearGradient(
  begin: Alignment.topCenter,
  end: Alignment.bottomCenter,
  colors: [Color(0x4D000000), Color(0xC2000000)],
  stops: [0, 0.55],
);

/// 버튼 테두리.
///
/// **면은 비운다** — 어두운 막을 깔면서 흰 면이 뿌옇게 떴다. 대신 뒤의
/// 굴절된 사진이 그대로 비치고, 아주 옅은 선이 형태만 세운다.
///
/// 버튼 자리에 진짜 유리(BackdropFilter)를 한 겹 더 넣을 수는 없다.
/// `refractive_glass.dart`가 "자식 안에 유리를 또 넣지 않는다 — 안쪽이 아직
/// 안 끝난 바깥을 읽어 내용이 프레임째로 사라진다"고 못박아 뒀고, 버튼은
/// 이미 유리 시트 안이다.
final Color _kButtonEdge = Colors.white.withValues(alpha: 0.22);

/// 버튼 모서리.
const double _kButtonRadius = 14;

/// 유리 세기. 시트가 고정이라 늘 최대다.
///
/// 끌어올리는 시트였을 때는 진행도를 그대로 넘겼다 — 올라오는 만큼만 유리가
/// 서야 접힌 상태에 뿌연 띠가 안 남았다. 고정이 되면서 그 이유가 사라졌다.
const Animation<double> _kGlassOn = AlwaysStoppedAnimation<double>(1);

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

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // **사진 뒤에 깔리는 색이다.** 밝은 색을 두면 사진이 풀리기 전 한
      // 프레임이 인트로의 잉크 구멍으로 비쳐 번쩍인다 — 잉크와 같은 색이면
      // 그 순간이 안 보인다.
      backgroundColor: kIntroInkColor,
      resizeToAvoidBottomInset: false,
      body: Stack(
        fit: StackFit.expand,
        children: [
          const Image(
            image: AssetImage('assets/images/player_mono.jpg'),
            fit: BoxFit.cover,
          ),
          const DecoratedBox(
            decoration: BoxDecoration(gradient: _kPhotoScrim),
            child: SizedBox.expand(),
          ),
          _sheetBody(),
        ],
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
          strength: _kGlassOn,
          child: _sheetColumn(),
        ),
      ),
    );
  }

  Widget _sheetColumn() {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 로고를 상단에서 넉넉히 내린다. 인트로 글자가 날아와 앉는 곳이라
          // 이 값이 곧 비행의 도착점이다 — GlobalKey로 실제 좌표를 읽으므로
          // 여기만 바꾸면 비행도 따라온다.
          const SizedBox(height: 96),
          // 인트로의 글자가 날아와 앉는 자리다 — 같은 위젯, 같은 글꼴.
          Center(
            child: BrandMark(
              key: kBrandLandingKey,
              fontSize: kBrandLandedSize,
            ),
          ),
          Expanded(child: _form()),
        ],
      ),
    );
  }

  Widget _form() {
    final notifier = sessionControllerProvider.notifier;
    // **Center가 스크롤 뷰를 감싼다.** 내용이 짧으면 남은 자리 한가운데에
    // 놓이고, 키보드가 올라와 자리가 모자라면 그때부터 스크롤된다.
    return Center(
      child: SingleChildScrollView(
        padding: EdgeInsets.only(
          top: 24,
          bottom: MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        // 입력란과 버튼이 **같은 폭**이다 — 여기서 한 번 정하고 아래는 전부
        // stretch로 따라간다. 좌우 여백을 패딩으로 주면 둘이 갈라진다.
        child: FractionallySizedBox(
          widthFactor: 2 / 3,
          child: Column(
            mainAxisSize: MainAxisSize.min,
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
                  textAlign: TextAlign.center,
                  style:
                      const TextStyle(color: Color(0xFFFF8A80), fontSize: 13),
                ),
              ],
              const SizedBox(height: 22),
              FilledButton(
                key: const Key('login-submit'),
                style: _glassButton,
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
                const SizedBox(height: 24),
                Text(
                  '개발용 바로 진입',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: _kOnPhoto.withValues(alpha: 0.85),
                    fontSize: 12,
                    letterSpacing: 0.4,
                  ),
                ),
                const SizedBox(height: 10),
                _DevLoginButton(
                  label: '개인 사용자 (데이터 있음)',
                  userId: MockDb.playerId,
                  busy: _busy,
                  style: _glassButton,
                  onTap: (id) => _run(() => ref.read(notifier).loginAs(id)),
                ),
                _DevLoginButton(
                  label: '팀 관리자',
                  userId: MockDb.managerId,
                  busy: _busy,
                  style: _glassButton,
                  onTap: (id) => _run(() => ref.read(notifier).loginAs(id)),
                ),
                _DevLoginButton(
                  label: '신규 가입자 (데이터 0건)',
                  userId: MockDb.newbieId,
                  busy: _busy,
                  style: _glassButton,
                  onTap: (id) => _run(() => ref.read(notifier).loginAs(id)),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  /// 모든 버튼이 같은 유리 면을 쓴다 — 테두리는 두르지 않는다. 형태를
  /// 세우는 건 테두리가 아니라 이 면이다.
  ButtonStyle get _glassButton => FilledButton.styleFrom(
        backgroundColor: Colors.transparent,
        foregroundColor: _kOnPhoto,
        disabledBackgroundColor: Colors.transparent,
        disabledForegroundColor: _kOnPhoto.withValues(alpha: 0.4),
        side: BorderSide(color: _kButtonEdge),
        elevation: 0,
        // 컴팩트하게 — 높이를 강제하지 않고 패딩으로만 잡는다.
        minimumSize: Size.zero,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(_kButtonRadius),
        ),
      );

  Widget _field({
    required Key key,
    required TextEditingController controller,
    required String label,
    bool obscure = false,
    TextInputType? keyboardType,
  }) {
    final line = _kOnPhoto.withValues(alpha: 0.55);
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
        labelStyle: TextStyle(color: _kOnPhoto.withValues(alpha: 0.85)),
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

class _DevLoginButton extends StatelessWidget {
  const _DevLoginButton({
    required this.label,
    required this.userId,
    required this.busy,
    required this.onTap,
    required this.style,
  });

  final String label;
  final String userId;
  final bool busy;
  final void Function(String userId) onTap;
  final ButtonStyle style;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: FilledButton(
        style: style,
        onPressed: busy ? null : () => onTap(userId),
        child: Text(label),
      ),
    );
  }
}
