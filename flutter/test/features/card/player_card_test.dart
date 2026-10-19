import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';

const _wire = {
  'id': '7b4d',
  'public_slug': 'hong-gildong-4f2a',
  'og_image_key': 'cards/7b4d.png',
  'user': {'id': '3f1c', 'nickname': '홍길동'},
  'titles': [
    {
      'code': 'sharp_shooter',
      'label': '슈팅이 매서운',
      'category': '강점',
      'granted_at': '2026-08-20T12:00:00Z',
    }
  ],
  'tagline': 'THREE LUNGS',
  'style': {'bg': '#91ea92', 'brush': 3},
};

PlayerCard _card({Object? tagline = 'x', Object? style = const {'bg': '#fff'}}) =>
    PlayerCard.fromJson({
      ..._wire,
      'tagline': tagline,
      'style': style,
    });

void main() {
  test('계약 응답을 읽는다', () {
    final card = PlayerCard.fromJson(_wire);

    expect(card.id, '7b4d');
    expect(card.publicSlug, 'hong-gildong-4f2a');
    expect(card.nickname, '홍길동');
    expect(card.tagline, 'THREE LUNGS');
    expect(card.titles.single.label, '슈팅이 매서운');
    expect(card.titles.single.category, '강점');
    expect(card.style!.raw['brush'], 3);
  });

  test('tagline·style 이 null 이면 null 로 둔다 — 지어내지 않는다', () {
    final card = _card(tagline: null, style: null);

    expect(card.tagline, isNull);
    expect(card.style, isNull);
  });

  test('titles 가 없어도 빈 목록이다', () {
    final json = Map<String, dynamic>.from(_wire)..remove('titles');
    expect(PlayerCard.fromJson(json).titles, isEmpty);
  });

  test('공개 응답에는 id 가 없다 — 그래도 읽힌다', () {
    // `GET /cards/{slug}` 는 공개해도 되는 것만 담느라 id 를 뺀다.
    final json = Map<String, dynamic>.from(_wire)..remove('id');
    expect(PlayerCard.fromJson(json).id, isNull);
    expect(PlayerCard.fromJson(json).publicSlug, 'hong-gildong-4f2a');
  });

  test('그릴 사진 주소는 photo_url 이다 — style.photo_key 가 아니다', () {
    // 🔴 photo_key 는 저장용이고, 그릴 수 있는 것은 사전 서명된 photo_url 이다.
    final card = PlayerCard.fromJson({
      ..._wire,
      'photo_url': 'https://example.test/signed',
      'style': {'photo_key': 'cards/abc.png'},
    });

    expect(card.photoUrl, 'https://example.test/signed');
  });

  group('aliasOf — 「비웠다」와 「안 정했다」를 style 로 가른다', () {
    test('tagline 이 있으면 그대로', () {
      expect(aliasOf(_card(tagline: '두 개의 심장')), '두 개의 심장');
    });

    test('🔴 tagline 이 null 이고 style 이 있으면 일부러 지운 것 — 글자 없음', () {
      // 서버는 null 과 "   " 를 똑같이 다뤄 tagline 만으로는 못 가른다.
      // style 이 있다는 것은 저장을 한 번 거쳤다는 뜻이다.
      expect(aliasOf(_card(tagline: null)), isEmpty);
    });

    test('tagline·style 둘 다 없으면 한 번도 안 꾸민 카드 — 기본 별명', () {
      expect(aliasOf(_card(tagline: null, style: null)), kDefaultCardAlias);
    });

    test('빈 문자열 tagline 도 그대로 빈 글자다', () {
      expect(aliasOf(_card(tagline: '')), isEmpty);
    });
  });
}
