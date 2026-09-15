import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_brush.dart';

/// 🔴 붓자국 무늬가 **웹과 같은지**를 지키는 시험이다. 기대값은 웹
/// `www/src/components/PlayerCardBrush.tsx` 의 `hash` · `rng` 를 node 로 그대로
/// 돌려 뽑았다(2026-09-15). 여기가 빨개지면 같은 카드가 웹과 앱에서 다른
/// 무늬로 그려진다 — 기대값을 앱 결과에 맞춰 고치지 말고 수식을 웹에 맞춘다.
void main() {
  test('해시가 웹과 같다', () {
    expect(brushHash('hong-gildong-4f2a'), 1439959468);
    // 한글은 UTF-16 단위로 돈다(JS charCodeAt).
    expect(brushHash('백성검-00ab'), 4181578827);
  });

  test('난수 수열이 웹과 같다', () {
    const expected = {
      'hong-gildong-4f2a': [0.673788970103, 0.970240031369, 0.929326354060, 0.734664981719],
      '백성검-00ab': [0.520521143219, 0.996315023862, 0.918445027666, 0.904882461997],
    };
    expected.forEach((seed, values) {
      final next = brushRng(brushHash(seed));
      for (final v in values) {
        expect(next(), closeTo(v, 1e-12), reason: seed);
      }
    });
  });
}
