import '../../../core/network/api_client.dart';
import 'contact_repository.dart';
import 'models/contact.dart';

/// 백엔드 없이 도는 지인 저장소.
///
/// 🔴 **서버가 막는 것을 여기서도 막는다**(자기 자신 · 없는 신청). Mock 이 다
/// 받아 주면 목업으로 만든 화면이 진짜 서버에서 처음으로 422·404 를 만난다.
class MockContactRepository implements ContactRepository {
  MockContactRepository();

  static const _delay = Duration(milliseconds: 300);
  static const _myId = 'u-me';

  /// 🔴 카드가 **있는 지인과 없는 지인**을 섞어 둔다 — 없는 쪽은 판이
  /// 이름표로 물러나는 갈래다.
  final List<Contact> _contacts = [
    const Contact(
      contactId: 'ct-1',
      userId: 'u-jin',
      nickname: '정어진',
      cardPublicSlug: 'jin-4d10',
    ),
    const Contact(contactId: 'ct-2', userId: 'u-ho', nickname: '정상호'),
  ];

  final List<ContactRequest> _requests = [
    const ContactRequest(id: 'ct-pending', requesterUserId: 'u-pass'),
  ];

  static const _directory = [
    FoundUser(id: 'u-pass', nickname: '한박자빠른패스'),
    FoundUser(id: 'u-stranger', nickname: '처음보는사람'),
    FoundUser(id: 'u-line', nickname: '라인세우기'),
  ];

  /// 이미 신청을 보낸 사람 — 두 번째 신청은 409 이고, 그걸 **성공으로 친다**.
  final Set<String> _sent = {};

  @override
  Future<List<Contact>> contacts() async {
    // Mock 이 즉시 성공하면 로딩 UI 를 안 만들게 된다.
    await Future<void>.delayed(_delay);
    return List.of(_contacts);
  }

  @override
  Future<List<ContactRequest>> requests() async {
    await Future<void>.delayed(_delay);
    return List.of(_requests);
  }

  @override
  Future<List<FoundUser>> search(String query) async {
    await Future<void>.delayed(_delay);
    final q = query.toLowerCase();
    if (q.isEmpty) return const [];
    return _directory
        .where((f) => f.nickname.toLowerCase().contains(q))
        .toList();
  }

  @override
  Future<void> request(String targetUserId) async {
    await Future<void>.delayed(_delay);

    if (targetUserId == _myId) {
      throw const ApiException('자기 자신에게는 신청할 수 없습니다',
          code: 'CANNOT_REQUEST_SELF', status: 422);
    }
    if (!_directory.any((f) => f.id == targetUserId)) {
      throw const ApiException('없는 사용자입니다',
          code: 'USER_NOT_FOUND', status: 404);
    }
    // 🔴 이미 보냈어도 오류가 아니다 — 원하던 상태가 이미 이뤄진 것이다.
    _sent.add(targetUserId);
  }

  @override
  Future<void> accept(String contactId) async {
    await Future<void>.delayed(_delay);

    final i = _requests.indexWhere((r) => r.id == contactId);
    if (i < 0) {
      throw const ApiException('없는 신청입니다',
          code: 'CONTACT_NOT_FOUND', status: 404);
    }

    final req = _requests.removeAt(i);
    /* 🔴 **지인 목록으로 옮겨 간다.** 신청에서 사라지기만 하면 화면은
       「수락했는데 아무 일도 안 일어났다」로 보인다. */
    _contacts.add(
      Contact(
        contactId: req.id,
        userId: req.requesterUserId,
        nickname: _directory
            .firstWhere((f) => f.id == req.requesterUserId,
                orElse: () => const FoundUser(id: '', nickname: '알 수 없음'))
            .nickname,
      ),
    );
  }
}
