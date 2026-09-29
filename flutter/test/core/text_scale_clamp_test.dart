import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/app.dart';

/* 🔴 **시스템 글꼴 배율에 상한이 있다** (2026-09-29 사용자 지적: 「좀 작은
   휴대폰들은 글자나 버튼 모든게 커지거나」).

   이 앱은 `fontSize` 가 대부분 **고정 논리 픽셀**이라 칸이 글자를 따라
   안 늘어난다. 폰 설정의 큰 글꼴을 그대로 받으면 버튼 글자가 넘친다.

   ⛔ **상한을 걷으려면 화면들이 글자 크기를 따라 늘어나게 먼저 고친다** —
   그 전에 걷으면 이 시험이 막으려던 깨짐이 그대로 돌아온다. */
void main() {
  double scaled(double system) =>
      clampTextScale(TextScaler.linear(system)).scale(100) / 100;

  test('시스템이 2배여도 상한까지만 커진다', () {
    expect(scaled(2), closeTo(kMaxTextScale, 0.001));
  });

  test('3배도 마찬가지다', () {
    expect(scaled(3), closeTo(kMaxTextScale, 0.001));
  });

  test('1배는 그대로다', () {
    expect(scaled(1), closeTo(1, 0.001));
  });

  /// 상한 아래는 손대지 않는다 — 조금 키운 사람은 그대로 조금 커진다.
  test('상한 아래는 그대로 따라간다', () {
    expect(scaled(1.1), closeTo(1.1, 0.001));
  });

  /// 🔴 **줄이지는 않는다** — 작게 쓰는 사람에게 억지로 키우면 그쪽이 깨진다.
  test('0.8배는 1배로 올린다', () {
    expect(scaled(0.8), closeTo(1, 0.001));
  });

  /// ⛔ 상한을 걷으면 이 시험이 먼저 깨진다.
  test('상한이 1.2 다', () {
    expect(kMaxTextScale, 1.2);
  });
}
