import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 로그인 토큰을 **앱을 껐다 켜도 남는 곳**에 둔다.
///
/// 🔴 **왜 있나** (미결 `min` 25번, 박민호 제보). 토큰이 메모리에만 있어서
/// 앱을 완전히 종료하면 무조건 로그아웃이었다 — APK 를 받아 본 팀장이 바로
/// 걸렸다. 웹(`www/`)은 같은 문제를 httpOnly 쿠키로 이미 풀어 두었다.
///
/// 🔴 **가로대(인터페이스)를 둔 이유는 시험이다.** 진짜 저장소는 안드로이드
/// Keystore · iOS Keychain 이라 **플러그인 채널이 필요해 단위 시험에서 못
/// 돈다.** 시험은 [InMemoryTokenStore] 를 물려 "새 인스턴스에서도 세션이
/// 돌아온다"는 성질만 본다 — 그 성질이 이 항목이 요구한 전부다.
abstract class TokenStore {
  Future<String?> read();
  Future<void> write(String token);

  /// 마지막으로 받은 `GET /me` **응답 본문 그대로**(JSON 글자).
  ///
  /// 🔴 **왜 본문을 통째로 두나** — `AppUser` 를 따로 직렬화하면 서버 응답을
  /// 읽는 파서와 **두 벌**이 되고, 계약이 늘 때 한쪽만 고쳐져도 아무 데서도
  /// 안 터진다. 본문을 그대로 두면 복원도 **같은 파서**를 탄다.
  ///
  /// 🔴 **비밀이 아니다** — 닉네임·이메일이라 토큰과 달리 감출 값은 아니지만,
  /// 저장소를 하나 더 들이는 것보다 같은 자리에 두는 편이 간단하다.
  Future<String?> readProfile();
  Future<void> writeProfile(String json);

  /// 🔴 **토큰과 프로필을 함께 지운다** — 하나만 지우면 다음에 켤 때
  /// 「토큰 없는 인사말」이나 「인사말 없는 세션」이 남는다.
  Future<void> clear();
}

/// 진짜 저장소 — 안드로이드 Keystore · iOS Keychain.
///
/// 🔴 **평문 저장소(`shared_preferences`)를 안 쓴다**(사용자 판단, 2026-09-17).
/// 그쪽은 루팅된 기기나 백업 파일에서 토큰이 **그대로 읽힌다.** 미결 항목의
/// 「참고」도 이쪽을 가리켰다.
///
/// ⚠️ **플러그인이라 핫 리로드로는 안 붙는다** — 넣고 나면 다시 빌드해야
/// 한다(`google_sign_in`·`video_player` 때와 같다).
class SecureTokenStore implements TokenStore {
  /// ⚠️ **옵션을 따로 주지 않는다.** `flutter_secure_storage` 11 부터는 기본
  /// 생성자가 이미 Keystore 기반(데이터 AES-GCM · 키는 RSA-OAEP 로 감쌈)이다 —
  /// 10 까지 쓰던 `AndroidOptions(encryptedSharedPreferences: true)` 는 **이제
  /// 없는 인자**라 적으면 컴파일이 안 된다(2026-09-17에 실제로 걸렸다).
  const SecureTokenStore([this._storage = const FlutterSecureStorage()]);

  final FlutterSecureStorage _storage;

  /// 🔴 **키 이름에 뜻을 담지 않는다** — 기기에 남는 이름이라
  /// 「supersub_access_token」처럼 적으면 무엇을 캐낼지 알려 주는 셈이다.
  static const _key = 'ss.t';

  /// 같은 까닭으로 뜻을 안 담는다.
  static const _profileKey = 'ss.p';

  /* 🔴 **저장소가 없거나 열리지 않아도 앱은 뜬다.** 플러그인 채널이 없는 곳
     (위젯 시험·기기 이상)에서 예외가 그대로 올라오면 `SessionController` 의
     복원이 끝나지 않아 **첫 화면에서 멈춘다** — 로그인 화면조차 안 나온다
     (2026-09-17에 스모크 시험이 그걸로 깨졌다). 못 읽으면 「저장된 것이
     없다」로 본다: 사람은 로그인 화면을 보고 다시 들어가면 된다.

     ⚠️ **예외 내용을 로그로 남기지 않는다** — 토큰이 딸려 나갈 수 있다
     (루트 `CLAUDE.md` 의 공개 금지 원칙). */

  @override
  Future<String?> read() async {
    try {
      return await _storage.read(key: _key);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> write(String token) async {
    try {
      await _storage.write(key: _key, value: token);
    } catch (_) {
      /* 못 남겨도 **이번 실행의 로그인은 그대로 된다** — 토큰이 메모리에는
         있다. 다음에 켤 때 다시 로그인하게 될 뿐이라 여기서 막지 않는다. */
    }
  }

  @override
  Future<String?> readProfile() async {
    try {
      return await _storage.read(key: _profileKey);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> writeProfile(String json) async {
    try {
      await _storage.write(key: _profileKey, value: json);
    } catch (_) {
      /* 못 남겨도 이번 실행은 그대로 된다 — 다음에 켤 때 한 번 더
         `GET /me` 를 기다릴 뿐이다(고치기 전의 동작). */
    }
  }

  @override
  Future<void> clear() async {
    try {
      await _storage.delete(key: _key);
      // 🔴 프로필도 함께 — 남기면 로그아웃한 사람의 인사말이 다음에 뜬다.
      await _storage.delete(key: _profileKey);
    } catch (_) {
      /* 지우지 못했어도 메모리의 토큰은 이미 버렸다. */
    }
  }
}

/// 시험용 — 플러그인 채널 없이 같은 약속을 지킨다.
class InMemoryTokenStore implements TokenStore {
  String? _token;
  String? _profile;

  @override
  Future<String?> read() async => _token;

  @override
  Future<void> write(String token) async => _token = token;

  @override
  Future<String?> readProfile() async => _profile;

  @override
  Future<void> writeProfile(String json) async => _profile = json;

  @override
  Future<void> clear() async {
    _token = null;
    _profile = null;
  }
}
