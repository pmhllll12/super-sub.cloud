import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 실행할 때 목업으로 시작할지 — `flutter run --dart-define=USE_MOCK=true`.
///
/// 웹의 `USE_MOCK=1`(www/.env.local)과 같은 뜻이다. 서버가 꺼져 있는 곳(집 ·
/// 학원 인스턴스를 내린 뒤)에서 화면 작업을 이어 가기 위한 것이다.
const bool kUseMockFromEnv = bool.fromEnvironment('USE_MOCK');

/// 데이터를 **목업에서** 받는가(참) · **실제 서버에서** 받는가(거짓).
///
/// 모든 리포지토리 교체 지점(`*_providers.dart`)이 이 값을 본다 — 🔴 화면에서
/// 이 값을 읽어 분기하지 않는다. 분기가 화면에 새면 「provider 한 줄 교체」가
/// 깨진다(flutter/CLAUDE.md).
///
/// 시작값은 [kUseMockFromEnv] 이고, 개발 빌드에서는 로그인 화면의 「개발자 전용」
/// 단추가 켠다.
class DataSourceController extends Notifier<bool> {
  @override
  bool build() => kUseMockFromEnv;

  void useMock() => state = true;
}

final useMockProvider =
    NotifierProvider<DataSourceController, bool>(DataSourceController.new);
