import 'dart:ui' show ImageFilter;

import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/dev/data_source.dart';
import '../../../../core/mock/mock_db.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/refractive_glass.dart';
import '../../../intro/presentation/brand_mark.dart';
import '../../../intro/presentation/screens/glitch_intro_screen.dart'
    show kIntroInkColor;
import '../rate_limit_controller.dart';
import '../session_controller.dart';

/// 시트 윗모서리 반지름. **클립과 셰이더가 같은 값을 봐야** 굴절이 모서리에서
/// 어긋나지 않는다.
const double _kSheetRadius = 28.0;

/// 사진 위에 얹히는 글자색.
///
/// 버튼의 테두리와 면도 이 색을 알파만 달리해 쓴다 — 한 곳만 바꾸면 따라온다.
const Color _kOnPhoto = Color(0xFFFFFFFF);

/// 배경 사진의 흐림(논리 픽셀). 웹 모바일 로그인 배경의 `blur(6px)` 와 같은 값이다.
///
/// 로그인 화면에서만 쓴다 — 유리 재질(`kGlassBlur`)은 하단 바와 함께 쓰는
/// 공용 값이라 건드리지 않는다. 가장자리는 `ImageFilter.blur` 기본 `clamp` 가
/// 끝 픽셀을 늘려 채워 검은 테가 생기지 않는다.
const double _kPhotoBlur = 6.0;

// 사진과 유리 사이에 깔던 어두운 막(검정 15%)은 뺐다(2026-09-15). 전 사진
// (`player_mono.jpg`)이 밝아 흰 글자가 묻혀서 뒀던 것인데, 지금 사진은 원래
// 어두워 막이 연기만 죽였다. 🔴 밝은 사진으로 다시 바꾸면 막도 다시 필요하다 —
// 유리 면(흰색)을 올리는 것으로 대신하면 배경이 같이 밝아져 역효과다.

// --- 로그인 버튼 -------------------------------------------------------
//
// 형태는 `com.sumworship`의 로그인 버튼 그대로다 — 알약 테두리에 아주 옅은
// 면, 누르면 살짝 줄었다 튕겨 돌아온다. 글꼴만 이 프로젝트 것을 쓴다.

/// 버튼 높이. 라벨 크기와 따로 둔다 — 라벨을 줄였다고 버튼이 납작해지면 안 된다.
const double _kButtonHeight = 54.0;

/// 알약이 되도록 높이의 절반.
const double _kButtonRadius = 27.0;

const TextStyle _kButtonLabel = TextStyle(
  fontVariations: [FontVariation('wght', 900)],
  color: _kOnPhoto,
  fontSize: 16,
);

/// 유리 세기. 시트가 고정이라 늘 최대다.
///
/// 끌어올리는 시트였을 때는 진행도를 그대로 넘겼다 — 올라오는 만큼만 유리가
/// 서야 접힌 상태에 뿌연 띠가 안 남았다. 고정이 되면서 그 이유가 사라졌다.
const Animation<double> _kGlassOn = AlwaysStoppedAnimation<double>(1);

// --- 입력칸 -------------------------------------------------------------
//
// 웹(`www/src/components/ui/Field.tsx`)과 같은 모양이다 — 라벨은 칸 **위**,
// 칸은 둥근 테두리에 어두운 면. 면을 까는 이유도 같다: 뒤가 사진이라 경계가
// 묻히지 않게 한다.

/// 웹 `--ss-field-radius`.
const double _kFieldRadius = 14.0;

/// 웹 `.ss-field-input` 의 `--ss-bg 35%`.
const Color _kFieldFill = Color(0x59000000);

