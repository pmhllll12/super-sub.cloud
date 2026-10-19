import 'models/contact.dart';

/// 지인 — 계약 3-12절. **상호 관계다**: 신청은 한쪽이 하지만 수락하면 양쪽이
/// 서로를 지인 목록에서 본다.
abstract class ContactRepository {
  /// 수락된 지인 목록 — `GET /me/contacts`.
  Future<List<Contact>> contacts();

  /// 나에게 온 **대기중** 신청 — `GET /me/contacts/requests`.
  Future<List<ContactRequest>> requests();

  /// 닉네임 부분일치로 찾는다 — `GET /users/search?q=`.
  ///
  /// 🔴 끈 사람과 본인은 **서버가 뺀다** — 화면이 다시 거르지 않는다.
  /// 못 찾으면 빈 목록이다(예외가 아니다).
  Future<List<FoundUser>> search(String query);

  /// 지인 신청 — `POST /me/contacts`.
  ///
  /// 🔴 **이미 신청했거나 이미 지인이면(409 `ALREADY_REQUESTED`) 성공으로
  /// 친다.** 사용자가 원하던 상태가 이미 이뤄진 것이라 오류로 보일 이유가
  /// 없다. 자기 자신(422 `CANNOT_REQUEST_SELF`)은 다르다 — 그건 드러낸다.
  Future<void> request(String targetUserId);

  /// 받은 신청 수락 — `POST /me/contacts/{id}/accept`.
  Future<void> accept(String contactId);
}
