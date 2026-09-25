/// 수락된 지인 한 명 — `GET /me/contacts` 의 `items` 한 줄(계약 3-12절).
///
/// **상호 관계다** — 내가 신청했든 상대가 신청했든 상대방이 평평하게 실린다.
class Contact {
  const Contact({
    required this.contactId,
    required this.userId,
    required this.nickname,
    this.note,
    this.cardPublicSlug,
  });

  factory Contact.fromJson(Map<String, dynamic> json) => Contact(
        contactId: json['contact_id'] as String,
        userId: json['user_id'] as String,
        nickname: json['nickname'] as String,
        note: json['note'] as String?,
        cardPublicSlug: json['card_public_slug'] as String?,
      );

  final String contactId;
  final String userId;
  final String nickname;

  /// 🔴 **내가 신청자일 때만** 온다 — 상대가 쓴 적 없는 내 개인 메모라서다.
  final String? note;

  /// 🔴 **계약의 `/me/contacts` 는 이 칸을 안 준다**(2026-09-25 확인). 웹은
  /// 읽고 있지만 늘 비어 있다. 없으면 판이 이름표로 물러나게 두고 **카드를
  /// 지어내지 않는다** — 서버가 나중에 실어 주면 그대로 쓰인다.
  final String? cardPublicSlug;
}

/// 나에게 온 **대기중** 지인 신청 — `GET /me/contacts/requests` 의 한 줄.
class ContactRequest {
  const ContactRequest({
    required this.id,
    required this.requesterUserId,
    this.note,
  });

  factory ContactRequest.fromJson(Map<String, dynamic> json) => ContactRequest(
        id: json['id'] as String,
        requesterUserId: json['requester_user_id'] as String,
        note: json['note'] as String?,
      );

  /// 수락할 때 쓰는 id — `POST /me/contacts/{id}/accept`.
  final String id;
  final String requesterUserId;
  final String? note;
}

/// 닉네임 검색 결과 한 줄 — `GET /users/search?q=`.
///
/// 🔴 **끈 사람과 본인은 서버가 뺀다**(계약) — 화면이 다시 거르지 않는다.
class FoundUser {
  const FoundUser({required this.id, required this.nickname});

  factory FoundUser.fromJson(Map<String, dynamic> json) => FoundUser(
        id: json['id'] as String,
        nickname: json['nickname'] as String,
      );

  final String id;
  final String nickname;
}
