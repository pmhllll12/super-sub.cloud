import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/contact.dart';

void main() {
  group('Contact', () {
    test('지인 한 명을 읽는다', () {
      final c = Contact.fromJson(const {
        'contact_id': 'ct-1',
        'user_id': 'u-1',
        'nickname': '김철수',
        'note': '같은 동네',
        'accepted_at': '2026-09-20T10:00:00Z',
      });

      expect(c.contactId, 'ct-1');
      expect(c.userId, 'u-1');
      expect(c.nickname, '김철수');
      expect(c.note, '같은 동네');
    });

    /// 🔴 `note` 는 **내가 신청자일 때만** 온다(계약) — 없는 것이 정상이다.
    test('메모가 없어도 지인이다', () {
      final c = Contact.fromJson(const {
        'contact_id': 'ct-2',
        'user_id': 'u-2',
        'nickname': '정어진',
        'note': null,
        'accepted_at': '2026-09-20T10:00:00Z',
      });

      expect(c.note, isNull);
    });

    /// 🔴 **계약의 `/me/contacts` 는 `card_public_slug` 를 안 준다.** 웹은 그
    /// 칸을 읽고 있는데 응답에 없어서 늘 비어 있다(미결에 올릴 것). 앱은
    /// 없는 것을 정상으로 받고, 없으면 판이 이름표로 물러난다 — **카드를
    /// 지어내지 않는다.**
    test('카드 슬러그는 안 와도 된다', () {
      final c = Contact.fromJson(const {
        'contact_id': 'ct-3',
        'user_id': 'u-3',
        'nickname': '정상호',
        'accepted_at': '2026-09-20T10:00:00Z',
      });

      expect(c.cardPublicSlug, isNull);
    });
  });

  group('ContactRequest', () {
    test('나에게 온 신청을 읽는다', () {
      final r = ContactRequest.fromJson(const {
        'id': 'ct-9',
        'requester_user_id': 'u-9',
        'target_user_id': 'me',
        'note': null,
        'accepted_at': null,
        'created_at': '2026-09-24T09:00:00Z',
      });

      expect(r.id, 'ct-9');
      expect(r.requesterUserId, 'u-9');
    });
  });

  group('FoundUser', () {
    test('검색 결과 한 줄을 읽는다', () {
      final f = FoundUser.fromJson(const {'id': 'u-5', 'nickname': '한박자'});

      expect(f.id, 'u-5');
      expect(f.nickname, '한박자');
    });
  });
}
