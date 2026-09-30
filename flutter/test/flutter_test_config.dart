import 'dart:async';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// 🔴 **번들한 글꼴을 시험에도 싣는다** (2026-09-24).
///
/// `flutter test` 는 `pubspec.yaml` 의 글꼴을 **안 싣는다** — `fontFamily` 가
/// 안 풀려 대체 글꼴로 그려진다. 그 대체 글꼴은 글자 폭이 달라서, **자리를
/// 재는 시험이 실기기와 다른 답을 낸다.**
///
/// 실제로 그것 때문에 한 번 속았다: 홈의 소개 두 줄(펴진고딕 35)이 **시험에서만
/// 두 배로 접혀** 화면 위로 올라왔고, 「맨 위 다크 판이 그 줄을 침범한다」로
/// 읽혀 판을 늘렸다가 되돌렸다. 실기기에서는 2줄이고 판과 41px 떨어져 있었다.
///
/// 🔴 **파일 이름을 바꾸지 말 것** — `flutter_test` 가 `test/` 아래의
/// `flutter_test_config.dart` 를 **이름으로 찾아** 모든 시험 앞에 돌린다.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  TestWidgetsFlutterBinding.ensureInitialized();
  await _loadFont('PyeojinGothic', 'assets/fonts/PyeojinGothic-Black.ttf');
  await _loadFont('Rubik', 'assets/fonts/Rubik-VariableFont.ttf');
  await _loadFont('RubikGlitch', 'assets/fonts/RubikGlitch-Regular.ttf');
  await _loadFont('YatraOne', 'assets/fonts/YatraOne-Regular.ttf');
  await _loadFont('YoungSerif', 'assets/fonts/YoungSerif-Regular.ttf');
  await testMain();
}

/// 🔴 **없으면 조용히 건너뛴다.** 글꼴 하나가 빠졌다고 시험 전체가 못 돌면
/// 안 된다 — 못 실으면 예전처럼 대체 글꼴로 그려질 뿐이다.
Future<void> _loadFont(String family, String path) async {
  final file = File(path);
  if (!file.existsSync()) return;
  final loader = FontLoader(family)
    ..addFont(file.readAsBytes().then(ByteData.sublistView));
  await loader.load();
}
