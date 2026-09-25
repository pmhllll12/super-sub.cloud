import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/squad_candidate.dart';

void main() {
  group('SquadCandidate', () {
    test('후보 한 명을 읽는다', () {
      final c = SquadCandidate.fromJson(const {
        'user_id': '7c05',
        'nickname': '김선우',
        'card_public_slug': 'kim-abc1',
        'grade': 'A',
        'provisional': false,
        'notes': ['차는 다리를 끝까지 뻗습니다', '디딤발을 공 옆에 붙입니다'],
      });

      expect(c.userId, '7c05');
      expect(c.nickname, '김선우');
      expect(c.cardPublicSlug, 'kim-abc1');
      expect(c.grade, 'A');
      expect(c.provisional, isFalse);
      expect(c.notes, hasLength(2));
    });

    /// 🔴 계약(3-14절): 카드가 없는 사람은 `card_public_slug`·`grade`·
    /// `provisional`·`notes` 가 **전부 `null`** 로 온다. 그게 정상이다.
    test('카드가 없는 후보는 등급도 문구도 없다', () {
      final c = SquadCandidate.fromJson(const {
        'user_id': '3af2',
        'nickname': '오재현',
        'card_public_slug': null,
        'grade': null,
        'provisional': null,
        'notes': null,
      });

      expect(c.nickname, '오재현');
      expect(c.cardPublicSlug, isNull);
      expect(c.grade, isNull);
      expect(c.provisional, isNull);
      expect(c.notes, isEmpty);
    });

    /// 🔴 **화면이 문구를 지어내지 않는다**(계약이 못 박은 것). 한 줄짜리도
    /// 정상이라 「두 줄이어야 한다」고 채우면 없는 말을 카드에 그리게 된다.
    test('문구가 한 줄이어도 그대로 한 줄이다', () {
      final c = SquadCandidate.fromJson(const {
        'user_id': 'u1',
        'nickname': '한박자',
        'notes': ['첫 터치를 앞으로 길게 놓습니다'],
      });

      expect(c.notes, ['첫 터치를 앞으로 길게 놓습니다']);
    });

    /// 카드가 없으면 그릴 썸네일도 없다 — 화면이 그 판단을 여기서 읽는다.
    test('카드가 있어야 썸네일을 물어볼 수 있다', () {
      expect(
        SquadCandidate.fromJson(const {
          'user_id': 'u1',
          'nickname': 'ㄱ',
          'card_public_slug': 'a-1',
        }).hasCard,
        isTrue,
      );
      expect(
        SquadCandidate.fromJson(const {'user_id': 'u2', 'nickname': 'ㄴ'})
            .hasCard,
        isFalse,
      );
    });
  });
}
