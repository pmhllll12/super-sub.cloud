import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';

void main() {
  group('CardStyle.photoKey', () {
    test('응답의 photo_key 를 읽는다', () {
      final style = CardStyle.fromJson(const {
        'photo_key': 'cards/photos/u-1/pc-1-1a2b3c4d.jpg',
      });

      expect(style.photoKey, equals('cards/photos/u-1/pc-1-1a2b3c4d.jpg'));
    });

    test('없으면 null 이다', () {
      expect(CardStyle.fromJson(const {}).photoKey, isNull);
    });

    test('저장할 때 그대로 싣는다', () {
      final style = CardStyle.fromJson(const {}).copyWith(photoKey: 'k-1');

      expect(style.toWire()['photo_key'], equals('k-1'));
    });

    /// 🔴 **이것이 이 파일의 핵심이다.** `toWire` 가 `...raw` 로 **앱이 모르는
    /// 칸**을 실어 나르는데, 앱이 아는 칸을 생략하면 원본의 옛 값이 살아남아
    /// **사진을 지워도 안 지워진다.**
    test('비우면 원본의 옛 키가 살아남지 않는다', () {
      final style = CardStyle.fromJson(const {'photo_key': 'old-key'});

      final cleared = style.copyWith(clearPhotoKey: true);

      expect(cleared.photoKey, isNull);
      expect(cleared.toWire()['photo_key'], isNull);
    });

    /// 🔴 **`null` 을 넘기는 것은 「안 바꿈」이다** — 비우는 뜻이 아니다.
    /// 둘을 뭉치면 크기만 조절하는 저장이 사진을 지운다.
    test('photoKey: null 은 「안 바꿈」이다', () {
      final style = CardStyle.fromJson(const {'photo_key': 'keep-me'});

      final same = style.copyWith(photoScale: 1.4);

      expect(same.photoKey, equals('keep-me'));
      expect(same.toWire()['photo_key'], equals('keep-me'));
    });

    /// 🔴 모르는 칸은 여전히 실어 나른다 — 서버가 칸을 늘렸는데 앱이 아직
    /// 안 읽는 값이면, 저장 한 번에 그 값이 사라진다.
    test('모르는 칸은 그대로 실어 나른다', () {
      final style = CardStyle.fromJson(const {'some_new_field': 7});

      expect(style.toWire()['some_new_field'], equals(7));
    });
  });
}
