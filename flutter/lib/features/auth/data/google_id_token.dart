import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'auth_repository.dart';

/// 구글 클라우드의 **"웹 애플리케이션"** 클라이언트 ID.
///
/// 🔴 안드로이드 클라이언트 ID 가 아니다(계약 `POST /auth/google` 의 「앱 쪽에서 할
/// 일」). 안드로이드 클라이언트는 패키지·서명을 구글에 등록하는 용도이고, ID 토큰의
/// `aud` 에는 이 값이 들어간다 — 잘못 넣으면 **로그인은 되는데 서버가 401 만 준다.**
///
/// 저장소가 공개라 코드에 박지 않고 실행할 때 넘긴다. 웹(`www/.env.local` 의
/// `NEXT_PUBLIC_GOOGLE_CLIENT_ID`)과 같은 값이다:
///   flutter run --dart-define=GOOGLE_SERVER_CLIENT_ID=<웹 클라이언트 ID>
const String googleServerClientId = String.fromEnvironment(
  'GOOGLE_SERVER_CLIENT_ID',
);

/// 구글 계정 선택 창을 띄워 **ID 토큰**을 받아 온다.
///
/// 인증 저장소와 따로 둔 이유: 저장소는 토큰을 서버에 넘기는 일만 하고, 창을
/// 띄우는 일은 기기 기능이라 위젯 시험에서 갈아 끼워야 한다.
abstract class GoogleIdTokenSource {
  /// 사용자가 창을 닫으면 `null` — 실패가 아니라서 오류 문구를 띄우지 않는다.
  Future<String?> fetchIdToken();
}

class GoogleSignInIdTokenSource implements GoogleIdTokenSource {
  Future<void>? _initialized;

  @override
  Future<String?> fetchIdToken() async {
    if (googleServerClientId.isEmpty) {
      throw const AuthException(
        '구글 로그인이 설정되지 않았습니다 (GOOGLE_SERVER_CLIENT_ID)',
      );
    }
    final signIn = GoogleSignIn.instance;
    try {
      // `initialize` 는 한 번만 부른다. 실패했으면 다음 탭에서 다시 시도한다.
      await (_initialized ??=
          signIn.initialize(serverClientId: googleServerClientId));
      final account = await signIn.authenticate();
      final idToken = account.authentication.idToken;
      if (idToken == null) {
        throw const AuthException('구글이 ID 토큰을 주지 않았습니다');
      }
      return idToken;
    } on GoogleSignInException catch (e) {
      _initialized = null;
      // 설정이 틀린 경우(서명 SHA-1 미등록 등)도 기기에 따라 canceled 로 온다 —
      // 원인을 찾을 수 있게 로그는 늘 남긴다.
      debugPrint('google_sign_in: ${e.code} ${e.description}');
      switch (e.code) {
        case GoogleSignInExceptionCode.canceled:
        case GoogleSignInExceptionCode.interrupted:
          return null;
        case GoogleSignInExceptionCode.clientConfigurationError:
        case GoogleSignInExceptionCode.providerConfigurationError:
          throw const AuthException('구글 로그인 설정이 맞지 않습니다');
        default:
          throw const AuthException('구글 로그인에 실패했습니다');
      }
    }
  }
}

final googleIdTokenSourceProvider = Provider<GoogleIdTokenSource>(
  (ref) => GoogleSignInIdTokenSource(),
);