/// 웹 `Field` 테두리의 `--ss-fg 35%`.
const double _kFieldLine = 0.35;

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
  final _nickname = TextEditingController();

  bool _busy = false;
  String? _error;

  /// 가입 중인가. **경로를 따로 두지 않고 같은 시트에서 바꾼다** — 로그아웃
  /// 상태에서 갈 수 있는 곳은 `/login` 하나라(`app_router.dart` 의 redirect),
  /// 가입 경로를 새로 만들면 그 규칙부터 고쳐야 한다. 이메일 · 비밀번호 칸도
  /// 그대로 이어 쓴다 — 로그인하려다 가입으로 바꾼 사람이 다시 치지 않게.
  bool _signingUp = false;

  /// 비밀번호를 잠깐 보이게 했는가 — 웹 `Field` 의 `revealable` 과 같다.
  bool _revealPassword = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _nickname.dispose();
    super.dispose();
  }

  /// 보내기 전에 막을 것 — 규칙은 계약(`POST /auth/signup` 입력 제약)과 같다.
  /// 서버도 막지만(422) 눌러 보고 알게 하지 않는다. 형식이 애매한 이메일은
  /// 서버 판단에 맡긴다 — 여기서 정규식을 세우면 두 규칙이 갈린다.
  String? _signupProblem() {
    if (!_email.text.contains('@')) return '이메일을 확인해 주세요';
    if (_password.text.length < 8) return '비밀번호는 8자 이상이어야 합니다';
    final nick = _nickname.text.trim();
    if (nick.isEmpty || nick.length > 20) return '닉네임을 1~20자로 적어 주세요';
    return null;
  }

  void _toggleMode() {
    if (_busy) return;
    setState(() {
      _signingUp = !_signingUp;
      _error = null;
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (e) {
      // 429 면 잠그고 안내 문구를 낸다 — 그 외에는 서버가 준 메시지 그대로.
      final locked = ref.read(rateLimitControllerProvider.notifier).lockFrom(e);
      if (mounted) {
        setState(() => _error = locked ? null : '$e');
      }
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
          // 웹 로그인과 같은 사진이다(`www/public/login_figure.jpg` 를 그대로
          // 옮겼다) — 바꿀 때는 두 파일을 같이 바꾼다.
          //
          // 흐림은 **사진에** 건다. 유리 시트는 공용 [RefractiveGlass] 그대로
          // 두고(하단 바와 같은 재질), 그 셰이더가 읽는 뒤 화면이 이미 흐린
          // 사진이 되게 한다 — 유리 쪽에 BackdropFilter 를 또 얹으면 「유리 안에
          // 유리」가 되어 내용이 프레임째 사라진다(flutter/CLAUDE.md).
          ImageFiltered(
            imageFilter: ImageFilter.blur(
              sigmaX: _kPhotoBlur,
              sigmaY: _kPhotoBlur,
            ),
            child: const Image(
              image: AssetImage('assets/images/login_figure.jpg'),
              fit: BoxFit.cover,
            ),
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
    // 폼은 화면 아래에 붙고, 로고는 **화면 위 끝과 폼 사이의 한가운데**에
    // 선다(2026-09-15 사용자 결정 — 폼에 붙여 두면 로고가 아니라 폼의 제목처럼
    // 읽혔다). 남는 칸을 로고가 차지하고 그 안에서 가운데 정렬하므로, 폼이
    // 길어지면(가입 모드 · 키보드) 로고도 그 새 가운데로 따라 올라간다.
    //
    // 폼 + 로고가 화면보다 길어지면 통째로 스크롤된다 — `hasScrollBody: false`
    // 는 남는 높이를 채우되 내용이 더 길면 내용 높이를 쓴다.
    return SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverFillRemaining(
            hasScrollBody: false,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: Center(
                    // 인트로의 글자가 날아와 앉는 자리이자, 홈으로 갈 때 하단 바의
                    // 알약으로 다시 날아가는 출발점이다 — 같은 위젯, 같은 글꼴,
                    // 같은 크기. 비행은 GlobalKey 로 **실제 화면 좌표**를
                    // 읽으므로(`intro_gate.dart` `_landingRect`) 자리를 옮겨도
                    // 도착점이 따라온다.
                    child: brandHero(
                      child: BrandMark(
                        key: kBrandLandingKey,
                        fontSize: kBrandLandedSize,
                      ),
                    ),
                  ),
                ),
                _form(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _form() {
    final notifier = sessionControllerProvider.notifier;
    final secondsLeft = ref.watch(rateLimitControllerProvider);
    final locked = secondsLeft > 0;
    // **화면 아래에 붙인다**(2026-09-15 사용자 결정) — 엄지가 닿는 자리다.
    // 전에는 로고 바로 밑(위쪽)에 붙였다. 아래 여백에 키보드 높이를 더하므로
    // 키보드가 올라오면 폼도 그 위로 올라간다(`resizeToAvoidBottomInset: false`
    // 라 스캐폴드가 대신 해 주지 않는다).
    return Padding(
      padding: EdgeInsets.only(
        top: 28,
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
            // 문구는 웹 로그인 · 가입 페이지의 `formDescription` 그대로다.
            Text(
              _signingUp
                  ? '이메일과 비밀번호로 몇 초 만에 가입하세요.'
                  : '이메일과 비밀번호를 입력해 로그인하세요.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: _kOnPhoto.withValues(alpha: 0.85),
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 24),
            _field(
              key: const Key('login-email'),
              controller: _email,
              label: '이메일',
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 16),
            _field(
              key: const Key('login-password'),
              controller: _password,
              label: '비밀번호',
              hint: _signingUp ? '8자 이상' : null,
              revealable: true,
            ),
            if (_signingUp) ...[
              const SizedBox(height: 16),
              _field(
                key: const Key('signup-nickname'),
                controller: _nickname,
                label: '닉네임',
                hint: '1~20자',
              ),
            ],
            if (_error != null || locked) ...[
              const SizedBox(height: 16),
              Text(
                locked ? rateLimitNote(secondsLeft)! : _error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFFFF8A80), fontSize: 13),
              ),
            ],
            const SizedBox(height: 24),
            // 🔴 **키가 다르다** — 같은 키면 Flutter 가 버튼 상태(눌림 애니메이션)를
            // 이어 써서, 바꾼 직후 누른 것이 앞 모드의 동작으로 나갈 수 있다.
            if (_signingUp)
              _GlassButton(
                key: const Key('signup-submit'),
                label: '가입하기',
                enabled: !_busy && !locked,
                busy: _busy,
                onTap: () {
                  final problem = _signupProblem();
                  if (problem != null) {
                    setState(() => _error = problem);
                    return;
                  }
                  _run(
                    () => ref
                        .read(notifier)
                        .signup(
                          _email.text.trim(),
                          _password.text,
                          _nickname.text.trim(),
                        ),
                  );
                },
              )
            else
              _GlassButton(
                key: const Key('login-submit'),
                label: '로그인',
                enabled: !_busy && !locked,
                busy: _busy,
                onTap: () => _run(
                  () => ref.read(notifier).login(_email.text, _password.text),
                ),
              ),
            const SizedBox(height: 16),
            // 구글은 가입 경로가 따로 없다 — 처음 보는 계정이면 서버가 가입까지
            // 한다. 그래서 두 모드에 같은 동작으로 두고 글자만 웹처럼 바꾼다.
            // 🔴 잠금(429)은 버튼이 아니라 **보내는 쪽**에서 건다 — 웹과 같다.
            _GlassButton(
              key: const Key('google-submit'),
              label: _signingUp ? '구글 계정으로 가입' : '구글 계정으로 로그인',
              leading: const _GoogleMark(size: 20),
              enabled: !_busy,
              onTap: () {
                if (ref.read(rateLimitControllerProvider) > 0) return;
                _run(() => ref.read(notifier).loginWithGoogle());
              },
            ),
            const SizedBox(height: 32),
            // 아래는 웹 `AuthShell` 의 footer — 약관 문구, 그 아래 모드 바꾸기.
            // 줄을 손으로 끊는다 — 자연 줄바꿈에 맡기면 「간주됩 / 니다」처럼
            // 낱말 중간에서 잘렸다(갤럭시 A36 실측).
            Text(
              '계속 진행하면 이용약관과 개인정보처리방침에\n동의하는 것으로 간주됩니다.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: _kOnPhoto.withValues(alpha: 0.6),
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 4),
            // 모드 바꾸기 — 버튼보다 한 단계 낮은 글자 줄이다. 주 동작과 겨루면
            // 어느 것을 누르라는 것인지 흐려진다. 누를 곳은 뒤 낱말 하나라 그것만
            // 강조색이다(웹과 같다).
            Center(
              child: TextButton(
                key: const Key('auth-mode-toggle'),
                onPressed: _busy ? null : _toggleMode,
                style: TextButton.styleFrom(foregroundColor: _kOnPhoto),
                child: Text.rich(
                  TextSpan(
                    text: _signingUp ? '이미 계정이 있으신가요? ' : '계정이 없으신가요? ',
                    children: [
                      TextSpan(
                        text: _signingUp ? '로그인' : '회원가입',
                        style: const TextStyle(
                          color: AppTheme.seed,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  style: TextStyle(
                    color: _kOnPhoto.withValues(alpha: 0.85),
                    fontSize: 14,
                  ),
                ),
              ),
            ),
            // 🔴 **개발 빌드에서만** 선다(`kDebugMode`). 릴리스 빌드에는 코드째
            // 빠지므로 로그인 없이 들어오는 뒷문이 되지 않는다 — 같은 날 걷어낸
            // 「바로 진입」 셋이 API 모드에서 예외만 던지던 것과 달리, 이것은
            // **데이터를 목업으로 바꾼 뒤** 목업 계정으로 들어간다.
            // 서버가 꺼진 곳(집 · 인스턴스를 내린 뒤)에서 화면 작업을 잇는 용도다.
            if (kDebugMode && !_signingUp) ...[
              const SizedBox(height: 4),
              Center(
                child: OutlinedButton(
                  key: const Key('dev-only-login'),
                  onPressed: _busy ? null : _enterWithMock,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: _kOnPhoto.withValues(alpha: 0.7),
                    side: BorderSide(color: _kOnPhoto.withValues(alpha: 0.3)),
                    visualDensity: VisualDensity.compact,
                    shape: const StadiumBorder(),
                  ),
                  child: const Text('개발자 전용', style: TextStyle(fontSize: 12)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 데이터를 목업으로 바꾸고 목업의 개인 사용자로 들어간다. 이후로는 구글
  /// 로그인 단추도 목업이 받는다(토큰 검증 없이 같은 목업 사용자).
  void _enterWithMock() {
    ref.read(useMockProvider.notifier).useMock();
    _run(() => ref.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId));
  }

  /// [revealable] 이면 눈 단추로 입력값을 잠깐 볼 수 있는 비밀번호 칸이다.
  Widget _field({
    required Key key,
    required TextEditingController controller,
    required String label,
    String? hint,
    bool revealable = false,
    TextInputType? keyboardType,
  }) {
    OutlineInputBorder border(double alpha) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(_kFieldRadius),
      borderSide: BorderSide(color: _kOnPhoto.withValues(alpha: alpha)),
    );
    // 사진 위라 웹보다 글자를 한 단계 밝게 둔다(웹은 어두운 판 위 60% · 40%).
    final muted = _kOnPhoto.withValues(alpha: 0.85);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(label, style: TextStyle(color: muted, fontSize: 14)),
        const SizedBox(height: 6),
        TextField(
          key: key,
          controller: controller,
          obscureText: revealable && !_revealPassword,
          keyboardType: keyboardType,
          enabled: !_busy,
          style: const TextStyle(color: _kOnPhoto, fontSize: 16),
          cursorColor: _kOnPhoto,
          decoration: InputDecoration(
            isDense: true,
            filled: true,
            fillColor: _kFieldFill,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 14,
            ),
            enabledBorder: border(_kFieldLine),
            disabledBorder: border(_kFieldLine),
            // 웹은 35% → 40% 로 거의 안 바뀌는데, 사진 위에서는 그 차이가 안
            // 보여 어느 칸에 있는지 모른다. 초점은 또렷하게 올린다.
            focusedBorder: border(0.75),
            suffixIcon: revealable
                ? IconButton(
                    key: const Key('password-reveal'),
                    tooltip: _revealPassword ? '비밀번호 숨기기' : '비밀번호 보기',
                    onPressed: () =>
                        setState(() => _revealPassword = !_revealPassword),
                    icon: Icon(
                      _revealPassword
                          ? Icons.visibility_off_outlined
                          : Icons.visibility_outlined,
                      color: muted,
                      size: 20,
                    ),
                  )
                : null,
          ),
        ),
        if (hint != null) ...[
          const SizedBox(height: 6),
          Text(
            hint,
            style: TextStyle(
              color: _kOnPhoto.withValues(alpha: 0.6),
              fontSize: 12,
            ),
          ),
        ],
      ],
    );
  }
}

/// 구글 G 표식. 그림 파일 없이 네 색 호와 가로 막대로 그린다.
class _GoogleMark extends StatelessWidget {
  const _GoogleMark({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) => SizedBox.square(
    dimension: size,
    child: const CustomPaint(painter: _GoogleMarkPainter()),
  );
}

class _GoogleMarkPainter extends CustomPainter {
  const _GoogleMarkPainter();

  static const _blue = Color(0xFF4285F4);
  static const _green = Color(0xFF34A853);
  static const _yellow = Color(0xFFFBBC05);
  static const _red = Color(0xFFEA4335);

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.shortestSide;
    final stroke = s * 0.19;
    final rect = Rect.fromCircle(
      center: size.center(Offset.zero),
      radius: (s - stroke) / 2,
    );
    Paint arc(Color c) => Paint()
      ..color = c
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    double deg(double d) => d * 3.141592653589793 / 180;

    // 0° 가 3시, 시계 방향이다. 오른쪽 위(-45°~0°)가 G 의 벌어진 입이다.
    canvas.drawArc(rect, deg(0), deg(45), false, arc(_blue));
    canvas.drawArc(rect, deg(45), deg(95), false, arc(_green));
    canvas.drawArc(rect, deg(140), deg(75), false, arc(_yellow));
    canvas.drawArc(rect, deg(215), deg(100), false, arc(_red));
    // 가로 막대 — 가운데에서 바깥 끝까지.
    canvas.drawRect(
      Rect.fromLTRB(
        size.width / 2,
        size.height / 2 - stroke / 2,
        rect.right + stroke / 2,
        size.height / 2 + stroke / 2,
      ),
      Paint()..color = _blue,
    );
  }

  @override
  bool shouldRepaint(_GoogleMarkPainter old) => false;
}

/// 누르면 0.95배로 살짝 줄었다가 통통 튕기듯 돌아온 뒤 [onTap]을 부르는 버튼.
///
/// 형태는 `com.sumworship`의 로그인 버튼과 같다 — 면은 거의 비우고 테두리로
/// 세운다. 시트가 이미 유리라 그 위에 또 면을 얹으면 겹겹이 뿌예진다.
class _GlassButton extends StatefulWidget {
  const _GlassButton({
    super.key,
    required this.label,
    required this.onTap,
    this.enabled = true,
    this.busy = false,
    this.leading,
  });

  final String label;
  final VoidCallback onTap;
  final bool enabled;

  /// 라벨 왼쪽에 붙는 표식(구글 G). 버튼 모양은 그대로다.
  final Widget? leading;

  /// 참이면 라벨 대신 인디케이터를 그린다.
  final bool busy;

  @override
  State<_GlassButton> createState() => _GlassButtonState();
}

class _GlassButtonState extends State<_GlassButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _press = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 340),
  );

  late final Animation<double> _scale = TweenSequence<double>([
    TweenSequenceItem(
      weight: 30,
      tween: Tween(
        begin: 1.0,
        end: 0.95,
      ).chain(CurveTween(curve: Curves.easeOut)),
    ),
    TweenSequenceItem(
      weight: 70,
      tween: Tween(
        begin: 0.95,
        end: 1.0,
      ).chain(CurveTween(curve: Curves.easeOutBack)),
    ),
  ]).animate(_press);

  @override
  void dispose() {
    _press.dispose();
    super.dispose();
  }

  Future<void> _handleTap() async {
    if (!widget.enabled || _press.isAnimating) return;
    // 튕김이 끝난 뒤에 부른다 — 눌린 것이 눈에 보이고 나서 화면이 움직인다.
    await _press.forward(from: 0);
    if (!mounted) return;
    widget.onTap();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: _handleTap,
      child: AnimatedBuilder(
        animation: _scale,
        builder: (context, child) =>
            Transform.scale(scale: _scale.value, child: child),
        child: SizedBox(
          height: _kButtonHeight,
          child: CustomPaint(
            painter: const _LoginOutline(),
            child: Center(
              child: widget.busy
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: _kOnPhoto,
                      ),
                    )
                  : Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (widget.leading != null) ...[
                          widget.leading!,
                          const SizedBox(width: 10),
                        ],
                        Text(
                          widget.label,
                          style: widget.enabled
                              ? _kButtonLabel
                              : _kButtonLabel.copyWith(
                                  color: _kOnPhoto.withValues(alpha: 0.4),
                                ),
                        ),
                      ],
                    ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 버튼의 테두리와 옅은 면.
class _LoginOutline extends CustomPainter {
  const _LoginOutline();

  static const double _width = 1.4;

  /// 선의 밝기. **사방이 같다** — 그라데이션을 주면 한쪽만 흰 테두리로 보인다.
  static const double _lit = 0.75;

  /// 면의 밝기. "덮였다"가 아니라 "밝다"로만 읽힐 만큼.
  static const double _fill = 0.13;

  @override
  void paint(Canvas canvas, Size size) {
    final r = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(_kButtonRadius),
    ).deflate(_width / 2);

    canvas.drawRRect(r, Paint()..color = _kOnPhoto.withValues(alpha: _fill));
    canvas.drawRRect(
      r,
      Paint()
        ..color = _kOnPhoto.withValues(alpha: _lit)
        ..style = PaintingStyle.stroke
        ..strokeWidth = _width
        ..isAntiAlias = true,
    );
  }

  @override
  bool shouldRepaint(_LoginOutline old) => false;
}
