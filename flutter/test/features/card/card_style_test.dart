import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';

CardStyle _style([Map<String, dynamic> over = const {}]) =>
    CardStyle.fromJson({'bg': '#91ea92', ...over});

void main() {
  group('색', () {
    test('#rrggbb 를 읽는다', () {
      expect(_style({'bg': '#91ea92'}).bg, const Color(0xFF91EA92));
    });

    test('대문자도 읽는다', () {
      expect(_style({'bg': '#91EA92'}).bg, const Color(0xFF91EA92));
    });

    /// 🔴 서버가 이상한 값을 주거나 칸이 비어도 **카드는 그려져야 한다** —
    /// 여기서 던지면 판 전체가 안 뜬다.
    test('모양이 틀리면 기본값으로 물러난다', () {
      expect(_style({'bg': 'red'}).bg, kCardBg);
      expect(_style({'bg': null}).bg, kCardBg);
      expect(_style({'bg': '#zzz'}).bg, kCardBg);
    });

    /// 🔴 `text_color` 하나가 별명·머리글·(logo 없을 때)워드마크·기본 붓자국을
    /// 한꺼번에 정한다. 자리마다 따로 칠하면 반드시 빠지는 곳이 생긴다.
    test('logo 가 없으면 text_color 를 따른다', () {
      final s = _style({'text_color': '#123456'});

      expect(s.textColor, const Color(0xFF123456));
      expect(s.logo, const Color(0xFF123456));
    });

    test('logo 가 있으면 그것이 이긴다', () {
      final s = _style({'text_color': '#123456', 'logo': '#abcdef'});

      expect(s.logo, const Color(0xFFABCDEF));
    });

    test('brush_color 가 없으면 text_color 를 따른다', () {
      expect(_style({'text_color': '#123456'}).brushColor,
          const Color(0xFF123456));
    });
  });

  group('기본값 — 안 꾸민 카드와 같아야 한다', () {
    test('빈 style 은 기본 모습이다', () {
      final s = CardStyle.fromJson(const {});

      expect(s.bg, kCardBg);
      expect(s.textColor, kCardFg);
      expect(s.textX, 50);
      expect(s.textY, 34);
      expect(s.brush, 0);
      expect(s.brushScale, 1);
      expect(s.brushX, 0);
      expect(s.brushY, 0);
      expect(s.photoScale, 1);
      expect(s.mode, CardMode.cutout);
    });
  });

  group('숫자', () {
    test('정수도 실수도 읽는다', () {
      expect(_style({'text_x': 30}).textX, 30.0);
      expect(_style({'text_x': 30.5}).textX, 30.5);
    });

    test('숫자가 아니면 기본값이다', () {
      expect(_style({'text_x': 'abc'}).textX, 50);
      expect(_style({'brush_scale': null}).brushScale, 1);
    });

    test('brush 는 정수다', () {
      expect(_style({'brush': 12}).brush, 12);
      expect(_style({'brush': '12'}).brush, 0);
    });
  });

  group('mode', () {
    test('full 을 읽는다', () {
      expect(_style({'mode': 'full'}).mode, CardMode.full);
    });

    test('모르는 값은 cutout 이다', () {
      expect(_style({'mode': 'wat'}).mode, CardMode.cutout);
      expect(_style({'mode': null}).mode, CardMode.cutout);
    });
  });

  group('자국 그림 — 번호는 영구 계약이다', () {
    /// 🔴 배열에서 항목을 빼면 그 뒤 번호가 당겨져 **남의 카드가 말없이 다른
    /// 그림**이 된다. 파일 번호 = brush − 1 이고 두 자리로 채운다.
    test('brush 2 는 01.png 다', () {
      expect(markAssetFor(2), 'assets/marks/01.png');
    });

    test('brush 18 은 17.png 다', () {
      expect(markAssetFor(18), 'assets/marks/17.png');
    });

    test('brush 0 은 절차적 붓자국이라 그림이 없다', () {
      expect(markAssetFor(0), isNull);
    });

    test('brush 1 은 「없음」이라 아무것도 안 그린다', () {
      expect(markAssetFor(1), isNull);
    });

    /// 🔴 저장된 값이 목록보다 클 수 있다 — 그때는 아무것도 안 그린다.
    test('범위 밖이면 그림이 없다', () {
      expect(markAssetFor(19), isNull);
      expect(markAssetFor(-1), isNull);
    });
  });
}
